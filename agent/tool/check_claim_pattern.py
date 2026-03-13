from langchain_core.tools import tool
from app.db.neo4j_provider import neo4j_provider
import logging

logger = logging.getLogger(__name__)

@tool
def check_claim_pattern(claim_text: str) -> str:
    """
    Takes the claim text being fact-checked as input.
    Runs semantic similarity search against Neo4j claim nodes.
    Returns a context string about coordination and patterns.
    """
    session = neo4j_provider.get_session()
    if not session:
        return "⚠️ Narrative graph analysis unavailable (connection error)."

    # This is a simplified version of semantic similarity in Neo4j.
    # In a production app, we might use Neo4j Vector Search.
    # For now, we'll use a CONTAINS query or exact match as a proxy.
    
    query = """
    MATCH (acc:Account)-[:POSTED]->(c:Claim)
    WHERE (c.text CONTAINS $text OR $text CONTAINS c.text)
    AND c.verdict = 'FALSE'
    WITH c, count(acc) AS posters
    RETURN c.text AS claim, posters, c.times_seen_this_week AS weekly_seen
    ORDER BY posters DESC
    LIMIT 1
    """
    
    result_text = ""
    try:
        result = session.run(query, text=claim_text)
        record = result.single()
        
        if record:
            posters = record["posters"]
            weekly_seen = record["weekly_seen"] or posters
            
            # Simple burst detection logic
            bursts = 0
            if posters > 10:
                bursts = 2
            if posters > 30:
                bursts = 5
                
            result_text = (f"⚠️ This claim pattern has been posted by {posters} accounts "
                    f"this week. {bursts} coordinated bursts detected. "
                    f"Total weekly reach: {weekly_seen} instances.")
        else:
            result_text = "✅ No previous coordinated patterns detected for this claim."
            
    except Exception as e:
        logger.error(f"Error in check_claim_pattern tool: {e}")
        result_text = f"Error checking claim pattern: {str(e)}"
    finally:
        session.close()

    return result_text