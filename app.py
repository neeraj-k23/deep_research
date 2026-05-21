import streamlit as st
import uuid
import sys
from pathlib import Path

# Add the project root to python path to ensure agent package imports work seamlessly
sys.path.append(str(Path(__file__).resolve().parent))

# Import agent core modules
from agent.config import print_status, LLM_MODEL, is_mock_mode
import agent.config as config
from agent.db import (
    create_session, get_all_sessions, get_session, delete_session,
    get_messages, get_turns, update_session_title, get_connection
)
from agent.orchestrator import run_deep_research

# Ensure page configuration is always the first streamlit call
st.set_page_config(
    page_title="Antigravity Deep Research Workspace",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fetch some live database stats for the premium sidebar indicator cards
def get_db_stats():
    """Queries the SQLite database to compile live telemetry counts."""
    stats = {"sessions_count": 0, "turns_count": 0, "urls_count": 0}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Total Sessions
        cursor.execute("SELECT COUNT(*) FROM sessions")
        stats["sessions_count"] = cursor.fetchone()[0]
        
        # 2. Total Turns
        cursor.execute("SELECT COUNT(*) FROM turns")
        stats["turns_count"] = cursor.fetchone()[0]
        
        # 3. Total Crawled URLs
        cursor.execute("SELECT urls_opened FROM turns")
        rows = cursor.fetchall()
        unique_urls = set()
        for row in rows:
            import json
            try:
                urls = json.loads(row[0])
                for u in urls:
                    unique_urls.add(u)
            except Exception:
                pass
        stats["urls_count"] = len(unique_urls)
        
        conn.close()
    except Exception:
        pass
    return stats

db_stats = get_db_stats()

# Custom premium CSS styling: Ultimate Glassmorphism & Cyberpunk Space Theme
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap');
    
    /* General body & canvas properties */
    .stApp {
        background: radial-gradient(circle at 50% 10%, #0d1117 0%, #07090e 100%);
        color: #e6edf3;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Modern neon typographic scale */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        color: #45f3ff !important;
        letter-spacing: -0.5px;
        text-shadow: 0 0 15px rgba(69, 243, 255, 0.15);
    }
    
    /* Glowing main title banner */
    .hero-banner {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.5) 0%, rgba(17, 24, 39, 0.5) 100%);
        border: 1px solid rgba(69, 243, 255, 0.2);
        border-radius: 12px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    
    /* Neon glowing sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0b0f17 !important;
        border-right: 1px solid rgba(69, 243, 255, 0.1) !important;
    }
    
    /* Sidebar stat cards */
    .stat-card {
        background: rgba(31, 41, 55, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        text-align: center;
        transition: all 0.2s ease-in-out;
    }
    
    .stat-card:hover {
        border-color: rgba(69, 243, 255, 0.3);
        background: rgba(31, 41, 55, 0.6);
        transform: translateY(-1px);
    }
    
    .stat-num {
        color: #45f3ff;
        font-size: 20px;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .stat-label {
        color: #8b949e;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Glassmorphic Citation Buttons */
    .citation-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 15px;
    }
    
    .citation-card {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid rgba(69, 243, 255, 0.15);
        border-radius: 8px;
        padding: 12px 16px;
        transition: all 0.2s ease-in-out;
        min-width: 180px;
        max-width: 280px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
    }
    
    .citation-card:hover {
        border-color: #45f3ff;
        background: rgba(22, 27, 34, 0.9);
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(69, 243, 255, 0.2);
    }
    
    .citation-link {
        color: #45f3ff !important;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 13px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .citation-domain {
        color: #58a6ff;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: block;
        margin-top: 6px;
        font-family: 'Fira Code', monospace;
    }
    
    /* Telemetry Panel Design */
    .telemetry-header {
        color: #ff7b72 !important;
        font-size: 14px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    
    .telemetry-row {
        background: rgba(31, 41, 55, 0.3);
        border-left: 3px solid #ff7b72;
        border-radius: 4px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 13px;
    }
    
    /* Code formatting */
    code {
        font-family: 'Fira Code', monospace !important;
        color: #ff7b72 !important;
        background: rgba(255, 123, 114, 0.1) !important;
        padding: 2px 5px !important;
        border-radius: 4px !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR: CONFIG & WORKSPACE HISTORY -----------------
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding-bottom: 15px;'>
        <img src="https://img.icons8.com/nolan/128/space-exploration.png" width="75"/>
        <h2 style='margin-top:0; font-size:26px; color:#45f3ff;'>ANTIGRAVITY</h2>
        <span style='color:#8b949e; font-size:11px; letter-spacing:1.5px; text-transform:uppercase;'>Deep Research Console</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    # 1. API Keys & Engine Settings
    st.subheader("🔑 Credentials & Config")
    
    if "gemini_key" not in st.session_state:
        st.session_state.gemini_key = config.GEMINI_API_KEY or ""
    if "tavily_key" not in st.session_state:
        st.session_state.tavily_key = config.TAVILY_API_KEY or ""
        
    user_gemini = st.text_input(
        "Google Gemini API Key",
        value=st.session_state.gemini_key,
        type="password",
        placeholder="AIzaSy..."
    )
    user_tavily = st.text_input(
        "Tavily Search API Key",
        value=st.session_state.tavily_key,
        type="password",
        placeholder="tvly-..."
    )
    
    # Dynamic settings injector
    if user_gemini:
        st.session_state.gemini_key = user_gemini
        config.GEMINI_API_KEY = user_gemini
    if user_tavily:
        st.session_state.tavily_key = user_tavily
        config.TAVILY_API_KEY = user_tavily
        
    # State Indicators
    if is_mock_mode():
        st.warning("⚠️ Demo/Mock Mode Active (API keys missing)")
    else:
        st.success("🟢 API Connected successfully")
        
    st.markdown("---")
    
    # 2. Database Stats Dashboard
    st.subheader("📊 Telemetry Statistics")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{db_stats["sessions_count"]}</div>
            <div class="stat-label">Threads</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{db_stats["turns_count"]}</div>
            <div class="stat-label">Turns</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{db_stats["urls_count"]}</div>
            <div class="stat-label">Sites</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # 3. Session Thread Selection
    st.subheader("📂 Conversations & History")
    sessions = get_all_sessions()
    
    # Automatically seed initial session if database has no active session
    if not sessions:
        new_sid = create_session(title="Initial Research Workspace")
        sessions = get_all_sessions()
        st.session_state.active_session_id = new_sid
        
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = sessions[0]["session_id"]
        
    session_options = {s["session_id"]: s["title"] for s in sessions}
    
    def on_session_change():
        st.session_state.active_session_id = st.session_state.session_selector
        
    selected_sid = st.selectbox(
        "Choose Session:",
        options=list(session_options.keys()),
        format_func=lambda x: session_options[x],
        key="session_selector",
        index=list(session_options.keys()).index(st.session_state.active_session_id) if st.session_state.active_session_id in session_options else 0,
        on_change=on_session_change
    )
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ New Session", use_container_width=True):
            new_sid = create_session(title=f"New Workspace — {uuid.uuid4().hex[:4]}")
            st.session_state.active_session_id = new_sid
            st.rerun()
    with c2:
        if st.button("🗑️ Delete Session", use_container_width=True, type="secondary"):
            delete_session(st.session_state.active_session_id)
            st.session_state.pop("active_session_id", None)
            st.rerun()

# ----------------- MAIN INTERFACE -----------------
# Premium Glassmorphic Hero Banner
st.markdown(f"""
<div class="hero-banner">
    <span style="color:#58a6ff; font-weight:600; text-transform:uppercase; font-size:11px; letter-spacing:2px; font-family:'Fira Code', monospace;">Advanced Agent Analytics Console</span>
    <h1 style="margin: 5px 0 0 0; font-size: 36px; line-height:1.1;">🌌 Antigravity Workspace</h1>
    <p style="margin: 8px 0 0 0; color:#8b949e; font-size:14px;">
        Zero-Framework deep research engine running query expansions, parallel scraper crawlers, and BM25-lite domain diversity rankers. 
        Active Model Engine: <code style="color:#45f3ff; background:rgba(69,243,255,0.08); padding:1px 6px; border-radius:3px;">{LLM_MODEL}</code>
    </p>
</div>
""", unsafe_allow_html=True)

# Fetch conversation history
active_session = get_session(st.session_state.active_session_id)
if not active_session:
    st.error("Active session thread missing. Rerunning...")
    st.session_state.pop("active_session_id", None)
    st.rerun()

messages = get_messages(st.session_state.active_session_id)
turns = get_turns(st.session_state.active_session_id)

# Render Chat interface
if not messages:
    st.markdown("""
    <div style='background:rgba(22, 27, 34, 0.4); border:1px solid rgba(255, 255, 255, 0.05); border-radius:10px; padding:30px; margin-top:10px;'>
        <h3 style='margin-top:0; color:#45f3ff;'>System Operational and Ready!</h3>
        <p>Input a research query in the bottom chat bar to initialize the multi-stage research flow:</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top:20px;">
            <div style="background:rgba(31, 41, 55, 0.3); padding:15px; border-radius:8px; border-left:3px solid #58a6ff;">
                <b style="color:#e6edf3;">📝 1. Expanded Planning</b>
                <p style="font-size:13px; color:#8b949e; margin-top:5px;">Gemini expands your question into 3 distinct search terms targeting contradictory and multi-hop perspective branches.</p>
            </div>
            <div style="background:rgba(31, 41, 55, 0.3); padding:15px; border-radius:8px; border-left:3px solid #3fb950;">
                <b style="color:#e6edf3;">🌐 2. Parallel Extraction</b>
                <p style="font-size:13px; color:#8b949e; margin-top:5px;">Scrapes raw page HTML concurrently inside Thread Pools, extracting clean text using Trafilatura blocks.</p>
            </div>
            <div style="background:rgba(31, 41, 55, 0.3); padding:15px; border-radius:8px; border-left:3px solid #bc8cff;">
                <b style="color:#e6edf3;">🧬 3. Round-Robin Diversity Ranker</b>
                <p style="font-size:13px; color:#8b949e; margin-top:5px;">Scores chunk keywords using custom BM25 overlap and boosts dates, selecting across different domains to avoid source starvation.</p>
            </div>
            <div style="background:rgba(31, 41, 55, 0.3); padding:15px; border-radius:8px; border-left:3px solid #ff7b72;">
                <b style="color:#e6edf3;">🛡️ 4. Synthesis with Conflict Disclosures</b>
                <p style="font-size:13px; color:#8b949e; margin-top:5px;">Streams grounded responses with inline citation hyperlinks, flagging conflicts or missing public evidence.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Render historical turns inside styled messages
    for msg in messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            # Map assistant response to DB turn telemetry
            matching_turn = None
            for t in turns:
                if t["final_answer"].strip() == msg["content"].strip():
                    matching_turn = t
                    break
                    
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                
                if matching_turn:
                    # 1. Premium Citation Buttons Display Grid
                    snippets = matching_turn["context_snippets"]
                    unique_citations = {}
                    for s in snippets:
                        unique_citations[s["url"]] = s
                        
                    if unique_citations:
                        st.markdown("<h5 style='font-size:13px; color:#58a6ff; font-weight:600; margin-top:20px; margin-bottom:5px; text-transform:uppercase;'>Sources Cited:</h5>", unsafe_allow_html=True)
                        st.markdown('<div class="citation-container">', unsafe_allow_html=True)
                        for url, c in unique_citations.items():
                            st.markdown(f"""
                            <div class="citation-card">
                                <a href="{url}" target="_blank" class="citation-link">🔗 {c['title']}</a>
                                <span class="citation-domain">{c['domain']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    # 2. Cyberpunk Telemetry Audit Panel
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("🛠️ View Agent Diagnostics & Scoring telemetry", expanded=False):
                        st.markdown('<div class="telemetry-header">💡 Query Planner Checklist</div>', unsafe_allow_html=True)
                        for q in matching_turn["search_queries"]:
                            st.markdown(f'<div class="telemetry-row">🚀 <code>{q}</code></div>', unsafe_allow_html=True)
                            
                        st.markdown('<div class="telemetry-header" style="color:#3fb950 !important; margin-top:15px;">🌐 Crawled Web Domain Targets</div>', unsafe_allow_html=True)
                        for u in matching_turn["urls_opened"]:
                            st.markdown(f'<div class="telemetry-row" style="border-left-color:#3fb950;"><a href="{u}" target="_blank" style="color:#e6edf3; text-decoration:none;">🔗 {u}</a></div>', unsafe_allow_html=True)
                            
                        st.markdown('<div class="telemetry-header" style="color:#bc8cff !important; margin-top:15px;">🧬 BM25-lite Grounded Snippets Scored</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="telemetry-row" style="border-left-color:#bc8cff;"><b>{len(matching_turn["context_snippets"])} snippet records</b> parsed, scored and packed inside the prompt window.</div>', unsafe_allow_html=True)

# ----------------- LIVE EXECUTION & TYPEWRITER GENERATOR -----------------
if user_query := st.chat_input("Enter your research question (e.g. 'Timeline discrepancies for 2026 quantum computers between TechCrunch and Engadget')"):
    
    # 1. Stream User bubble
    with st.chat_message("user"):
        st.markdown(user_query)
        
    # Dynamically update Workspace name if it is the first turn
    if not messages:
        title_summary = user_query[:35] + ("..." if len(user_query) > 35 else "")
        update_session_title(st.session_state.active_session_id, f"Research: {title_summary}")
        
    # 2. Glowing multi-stage progress container
    with st.status("🌌 Antigravity Deep Research: Initializing Loop...", expanded=True) as status:
        plan_spot = st.empty()
        search_spot = st.empty()
        fetch_spot = st.empty()
        rank_spot = st.empty()
        synthesis_spot = st.empty()
        
        # Instantiate orchestration loop generator
        research_generator = run_deep_research(st.session_state.active_session_id, user_query)
        
        telemetry_data = None
        final_answer = ""
        
        # Consume generator step states
        for step in research_generator:
            label = step["status"]
            
            if label == "planning":
                plan_spot.markdown("📝 **Planning**: Query Planner generating search strategies...")
            elif label == "planning_done":
                plan_spot.markdown("📝 **Planning Complete**: Expanded search checklist:\n" + "\n".join([f"- `\"{q}\"`" for q in step["queries"]]))
                
            elif label == "searching":
                search_spot.markdown("🔍 **Searching**: Querying Tavily Search API...")
            elif label == "searching_query":
                search_spot.markdown(f"🔍 **Searching**: Executing keyword query `\"{step['query']}\"`...")
            elif label == "searching_done":
                search_spot.markdown(f"🔍 **Searching Complete**: Compiled {step['results_count']} search records.")
                
            elif label == "fetching":
                fetch_spot.markdown("🌐 **Crawling**: Spawning parallel workers to crawl bodies...")
            elif label == "fetching_done":
                fetch_spot.markdown(f"🌐 **Crawling Complete**: Downloaded and parsed HTML data from {step['pages_count']} URLs.")
                
            elif label == "selecting_context":
                rank_spot.markdown("🧬 **Selecting Context**: Ranking snippets with custom BM25 diversity ranker...")
            elif label == "conflict_detected":
                rank_spot.markdown(f"🧬 **Conflict Flagged**: Discrepancies spotted between domains: `{(', ').join(step['domains'])}`")
            elif label == "context_selected":
                rank_spot.markdown(f"🧬 **Context Complete**: Loaded {step['snippets_count']} highly-ranked snippets inside prompt window.")
                
            elif label == "synthesizing":
                synthesis_spot.markdown("⚙️ **Synthesis**: Building prompt context & generating grounded response...")
                
            elif label == "generating_start":
                status.update(label="🌌 Research Loop Completed! Streaming Answer...", state="complete", expanded=False)
                break  # Break out to stream inside assistant chat bubble below
                
        # 3. Stream text in Chat message bubble typewriter-style
        with st.chat_message("assistant"):
            answer_spot = st.empty()
            
            # Consume remaining chunks from generator
            for step in research_generator:
                if step["status"] == "generating_chunk":
                    final_answer += step["chunk"]
                    answer_spot.markdown(final_answer + "▌")
                elif step["status"] == "done":
                    telemetry_data = step["telemetry"]
                    
            answer_spot.markdown(final_answer)
            
            # 4. Premium Citation Buttons Display Grid for the current turn
            if telemetry_data:
                citations_map = telemetry_data["citations_map"]
                if citations_map:
                    st.markdown("<h5 style='font-size:13px; color:#58a6ff; font-weight:600; margin-top:20px; margin-bottom:5px; text-transform:uppercase;'>Sources Cited:</h5>", unsafe_allow_html=True)
                    st.markdown('<div class="citation-container">', unsafe_allow_html=True)
                    for ref_num, c in citations_map.items():
                        st.markdown(f"""
                        <div class="citation-card">
                            <a href="{c['url']}" target="_blank" class="citation-link">🔗 {c['title']}</a>
                            <span class="citation-domain">{c['domain']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                # Cyberpunk Diagnostics panel
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("🛠 decline Telemetry & Scoring telemetry", expanded=False):
                    st.markdown('<div class="telemetry-header">💡 Query Planner Checklist</div>', unsafe_allow_html=True)
                    for q in telemetry_data["queries"]:
                        st.markdown(f'<div class="telemetry-row">🚀 <code>{q}</code></div>', unsafe_allow_html=True)
                        
                    st.markdown('<div class="telemetry-header" style="color:#3fb950 !important; margin-top:15px;">🌐 Crawled Web Domain Targets</div>', unsafe_allow_html=True)
                    for u in telemetry_data["urls_opened"]:
                        st.markdown(f'<div class="telemetry-row" style="border-left-color:#3fb950;"><a href="{u}" target="_blank" style="color:#e6edf3; text-decoration:none;">🔗 {u}</a></div>', unsafe_allow_html=True)
                        
                    st.markdown('<div class="telemetry-header" style="color:#bc8cff !important; margin-top:15px;">🧬 BM25-lite Grounded Snippets Scored</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="telemetry-row" style="border-left-color:#bc8cff;"><b>{telemetry_data["snippets_selected_count"]} snippet records</b> parsed, scored and packed inside the prompt window.</div>', unsafe_allow_html=True)
                    
    # Force state synchronization and lock logs
    st.rerun()
