# Testing the Misinfo Shield ML/AI Pipeline

This guide explains how to test the LangGraph ML agent locally with synthetic mock data, simulating what happens when the Full-Stack/Backend team feeds data via Kafka.

## Prerequisites

1. Ensure you have activated your python environment (if any) and have installed the requirements:
   ```bash
   pip install -r ml-agent/requirements.txt
   ```
2. Your `.env` file should be filled out (as you've already done).

## Running the Complete Pipeline Test

We have provided a testing script `test_pipeline.py`. To run it and see the LLM at work:

### Option 1: Using pytest (Standard)

```bash
cd ml-agent
pytest tests/test_pipeline.py -v
```

### Option 2: Running a manual Python Interactive Test

If you want to see the detailed JSON output and reasoning chain logged out to the console, you can run this script directly from the project root:

```python
# Create a temporary test runner (e.g., run_demo.py)
import asyncio
import json
from ml_agent.agent.graph import graph

async def main():
    print("🚀 Starting Misinfo Shield Agent...")
    
    # Simulate an incoming claim from social media
    mock_state = {
        "claim_id": "demo_claim_001",
        "original_text": "Drinking bleach cures all viral illnesses, according to a leaked government document.",
        "source_platform": "twitter",
    }
    
    # Run the graph
    result = await graph.ainvoke(mock_state)
    
    print("\n✅ Verification Complete!\n")
    print(json.dumps(result["verdict"], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

Save the code above an run `python run_demo.py`. This will trigger:
1. NLLB-200 Language detection
2. spaCy Extraction
3. ChromaDB vector deduplication
4. **Parallel querying** to Google Fact Checks, DuckDuckGo, and **Data.gov.in**
5. XGBoost risk scoring
6. **Gemini 2.0 Flash** Verdict Generation

## Testing the Red Team Agent

To test the adversarial pipeline (which generates "sneaky" mutations of a claim):

```python
from ml_agent.models.red_team.adversarial_agent import generate_adversarial_variants

variants = generate_adversarial_variants("The earth is completely flat and NASA is lying.", num_variants=2)
for i, v in enumerate(variants):
    print(f"Variant {i+1}: {v}")
```
