import sys
import asyncio
import json
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ml", "ml-agent"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "ml", "ml-agent", ".env"))

from agent.graph import graph

async def main():
    print("Starting Misinfo Shield Agent...")
    
    mock_state = {
        "claim_id": "demo_claim_001",
        "original_text": "Drinking bleach cures all viral illnesses, according to a leaked government document.",
        "source_platform": "twitter",
    }
    
    print(f"Input Claim: '{mock_state['original_text']}'\n")
    try:
        result = await graph.ainvoke(mock_state)
        print("\nVerification Complete!\n")
        if "verdict" in result and result["verdict"]:
            print(json.dumps(result["verdict"], indent=2))
        else:
            print("⚠️ No verdict generated.")
    except Exception as e:
        print(f"\nPipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
