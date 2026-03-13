import os
import httpx
import logging

logger = logging.getLogger(__name__)

async def search_fact_checks(query: str, num_results: int = 3) -> list:
    """Wrapper for Google Fact Check Tools API."""
    api_key = os.getenv("GOOGLE_FCAT_API_KEY")
    
    if not api_key:
        logger.warning("GOOGLE_FCAT_API_KEY missing. Returning mock data for demo.")
        return [{
            "url": "https://snopes.com/mock-fact-check",
            "title": "Mock FCAT Result: " + query,
            "credibility_score": 0.85,
            "excerpt": "This claim has been checked and found to be lacking context.",
            "source_type": "fact_check",
        }]
        
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {"query": query, "key": api_key, "pageSize": num_results}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for claim in data.get("claims", []):
                review = claim.get("claimReview", [{}])[0]
                results.append({
                    "url": review.get("url", ""),
                    "title": review.get("title", f"Fact check: {query}"),
                    "credibility_score": 0.9, # FCAT publishers are generally trusted
                    "excerpt": review.get("textualRating", "No rating found"),
                    "source_type": "fact_check",
                })
            return results
    except Exception as e:
        logger.error(f"FCAT API error: {e}")
        return []
