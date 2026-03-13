import os
import logging
from typing import Dict, Any
import chromadb

from agent.state import AgentState

logger = logging.getLogger(__name__)

try:
    persist_directory = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
    os.makedirs(persist_directory, exist_ok=True)
    
    chroma_client = chromadb.PersistentClient(path=persist_directory)
    
    collection = chroma_client.get_or_create_collection(
        name="misinfo-claims",
        metadata={"hnsw:space": "cosine"}
    )
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}")
    collection = None

async def dedup_node(state: AgentState) -> Dict[str, Any]:
    text = state.get("translated_text") or state.get("original_text", "")
    claim_id = state.get("claim_id", "unknown")
    
    if not text.strip() or collection is None:
        return {"mutation_depth": 0}
        
    try:
        results = collection.query(
            query_texts=[text],
            n_results=1,
            include=["distances", "metadatas"]
        )
        
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        
        if distances and distances[0] < 0.18:
            best_dist = distances[0]
            parent_id = ids[0]
            parent_meta = metadatas[0] or {}
            
            parent_depth = parent_meta.get("mutation_depth", 0)
            
            sim_score = 1.0 - best_dist
            logger.info(f"Duplicate/Mutation found (sim={sim_score:.2f}). Parent: {parent_id}")
            
            reasoning = list(state.get("reasoning_chain", []))
            reasoning.append(f"Dedup: High similarity ({sim_score:.2f}) with past claim {parent_id}. Linked as mutation.")
            
            return {
                "mutation_of": parent_id,
                "mutation_depth": int(parent_depth) + 1,
                "reasoning_chain": reasoning,
            }
        else:
            # Upsert the novel claim so future runs can detect duplicates
            try:
                collection.add(
                    documents=[text],
                    ids=[claim_id],
                    metadatas=[{"mutation_depth": 0, "claim_id": claim_id}],
                )
                logger.info("Novel claim upserted to ChromaDB: %s", claim_id)
            except Exception as upsert_err:
                logger.error("ChromaDB upsert failed: %s", upsert_err)
            
            reasoning = list(state.get("reasoning_chain", []))
            reasoning.append("Dedup: No similar claims found in vector store. Claim is novel.")
            return {"mutation_depth": 0, "reasoning_chain": reasoning}
            
    except Exception as e:
        logger.error(f"Dedup failed: {e}")
        return {"mutation_depth": 0}
