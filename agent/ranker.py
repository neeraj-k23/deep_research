import re
from collections import defaultdict
from agent.config import MAX_SNIPPET_SIZE, MAX_CONTEXT_CHAR_LIMIT

# A short list of common English stopwords to filter out of the query terms
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "cant", "cannot",
    "co", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during", "each",
    "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he", "hed",
    "hell", "hes", "her", "here", "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id",
    "ill", "im", "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most",
    "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shannt", "she", "shed", "shell", "shes", "should",
    "shouldnt", "so", "some", "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves",
    "then", "there", "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
    "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom", "why", "whys",
    "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your", "yours", "yourself", "yourselves"
}

def clean_query_terms(query: str) -> list:
    """Extracts non-stopword alphanumeric terms from the query for keyword similarity matching."""
    words = re.findall(r"\b\w+\b", query.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]

def chunk_text(text: str, max_size: int = MAX_SNIPPET_SIZE, overlap: int = 200) -> list:
    """
    Splits text into overlapping chunks.
    Ensures sentence boundaries are preserved where possible.
    """
    if not text:
        return []
        
    # Replace multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    
    if len(text) <= max_size:
        return [text]
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        if end >= len(text):
            chunks.append(text[start:])
            break
            
        # Try to backtrack to a sentence boundary (.!?) or word space
        boundary = -1
        for char_idx in range(end, max_size - overlap, -1):
            if text[char_idx] in (".", "!", "?") and char_idx + 1 < len(text) and text[char_idx + 1] == " ":
                boundary = char_idx + 1
                break
                
        if boundary != -1:
            chunks.append(text[start:boundary])
            start = boundary
        else:
            # Fall back to word space boundary
            space_idx = text.rfind(" ", start, end)
            if space_idx > start + (max_size - overlap):
                chunks.append(text[start:space_idx])
                start = space_idx + 1
            else:
                chunks.append(text[start:end])
                start = end
                
    return chunks

def score_snippet(snippet: str, query_terms: list, doc_metadata: dict) -> float:
    """
    Computes a numerical scoring value for a text snippet based on:
    1. Term frequency overlap (relevance)
    2. Recency boost (scanning snippet or metadata for recent years)
    """
    if not snippet:
        return 0.0
        
    snippet_lower = snippet.lower()
    
    # 1. Relevance: Count occurrences of query terms (BM25-lite term overlap)
    score = 0.0
    for term in query_terms:
        # Exact word match boost
        count = snippet_lower.count(term)
        if count > 0:
            # Diminishing returns for repetitive terms to avoid keyword-stuffing gaming
            score += (count / (count + 1.5)) * 10.0
            
    # 2. Recency Boost
    # Scan for years like 2025, 2026, 2027 in the snippet text
    years = re.findall(r"\b(202[4-9]|2030)\b", snippet)
    if years:
        # Boost for referencing current/future years
        score += 2.0
        # Extra boost if it explicitly references future projections (e.g. 2026/2027)
        if any(yr in ("2026", "2027") for yr in years):
            score += 1.5
            
    # Minor boost if relevance score is from a search result that itself had a high search score
    search_score = doc_metadata.get("search_score", 0.5)
    score += search_score * 2.0
    
    return score

def select_context_snippets(fetched_pages: list, user_query: str, search_results: list = None) -> list:
    """
    Advanced custom snippet selector prioritizing Relevance, Recency, and Source Diversity.
    Enforces a strict maximum context character limit.
    Uses Round-Robin Diversity Selection.
    
    Returns: List of dicts containing keys: snippet, url, title, domain, score.
    """
    query_terms = clean_query_terms(user_query)
    
    # Map search scores to URLs for integration
    search_scores = {}
    if search_results:
        for res in search_results:
            search_scores[res["url"]] = res.get("score", 0.5)
            
    # 1. Process all fetched documents, chunk them, and score each chunk
    all_chunks_by_source = defaultdict(list)
    
    for page in fetched_pages:
        if not page.get("success") or not page.get("content"):
            continue
            
        url = page["url"]
        title = page["title"]
        domain = page["domain"]
        content = page["content"]
        
        # Integrate search score if available
        doc_metadata = {
            "search_score": search_scores.get(url, 0.5),
            "retrieved_at": page.get("retrieved_at", "")
        }
        
        chunks = chunk_text(content)
        for chunk in chunks:
            score = score_snippet(chunk, query_terms, doc_metadata)
            if score > 0.5:  # Filter out completely irrelevant boilerplate noise
                all_chunks_by_source[url].append({
                    "snippet": chunk,
                    "url": url,
                    "title": title,
                    "domain": domain,
                    "score": score
                })
                
    # Sort chunks for each source by score descending
    for url in all_chunks_by_source:
        all_chunks_by_source[url].sort(key=lambda x: x["score"], reverse=True)
        
    # 2. Round-Robin Diversity Selector
    # Pull highest scored chunk from Source A, then Source B, then Source C, then second-highest from A, etc.
    # Enforces a rich set of domains inside the LLM prompt.
    selected_snippets = []
    current_char_count = 0
    
    # Track sources in a list for iteration
    active_sources = list(all_chunks_by_source.keys())
    # Keep track of index in the chunks list for each source
    source_chunk_ptrs = {url: 0 for url in active_sources}
    
    while active_sources and current_char_count < MAX_CONTEXT_CHAR_LIMIT:
        next_active_sources = []
        
        for url in active_sources:
            ptr = source_chunk_ptrs[url]
            chunks_list = all_chunks_by_source[url]
            
            if ptr < len(chunks_list):
                candidate = chunks_list[ptr]
                candidate_len = len(candidate["snippet"])
                
                # Check character limit budget
                if current_char_count + candidate_len < MAX_CONTEXT_CHAR_LIMIT:
                    selected_snippets.append(candidate)
                    current_char_count += candidate_len
                    source_chunk_ptrs[url] += 1
                    
                    # If this source still has chunks left, keep it in the rotation
                    if source_chunk_ptrs[url] < len(chunks_list):
                        next_active_sources.append(url)
                else:
                    # Budget exceeded, we must stop adding snippets
                    active_sources = []
                    break
            
        active_sources = next_active_sources
        
    # Final sorting of selected snippets by score descending for optimal placement in prompt
    selected_snippets.sort(key=lambda x: x["score"], reverse=True)
    return selected_snippets
