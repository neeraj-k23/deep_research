import json
from datetime import datetime
from agent.config import LLM_MODEL, MAX_CONTEXT_CHAR_LIMIT
from agent.db import save_message, save_turn, get_messages, get_turns
from agent.llm import generate_text, stream_text, manage_context_window
from agent.search import generate_search_queries, execute_search
from agent.fetcher import fetch_all_pages
from agent.ranker import select_context_snippets

def check_for_conflicts(snippets: list) -> list:
    """
    Very lightweight heuristic detector for conflicts in snippets.
    Helps orchestrator alert the LLM to conflicting reports.
    """
    # Look for keywords indicating contradiction in proximity of dates or specs
    conflict_words = ["disagree", "contradict", "conflict", "dispute", "alternative", "contrary", "delayed", "postponed"]
    detected = []
    
    # We check if multiple sources mention the same key entities but different details
    # E.g. TechCrunch vs Engadget, etc.
    for i, s1 in enumerate(snippets):
        for j, s2 in enumerate(snippets[i+1:]):
            if s1["domain"] != s2["domain"]:
                # Check for semantic collision
                # If they both mention quantum error correction or releases but with different terms
                text1 = s1["snippet"].lower()
                text2 = s2["snippet"].lower()
                if any(w in text1 for w in conflict_words) or any(w in text2 for w in conflict_words):
                    if s1["domain"] not in detected:
                        detected.append(s1["domain"])
                    if s2["domain"] not in detected:
                        detected.append(s2["domain"])
    return detected

def run_deep_research(session_id: str, user_query: str):
    """
    Core custom agent orchestration loop running Plan -> Search -> Fetch -> Select Context -> Answer.
    Implemented as a pure Python generator yielding execution steps for real-time Streamlit visualization.
    
    Yields:
        dict: Operational steps representing intermediate telemetry, status, and raw streams.
    """
    # Retrieve rolling message history
    prior_messages = get_messages(session_id)
    prior_turns = get_turns(session_id)
    
    # 1. PLANNING STAGE
    yield {"status": "planning", "message": "Analyzing query and formulating search strategy..."}
    search_queries = generate_search_queries(user_query)
    yield {"status": "planning_done", "queries": search_queries}
    
    # 2. SEARCH STAGE
    yield {"status": "searching", "message": f"Executing multi-query expanded web searches across {len(search_queries)} pathways..."}
    
    all_search_results = []
    for query in search_queries:
        yield {"status": "searching_query", "query": query}
        results = execute_search(query)
        all_search_results.extend(results)
        
    # Deduplicate search results by URL
    unique_results = {}
    for r in all_search_results:
        unique_results[r["url"]] = r
    deduped_search_results = list(unique_results.values())
    
    yield {"status": "searching_done", "results_count": len(deduped_search_results), "results": deduped_search_results}
    
    if not deduped_search_results:
        yield {"status": "error", "message": "Search returned no active results. Proceeding with null-state disclaimer."}
        
    # 3. ACQUIRE & EXTRACT STAGE (FETCH)
    urls_to_fetch = [res["url"] for res in deduped_search_results[:6]]  # Cap at top 6 URLs for performance
    
    yield {"status": "fetching", "message": f"Downloading full pages and extracting raw contents for {len(urls_to_fetch)} URLs..."}
    fetched_pages = fetch_all_pages(urls_to_fetch)
    yield {"status": "fetching_done", "pages_count": len(fetched_pages)}
    
    # 4. SELECT CONTEXT STAGE (RANKER)
    yield {"status": "selecting_context", "message": "Executing BM25-lite keyword scoring & diversity ranker..."}
    selected_snippets = select_context_snippets(fetched_pages, user_query, deduped_search_results)
    
    # Heuristic conflict check
    conflicts_detected = check_for_conflicts(selected_snippets)
    if conflicts_detected:
        yield {"status": "conflict_detected", "domains": conflicts_detected}
        
    yield {"status": "context_selected", "snippets_count": len(selected_snippets), "snippets": selected_snippets}
    
    # 5. ANSWER SYNTHESIS (LLM)
    yield {"status": "synthesizing", "message": "Synthesizing deep research report with citation-grounded mappings..."}
    
    # Build history context with rolling summarization logic
    rolling_summary, active_messages = manage_context_window(prior_messages, prior_turns, user_query)
    
    # Build Context prompt string with index numbers
    context_str = ""
    citations_map = {}
    for idx, snip in enumerate(selected_snippets):
        ref_num = idx + 1
        citations_map[ref_num] = {
            "title": snip["title"],
            "url": snip["url"],
            "domain": snip["domain"]
        }
        context_str += f"[{ref_num}] (Source: {snip['domain']}, URL: {snip['url']})\n{snip['snippet']}\n\n"
        
    # Standard prompt for deep research grounded answers
    system_instruction = """
You are Antigravity, a professional, high-fidelity Deep Research AI Agent.
Your objective is to generate an exhaustive, comprehensive answer fully grounded in the provided web context snippets.

Strict Instructions:
1. CITATIONS: Every claim-heavy statement or fact MUST cite its source using inline numbers, matching the format: [Title — domain](URL) or simply linking directly to the URL using markdown. For example: "...as reported in [TechCrunch — techcrunch.com](https://techcrunch.com/quantum-computing)".
2. EVIDENCE STRENGTH: If the evidence is weak, missing, or inconclusive, you MUST explicitly state your uncertainty, highlight information gaps, and recommend potential verification steps.
3. CONFLICTS: If different sources offer conflicting accounts (e.g. differing release dates, performance specs, or timelines), you MUST explicitly note this disagreement, detail the alternate perspectives, and cite all involved sources.
4. HONESTY: Do NOT hallucinate any facts not explicitly present in the selected snippets. Rely only on the context provided.
"""

    history_context_str = ""
    if rolling_summary:
        history_context_str += f"Summary of Prior Conversation:\n{rolling_summary}\n\n"
    if active_messages:
        history_context_str += "Recent Conversation Logs:\n"
        for msg in active_messages:
            history_context_str += f"{msg['role'].upper()}: {msg['content']}\n"
        history_context_str += "\n"

    # Assemble final query prompt
    prompt = f"""
{history_context_str}
Selected Web Context Snippets:
===================================
{context_str or "No relevant search context was found."}
===================================

Original User Research Query:
"{user_query}"

Generate your comprehensive, citation-grounded research report now.
"""
    
    # Trigger streaming response generator
    answer_text = ""
    yield {"status": "generating_start"}
    
    for chunk in stream_text(prompt, system_instruction):
        answer_text += chunk
        yield {"status": "generating_chunk", "chunk": chunk}
        
    yield {"status": "generating_end", "answer": answer_text}
    
    # 6. PERSIST STATE
    # Save the interaction to chat history
    save_message(session_id, "user", user_query)
    save_message(session_id, "assistant", answer_text)
    
    # Save turning telemetry database logs
    urls_opened = [p["url"] for p in fetched_pages if p.get("success")]
    turn_id = save_turn(
        session_id=session_id,
        query=user_query,
        search_queries=search_queries,
        urls_opened=urls_opened,
        context_snippets=[{
            "snippet": s["snippet"],
            "url": s["url"],
            "title": s["title"],
            "domain": s["domain"]
        } for s in selected_snippets],
        final_answer=answer_text
    )
    
    # Final state with summary telemetry data
    yield {
        "status": "done",
        "answer": answer_text,
        "telemetry": {
            "turn_id": turn_id,
            "queries": search_queries,
            "urls_opened": urls_opened,
            "snippets_selected_count": len(selected_snippets),
            "citations_map": citations_map,
            "conflicts_flag": bool(conflicts_detected)
        }
    }
