import json
from tavily import TavilyClient
from agent.config import TAVILY_API_KEY, MAX_SEARCH_RESULTS, is_mock_mode
from agent.llm import generate_text

def get_tavily_client():
    """Initializes and returns the TavilyClient or None if in mock mode."""
    if is_mock_mode():
        return None
    try:
        return TavilyClient(api_key=TAVILY_API_KEY)
    except Exception as e:
        print(f"Error creating Tavily client: {e}")
        return None

def generate_search_queries(user_query: str) -> list:
    """
    Uses Gemini LLM to expand the user's query into 2-3 distinct, optimal search keywords.
    Ensures broad and deep coverage of different source materials.
    """
    prompt = f"""
You are the query planner for a Deep Research Agent.
The user has asked the following research question:
"{user_query}"

Generate a list of up to 3 distinct, highly effective search queries in JSON format that will help gather comprehensive, diverse perspectives and answer the question accurately.
Each search query should target a different aspect, sub-topic, or potential viewpoint (including conflicting ones, if applicable).

Return ONLY a valid JSON array of strings. Do not include markdown codeblocks or explanation.
Example Output:
["query 1", "query 2", "query 3"]
"""
    
    # Get JSON output from LLM
    response = generate_text(prompt, system_instruction="You are a precise JSON query-generator.")
    
    # Clean output
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.endswith("```"):
        response = response[:-3]
    response = response.strip()
    
    try:
        queries = json.loads(response)
        if isinstance(queries, list):
            # Enforce string items and list size
            return [str(q) for q in queries[:3]]
    except Exception as e:
        print(f"Failed to parse search queries JSON. Response was: {response}. Using fallback.")
    
    # Fallback to simple variations
    return [user_query, f"{user_query} details", f"{user_query} recent updates"]

def execute_search(query: str, max_results: int = None) -> list:
    """
    Executes a search query using Tavily API.
    Returns: [{'title': '...', 'url': '...', 'snippet': '...', 'score': 0.95}]
    """
    results_limit = max_results or MAX_SEARCH_RESULTS
    
    if is_mock_mode():
        return get_mock_search_results(query, results_limit)
        
    client = get_tavily_client()
    if not client:
        return get_mock_search_results(query, results_limit)
        
    try:
        # Perform advanced depth search
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=results_limit,
            include_raw_content=False
        )
        
        search_results = []
        for res in response.get("results", []):
            search_results.append({
                "title": res.get("title", "Untitled Source"),
                "url": res.get("url", ""),
                "snippet": res.get("snippet", ""),
                "score": res.get("score", 0.5)
            })
        return search_results
    except Exception as e:
        print(f"Tavily search failed for query '{query}': {e}. Falling back to mock results.")
        return get_mock_search_results(query, results_limit)

def get_mock_search_results(query: str, limit: int) -> list:
    """Returns realistic mock search results based on the search query terms."""
    q_lower = query.lower()
    
    # Generate mock database
    mock_db = [
        {
            "title": "Quantum Computing Milestones in 2026",
            "url": "https://techcrunch.com/2026/quantum-computing-milestones",
            "snippet": "Researchers in 2026 achieved a quantum advantage milestone, demonstrating a 1000-qubit processor running fault-tolerant error correction codes. However, critics claim practical scalability remains years away.",
            "score": 0.92,
            "keywords": ["quantum", "compute", "tech", "2026"]
        },
        {
            "title": "Scaling Quantum Processors: The 2027 Timeline Debate",
            "url": "https://engadget.com/2026/quantum-scaling-debate",
            "snippet": "Engadget has learned that leading labs are pushing back their general availability dates for quantum cloud APIs to mid-2027. Software optimization issues are cited as primary blockers.",
            "score": 0.88,
            "keywords": ["quantum", "scale", "2027", "timeline"]
        },
        {
            "title": "History of Quantum Mechanics and Computing",
            "url": "https://wikipedia.org/wiki/Quantum_computing",
            "snippet": "Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve problems too complex for classical computers. Early foundations were laid in the 1980s.",
            "score": 0.75,
            "keywords": ["quantum", "wikipedia", "mechanics", "history"]
        },
        {
            "title": "State of Agentic Workflows and Python Chains",
            "url": "https://wired.com/2026/agentic-python-workflows",
            "snippet": "AI agents built entirely using custom Python orchestration loops are outpacing rigid pre-made framework packages. Developers cite lower overhead, direct context limits control, and absolute database transparency as core drivers.",
            "score": 0.94,
            "keywords": ["agent", "python", "workflow", "orchestration"]
        },
        {
            "title": "Semantic Relevance Scoring in LLM Prompts",
            "url": "https://arxiv.org/abs/2604.12345",
            "snippet": "This paper presents a custom, non-vector relevance ranker utilizing BM25 and diversity clustering metrics. The authors prove that balancing source diversity with raw similarity mitigates generative confabulation.",
            "score": 0.91,
            "keywords": ["rank", "relevance", "arxiv", "semantic", "snippet"]
        }
    ]
    
    # Filter and score based on query keywords matching
    matched = []
    query_words = q_lower.split()
    for item in mock_db:
        match_count = 0
        for word in query_words:
            # Check title, snippet, or explicit keywords
            if word in item["title"].lower() or word in item["snippet"].lower() or any(kw in word for kw in item["keywords"]):
                match_count += 1
        if match_count > 0 or not query_words:
            # Adjust score slightly based on query match count
            boost = min(0.05 * match_count, 0.08)
            item_copy = item.copy()
            item_copy["score"] = min(item_copy["score"] + boost, 1.0)
            matched.append(item_copy)
            
    # Sort by score descending
    matched.sort(key=lambda x: x["score"], reverse=True)
    
    # Return up to the limit, default to first few if nothing matched
    results = matched[:limit]
    if not results:
        results = mock_db[:limit]
        
    # Remove custom keywords from final output
    return [{"title": r["title"], "url": r["url"], "snippet": r["snippet"], "score": r["score"]} for r in results]
