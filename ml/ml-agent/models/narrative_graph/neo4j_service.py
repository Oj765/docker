import os
import logging
from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

class Neo4jService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        
        if uri and password:
            self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
            logger.info("Connected to Neo4j AuraDB.")
        else:
            self.driver = None
            logger.warning("NEO4J_URI or NEO4J_PASSWORD missing. Neo4j disabled.")
            
    async def close(self):
        if self.driver:
            await self.driver.close()

    async def ingest_post(self, account_id: str, platform: str, claim_id: str, timestamp: str):
        """Creates Account and Claim nodes and POSTED relationship."""
        if not self.driver: return
        
        query = """
        MERGE (a:Account {id: $account_id, platform: $platform})
        MERGE (c:Claim {id: $claim_id})
        MERGE (a)-[r:POSTED {timestamp: $timestamp}]->(c)
        """
        async with self.driver.session() as session:
            try:
                await session.run(query, account_id=account_id, platform=platform, 
                                  claim_id=claim_id, timestamp=timestamp)
            except Exception as e:
                logger.error(f"Neo4j ingest failed: {e}")

# Singleton
neo4j_db = Neo4jService()
