"""Verify all ML/AI dependencies are installed and working."""
import sys

results = []

def check(name, func):
    try:
        func()
        results.append((name, "OK"))
        print(f"  [OK] {name}")
    except Exception as e:
        results.append((name, f"FAIL: {e}"))
        print(f"  [FAIL] {name}: {e}")

print("=" * 50)
print("Misinfo Shield - ML/AI Dependency Check")
print("=" * 50)

# PyTorch + CUDA
def check_torch():
    import torch
    ver = torch.__version__
    cuda = torch.cuda.is_available()
    gpu = torch.cuda.get_device_name(0) if cuda else "N/A"
    vram = f"{torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB" if cuda else "N/A"
    print(f"       PyTorch {ver} | CUDA: {cuda} | GPU: {gpu} | VRAM: {vram}")
check("PyTorch + CUDA", check_torch)

# spaCy
def check_spacy():
    import spacy
    nlp = spacy.load("en_core_web_sm")
    print(f"       spaCy {spacy.__version__} | en_core_web_sm loaded")
check("spaCy", check_spacy)

# LangGraph
check("LangGraph", lambda: __import__("langgraph"))

# Groq (Primary LLM)
def check_groq():
    import groq
    print(f"       Groq SDK {groq.__version__}")
check("Groq SDK", check_groq)

# Google GenAI (Fallback LLM)
check("Google GenAI", lambda: __import__("google.genai"))

# Anthropic (Removed as per user request)

# sentence-transformers
check("SentenceTransformers", lambda: __import__("sentence_transformers"))

# ChromaDB
check("ChromaDB", lambda: __import__("chromadb"))

# Neo4j
check("Neo4j", lambda: __import__("neo4j"))

# XGBoost
def check_xgb():
    import xgboost
    print(f"       XGBoost {xgboost.__version__}")
check("XGBoost", check_xgb)

# Transformers (for NLLB)
def check_transformers():
    import transformers
    print(f"       Transformers {transformers.__version__}")
check("Transformers", check_transformers)

# aiokafka
check("aiokafka", lambda: __import__("aiokafka"))

# httpx
check("httpx", lambda: __import__("httpx"))

# aiohttp
check("aiohttp", lambda: __import__("aiohttp"))

# DuckDuckGo Search
check("DuckDuckGo", lambda: __import__("duckduckgo_search"))

# langdetect
check("langdetect", lambda: __import__("langdetect"))

# sentencepiece
check("sentencepiece", lambda: __import__("sentencepiece"))

# pydantic
check("Pydantic", lambda: __import__("pydantic"))

# tenacity
check("tenacity", lambda: __import__("tenacity"))

# structlog
check("structlog", lambda: __import__("structlog"))

# python-dotenv
check("python-dotenv", lambda: __import__("dotenv"))

print("=" * 50)
passed = sum(1 for _, s in results if s == "OK")
failed = sum(1 for _, s in results if s != "OK")
print(f"Results: {passed} passed, {failed} failed out of {len(results)}")
if failed:
    print("\nFailed packages:")
    for name, status in results:
        if status != "OK":
            print(f"  - {name}: {status}")
else:
    print("ALL CHECKS PASSED")
print("=" * 50)
