import logging
from models.narrative_graph.neo4j_service import neo4j_db

logger = logging.getLogger(__name__)

async def detect_campaigns():
    if not neo4j_db.driver:
        logger.warning("Neo4j not configured. Returning mock campaigns.")
        return [{"campaign_id": "mock_cmp_1", "claim_count": 15, "accounts_involved": 42}]
        
    query = """
    MATCH (a:Account)-[r:POSTED]->(c:Claim)
    WITH c.id AS claim_id, count(a) AS account_count, collect(a.id) AS accounts
    WHERE account_count > 10
    RETURN claim_id, account_count, accounts
    ORDER BY account_count DESC LIMIT 5
    """
    
    try:
        campaigns = []
        async with neo4j_db.driver.session() as session:
            result = await session.run(query)
            async for record in result:
                campaigns.append({
                    "claim_id": record["claim_id"],
                    "accounts_involved": record["account_count"],
                })
        return campaigns
    except Exception as e:
        logger.error(f"Campaign detection failed: {e}")
        return []
