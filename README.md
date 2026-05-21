# 🌌 Antigravity: Production Deep Research Agent

A state-of-the-art, zero-framework **Deep Research Agent** built from scratch in Python. Antigravity dynamically expands queries, fetches and extracts web content in parallel, sorts context snippets utilizing a custom relevance and diversity scoring algorithm, and synthesizes citation-grounded research reports. It features SQLite-backed session persistence, real-time UI execution step visualization, and an automated evaluation harness.

---

## 🚀 Quick Start & Installation

### 📋 Prerequisites
Ensure you have Python 3.9+ installed on your system.

### ⚙️ Step-by-Step Setup

1. **Clone or Navigate to the Directory**:
   ```bash
   cd /Users/neerajkulkarni/Downloads/A3_Moodle/deep_research_agent
   ```

2. **Install Dependencies**:
   Install the required libraries listed in `requirements.txt` (including Streamlit, google-generativeai, tavily-python, beautifulsoup4, trafilatura, python-dotenv, and numpy):
   ```bash
   python3 -m pip install -r requirements.txt
   ```

3. **Configure API Credentials**:
   Create a `.env` file in the root directory:
   ```bash
   touch .env
   ```
   Add your credentials inside `.env`:
   ```env
   GEMINI_API_KEY="your_google_gemini_api_key"
   TAVILY_API_KEY="your_tavily_search_api_key"
   LLM_MODEL="gemini-1.5-flash"
   ```
   *Note: If no API keys are provided, the system automatically triggers a fully functional, highly interactive **Mock Simulation Mode** so the app remains entirely inspectable and usable with rich, simulated data.*

4. **Launch the Web Dashboard**:
   Boot up the Streamlit interface:
   ```bash
   streamlit run app.py
   ```

5. **Run the Automated Evaluation Harness**:
   Execute the evaluation benchmark suite:
   ```bash
   python3 eval/runner.py
   ```

---

## 📝 Part 1: Design Note

### 👥 Target Users & Problem Solved
* **Target Users**: Knowledge workers, researchers, business analysts, and software developers who spend hours compiling comparative reports, reading multiple search links, filtering boilerplate web ads, and fact-checking timeline contradictions.
* **The Problem**: Public search engines are flooded with advertisements and SEO-spam articles. Traditional RAG systems are simple: they perform a single search query, scrape the top 3 snippets, and send them to an LLM. This leads to information gaps, missed secondary sources, vulnerability to contradictory claims, and failure to express appropriate uncertainty on undocumented facts.

### 🧬 Definition of "Deep Research" for this Implementation
For Antigravity, **Deep Research** is defined as an active, multi-turn reasoning and discovery loop:
1. **Multi-Query Expansion**: Translating a complex user query into 2-3 distinct, highly targeted keyword searches to capture diverse perspective angles.
2. **Concurrence Crawling**: Parallel download of full text blocks (bypassing commercial advertisements, navbars, and headers).
3. **Relevance & Diversity Snippet Filtering**: Extracting text blocks based on keyword similarity, boosting recency indicators, and executing **Round-Robin Diversity Selection** to ensure prompt context contains a balanced representation across different web domains.
4. **Resolution of Discrepancies**: Actively identifying date or specifications contradictions between sources, citing both perspectives, and explicitly declaring uncertainty where data is weak.

### 📈 Success Metrics for Research Quality
We evaluate the agent's research outputs using five primary indicators:
1. **Grounding Ratio**: The percentage of claims in the generated answer that directly map to a selected search snippet (aiming for 100% to eliminate hallucinations).
2. **Source Diversity Index**: The unique count of crawled web domains represented in the final citation list (measured to verify that the agent didn't rely entirely on a single site).
3. **Uncertainty Calibration Accuracy**: The rate at which the agent correctly declares uncertainty, details missing details, or suggests follow-up queries on unindexed or confidential questions.
4. **Conflict Resolution Completeness**: The percentage of detected timeline/spec contradictions where both sides of the argument are cited.
5. **Answer Correctness Score (LLM-as-a-Judge)**: A structured score from 1 to 5 evaluating structure, completeness, and factual precision.

### 🔄 Data Flow & Components
```
[User Input Query]
        ↓
  Query Planner (LLM generates 3 search keywords)
        ↓
  Search layer (Tavily executes multi-query API calls)
        ↓
  Concurrent Fetcher (HTTP requests + Trafilatura + BeautifulSoup HTML parser)
        ↓
  Custom Scorer & Ranker (BM25 + Recency + Round-Robin Domain Diversity Selection)
        ↓
  Synthesizer (Direct stream to Gemini with Conflict Check & strict Citation Instructions)
        ↓
  Database Logger (SQLite turn telemetry & message persistence)
        ↓
  Streamlit UI (Real-time typewriter display + citation links + telemetries)
```

### ⚠️ Risks, Limitations & Future Roadmaps

#### Core Risks & Limitations
1. **Rate Limits & API Quotas**: Free-tier Gemini and Tavily accounts have strict requests-per-minute limits. If limit blocks are encountered, the agent could fail to retrieve web context.
2. **Context Budgets vs Cost**: Crawling several dense sites can saturate token limits. Packing too many words in the prompt increases token costs and latency.
3. **Conflicting & Low-Quality SEO Sites**: Scraping unverified blogs could load contradictory rumors, making it difficult for the LLM to verify ground truth.

#### Future Improvements
1. **Vector Cache Integration**: Implementing a lightweight, local vector cache (e.g. using `numpy` cosine similarities or `sqlite-vss`) to save crawled chunks and avoid redundant search crawls across similar user sessions.
2. **Dynamic Web Browser Scraper**: Integrating a headless browser execution layer (like Playwright) to scrape pages that require javascript rendering or have bot-protection scripts that standard requests cannot bypass.

---

## 🛠️ Technical Implementation details

### 🧩 Zero-Framework Agent Orchestration
Antigravity does not use LangChain, LangGraph, or CrewAI.
Instead, it establishes a native Python Generator-based loop inside `agent/orchestrator.py`:
```python
def run_deep_research(session_id: str, user_query: str):
    # 1. Plan
    yield {"status": "planning"}
    queries = generate_search_queries(user_query)
    
    # 2. Search
    yield {"status": "searching"}
    results = [execute_search(q) for q in queries]
    
    # 3. Fetch
    yield {"status": "fetching"}
    pages = fetch_all_pages([r['url'] for r in results])
    
    # 4. Rank
    yield {"status": "selecting_context"}
    snippets = select_context_snippets(pages, user_query)
    
    # 5. Synthesize & Stream
    yield {"status": "generating_start"}
    for chunk in stream_text(prompt):
        yield {"status": "generating_chunk", "chunk": chunk}
```
This generator pattern allows the Streamlit UI to consume steps as they occur in real time using non-blocking loops, ensuring complete control over the interface.

### 💾 Session Management (SQLite Schema)
The agent automatically creates and manages a SQLite database `research_sessions.db` with three fully-relational tables:

1. **`sessions`**: Manages workspaces (`session_id`, `title`, `created_at`).
2. **`messages`**: Stores message logs for UI rendering (`message_id`, `session_id`, `role`, `content`, `timestamp`).
3. **`turns`**: Records rich execution telemetry for auditor review (`turn_id`, `session_id`, `query`, `search_queries`, `urls_opened`, `context_snippets`, `final_answer`, `timestamp`).

---

## 📊 Evaluation Harness (Part 3)

The automated evaluation harness inside `eval/runner.py` feeds a curated dataset (`eval/dataset.json`) representing five critical research scenarios (Factual, Multi-hop, Comparison, Insufficient Evidence, and Conflicting Sources) to the agent.

### Curated Scenarios
1. **Factual** (`fact_01`): Searches for exact qubit parameters and cost metrics.
2. **Multi-hop** (`multihop_01`): Synthesis of facts scattered across separate TechCrunch and Engadget pages.
3. **Comparison** (`compare_01`): Contrasting custom Python agent loops against pre-built framework limits.
4. **Insufficient Evidence** (`insufficient_01`): Testing agent safety disclosures when searching for classified Q-Force security codes.
5. **Conflicting Sources** (`conflict_01`): Compiling contradictory reports regarding 2026 vs 2027 release dates, testing citation representation.

### Metric Compilation
Upon completion, the script automatically compiles:
- `eval/eval_results.json`: Complete telemetry JSON.
- `eval/EVAL_REPORT.md`: A gorgeous, human-readable markdown report displaying category scores, grounding statistics, latency metrics, and evaluation findings!

---

## 📽️ Video Demo
*A placeholder link for your application video demonstration is provided in the submissions file. The Streamlit UI offers complete visual controls for presenting real-time agent diagnostics.*
