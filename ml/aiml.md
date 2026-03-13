# Misinfo Shield — ML/AI Implementation Plan

> Extracted from `instruction.md` (ML / AI Engineer section, lines 227–479) and cross-referenced with `problem_statement.txt`.

---

## Problem Statement Recap

Build a **real-time misinformation detection agent** that:
1. Monitors social media feeds for viral, harmful claims
2. Cross-references claims against trusted national databases
3. Generates structured fact-check reports (claim, evidence, citations, severity)
4. Posts corrective, evidence-based responses when confidence + virality thresholds are met
5. Logs every response with a confidence score for human audit/override

---

## Tech Stack (ML/AI Scope)

| Component | Technology |
|---|---|
| Agent Orchestration | **LangGraph** (multi-step agent with memory, tool nodes, rollback) |
| LLM Backbone | **Claude claude-sonnet-4-20250514** (Anthropic SDK) |
| NLP | **spaCy** + **sentence-transformers** (all-MiniLM-L6-v2) |
| Vector Store | **Pinecone** (semantic dedup + claim similarity) |
| Graph DB | **Neo4j AuraDB** (narrative/campaign detection) |
| Amplification Model | **XGBoost** (virality/reach prediction) |
| Translation | **Meta NLLB-200-distilled-600M** |
| Multimodal | **Whisper** (audio transcription), **EasyOCR** (image text) |
| External APIs | Google Fact Check Tools API, Tavily API, NewsAPI, WHO API |

---

## Step-by-Step Implementation Tasks

### Phase 1 — Foundation & Schema (H0–H6)

- [ ] **Task 1.1: Define `AgentState` TypedDict** (`agent/state.py`)
  - Fields: `claim_id`, `original_text`, `translated_text`, `language`, `claims_extracted`, `evidence`, `verdict`, `risk_score`, `confidence`, `reasoning_chain`, `satire_flag`, `mutation_of`, `predicted_6h_reach`, `processed_at`
  - This IS the contract shared with the Full-Stack Dev and Backend

- [ ] **Task 1.2: Create Verdict JSON Schema** (Pydantic model)
  ```
  { claim_id, label (FALSE|MISLEADING|UNVERIFIED|TRUE), confidence (0-1),
    risk_score (0-1), reasoning_chain[], evidence_sources[{url, title,
    credibility_score, excerpt}], satire_flag, language, mutation_of,
    predicted_6h_reach, processed_at }
  ```

- [ ] **Task 1.3: Build LangGraph skeleton** (`agent/graph.py`)
  - Register all 9 node names (ingest → extract → translate → dedup → verify → score → guardrail → verdict → output)
  - Define edges and conditional routing
  - Empty node functions — fill logic node by node

- [ ] **Task 1.4: Write LLM prompts** (`prompts/`)
  - `verdict_system.txt` — fact-checker system prompt (conservative: use UNVERIFIED if weak evidence)
  - `claim_extract.txt` — atomic claim extraction prompt
  - `red_team_system.txt` — adversarial variant generator prompt

- [ ] **Task 1.5: Set up `requirements.txt`**
  - langgraph, anthropic, spacy, sentence-transformers, pinecone-client, neo4j, xgboost, langdetect, nllb (transformers), whisper, easyocr, httpx, aiokafka, etc.

---

### Phase 2 — NLP Extraction & Kafka Integration (H6–H14)

- [ ] **Task 2.1: Implement `ingest_node`** (`nodes/ingest.py`)
  - Async Kafka consumer from `normalized_claims` topic
  - Parse incoming message into `AgentState`
  - Log with timestamp + topic + partition offset

- [ ] **Task 2.2: Implement `extract_node`** (`nodes/extract.py`)
  - spaCy NER + dependency parsing to extract atomic checkable claims
  - One claim = one verifiable factual statement
  - Use sentence-transformers (all-MiniLM-L6-v2) for claim embeddings

---

### Phase 3 — LLM Agent: Claim Extraction & Verdict (H10–H22)

- [ ] **Task 3.1: Implement `verdict_node`** (`nodes/verdict.py`)
  - Call Claude claude-sonnet-4-20250514 via Anthropic SDK with `verdict_system.txt` prompt
  - Input: claim text + all gathered evidence
  - Output: structured JSON matching verdict schema
  - Must include fallback for API rate-limits
  - Must be async

- [ ] **Task 3.2: Implement `output_node`** (`nodes/output.py`)
  - Serialize verdict to JSON
  - Publish to Kafka `verdict_ready` topic via aiokafka
  - Log the full reasoning chain for auditability

---

### Phase 4 — Verification Toolkit (H14–H24)

- [ ] **Task 4.1: Google Fact Check Tools API wrapper** (`tools/fact_check_api.py`)
  - Async httpx calls — NO synchronous requests
  - Return: matching fact-checks with source, rating, URL

- [ ] **Task 4.2: Tavily Search API wrapper** (`tools/tavily_search.py`)
  - Async search for supporting/contradicting evidence
  - Return: relevant articles with title, url, excerpt, credibility

- [ ] **Task 4.3: WHO / CDC API wrapper** (`tools/who_api.py`)
  - Query against health-related databases
  - Return: official statements, data, source URLs

- [ ] **Task 4.4: Implement `verify_node`** (`nodes/verify.py`)
  - Call all 3 tools in **parallel** via `asyncio.gather`
  - Never sequential — this is a hard rule
  - Aggregate results into evidence list with credibility scores

---

### Phase 5 — Confidence & Risk Scoring (H22–H30)

- [ ] **Task 5.1: Implement `score_node`** (`nodes/score.py`)
  - Compute `confidence` (0–1): based on evidence strength, source count, source credibility
  - Compute `risk_score` (0–1): based on virality signals, claim severity, topic sensitivity
  - Both scores feed into the verdict and the frontend severity display

---

### Phase 6 — Satire/Tone/Dedup Filters (H24–H32)

- [ ] **Task 6.1: Implement `guardrail_node`** (`nodes/guardrail.py`)
  - **Satire check**: detect satirical content to avoid false flags
  - **Tone filter**: filter out clearly non-serious or hyperbolic content
  - **Source triangulation**: require 3+ independent source hits before labeling FALSE
  - Set `satire_flag` in state if detected

---

### Phase 7 — Pinecone Semantic Dedup (H30–H38)

- [ ] **Task 7.1: Implement `dedup_node`** (`nodes/dedup.py`)
  - Generate embedding via sentence-transformers (all-MiniLM-L6-v2)
  - Query Pinecone for cosine similarity > 0.82
  - If match found → link as mutation (`mutation_of = parent_claim_id`, increment `mutation_depth`)
  - If no match → upsert new claim with metadata: `claim_id`, `verdict`, `category`

---

### Phase 8 — Neo4j Narrative Graph (H32–H44)

- [ ] **Task 8.1: Neo4j service layer** (`models/narrative_graph/neo4j_service.py`)
  - Create `Account` nodes and `Claim` nodes
  - Create `POSTED` relationships between accounts and claims
  - Store metadata: timestamps, platform, engagement metrics

- [ ] **Task 8.2: Campaign detector** (`models/narrative_graph/campaign_detector.py`)
  - Cypher queries to detect clusters of coordinated accounts
  - Identify narrative campaigns (same claim variants from linked accounts)
  - Output campaign data for the frontend graph visualization

---

### Phase 9 — XGBoost Amplification Model (H38–H50)

- [ ] **Task 9.1: Feature extraction** (`models/amplification/features.py`)
  - Features: `account_followers`, `avg_rt_rate`, `sentiment`, `time_of_day`, `centrality`
  - Extract from claim metadata and Neo4j graph centrality metrics

- [ ] **Task 9.2: Training script** (`models/amplification/train.py`)
  - Train XGBoost model to predict `predicted_6h_reach`
  - Needs historical data (or synthetic data for hackathon demo)
  - Save model checkpoint

- [ ] **Task 9.3: Inference function** (`models/amplification/predict.py`)
  - Load trained model
  - Predict `predicted_6h_reach` for incoming claims
  - Feed prediction into `score_node` risk calculation

---

### Phase 10 — Multilingual Support (H44–H54)

- [ ] **Task 10.1: Implement `translate_node`** (`nodes/translate.py`)
  - Use `langdetect` to identify language
  - If not English → translate via Meta NLLB-200-distilled-600M
  - Store both `original_text` and `translated_text` in state
  - Set `language` field

---

### Phase 11 — Red Team Adversarial Agent (H50–H60)

- [ ] **Task 11.1: Adversarial agent** (`models/red_team/adversarial_agent.py`)
  - Generate misinfo variants (rephrased, mutated claims) to test the pipeline's robustness
  - Use `red_team_system.txt` prompt with Claude
  - Feed variants back into the pipeline and measure detection rate

---

### Phase 12 — End-to-End Testing & Tuning (H54–H64)

- [ ] **Task 12.1: Pipeline integration test** (`tests/test_pipeline.py`)
  - Full flow: ingest → extract → translate → dedup → verify → score → guardrail → verdict → output
  - Use test claims covering all verdict labels (FALSE, MISLEADING, UNVERIFIED, TRUE)

- [ ] **Task 12.2: Verdict quality test** (`tests/test_verdict.py`)
  - Test LLM output conforms to verdict JSON schema
  - Test confidence/risk score ranges
  - Test reasoning chain completeness

- [ ] **Task 12.3: Tuning & optimization**
  - Tune confidence thresholds
  - Tune Pinecone cosine similarity threshold (0.82)
  - Tune XGBoost hyperparameters
  - Tune guardrail sensitivity (satire detection false-positive rate)

---

## Cross-Role Conflict Verification ✅

> **All suggestions below have been verified against the Backend/Infra (lines 27–226) and Full-Stack Dev (lines 481–682) sections of `instruction.md`.**

| Suggestion | Touches Backend? | Touches Fullstack? | Verdict |
|---|---|---|---|
| Mock external APIs (FCAT, Tavily, WHO) | ❌ ML-side only | ❌ | ✅ Safe |
| Prioritize verdict_node + verify_node | ❌ ML-side only | ❌ | ✅ Safe |
| Synthetic data for XGBoost | ❌ ML-side only | ❌ | ✅ Safe |
| Circuit breaker for API calls | ❌ ML-side only | ❌ | ✅ Safe |
| Reasoning chain logging at every node | ❌ Writes to existing `reasoning_chain[]` in verdict schema | ❌ | ✅ Safe |
| Lazy-load NLLB-200 | ❌ ML-side only | ❌ | ✅ Safe |
| Pre-seed demo with test claims | ⚠️ Test data fed via Kafka `normalized_claims` topic | ❌ | ✅ Safe — uses agreed topic name |
| Batch Pinecone upserts | ❌ ML-side only | ❌ | ✅ Safe |

**Key boundary rules respected:**
- Kafka topics: Only consuming `normalized_claims` and publishing to `verdict_ready` (as specified)
- Verdict JSON schema: All output matches the frozen schema agreed at H0
- No FastAPI routes, MongoDB writes, or React code in any ML suggestion
- Whisper + EasyOCR stay with the Full-Stack Dev (we only consume their output)

---

## My Suggestions & Considerations

### 🔧 Practical / Hackathon-Specific

1. **Mock external APIs early**: For the hackathon, create mock responses for Google FCAT, Tavily, and WHO APIs. This lets you test the full pipeline without depending on API keys or rate limits. Switch to real APIs once the pipeline works end-to-end.

2. **Start with `verdict_node` + `verify_node` first** (not strictly by the hour timeline): These are the core value-add of the system. A working LLM verdict with evidence is demo-able even without dedup, translation, or campaign detection.

3. **Use synthetic training data for XGBoost**: You won't have real historical virality data. Generate synthetic features with realistic distributions. The model itself is a proof-of-concept for the demo.

4. **Pinecone free tier**: Use the free tier (1 index, 100K vectors). More than enough for a hackathon. Set up the index with dimensionality 384 (all-MiniLM-L6-v2 output).

5. **Neo4j AuraDB free tier**: Use the free instance. Pre-populate with a few fake accounts and claims to make the campaign graph demo compelling.

### 🧠 Architecture / Design

6. **Add a circuit breaker for external API calls**: If Tavily or WHO API is down, the pipeline shouldn't hang. Add timeouts (5s per API call) and graceful degradation — proceed with available evidence.

7. **Reasoning chain is critical for the demo**: The problem statement emphasizes "reasoning chain visible showing which sources it checked." Make sure every node appends to `reasoning_chain[]` with a clear, human-readable step description. This is what judges will look at.

8. **Consider a retry/fallback LLM strategy**: If Claude rate-limits, have a fallback to a cheaper/faster model or a cached response template. The instructions mention this rule but don't specify the fallback — I suggest using a simpler prompt with GPT-3.5 or a local model as backup.

9. **Batch Pinecone upserts**: Instead of upserting one-by-one, batch upserts (up to 100 vectors per call) for better performance at scale.

### ⚠️ Risk Flags

10. **NLLB-200-distilled-600M is ~2.4GB**: Loading this model will take time and RAM. Consider lazy-loading it only when a non-English claim is detected rather than at startup.

11. **Whisper + EasyOCR are Full-Stack Dev's domain** (per instructions). Don't implement them — just consume their output from the `normalized_claims` Kafka topic.

12. **Image provenance tool** (`tools/image_provenance.py`) is listed in the folder structure but NOT in the priority tasks. Treat it as a stretch goal — implement only if time permits.

13. **API key management**: The instructions say `os.getenv()` only. Set up a `.env.example` file documenting all required keys: `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`, `NEO4J_URI`, `NEO4J_PASSWORD`, `TAVILY_API_KEY`, `GOOGLE_FCAT_API_KEY`, `WHO_API_KEY`.

### 🎯 Demo Impact

14. **Pre-seed the system with known misinformation examples**: Have 5–10 well-known false claims (e.g., health misinformation) ready to stream through during the demo. This makes the live demo reliable and impressive.

15. **Neo4j graph visualization = wow factor**: If the frontend engineer builds the D3 force-directed graph, make sure the Neo4j data feeds it well. Pre-populate a small coordinated campaign cluster for the demo.

---

## File-to-Task Mapping

| File | Task(s) | Priority |
|---|---|---|
| `agent/state.py` | 1.1 | 🔴 Critical (H0) |
| `agent/graph.py` | 1.3 | 🔴 Critical (H0) |
| `prompts/verdict_system.txt` | 1.4 | 🔴 Critical (H0) |
| `prompts/claim_extract.txt` | 1.4 | 🟡 Medium |
| `prompts/red_team_system.txt` | 1.4 | 🟢 Low (H50+) |
| `nodes/ingest.py` | 2.1 | 🔴 Critical |
| `nodes/extract.py` | 2.2 | 🔴 Critical |
| `nodes/verdict.py` | 3.1 | 🔴 Critical |
| `nodes/output.py` | 3.2 | 🔴 Critical |
| `tools/fact_check_api.py` | 4.1 | 🔴 Critical |
| `tools/tavily_search.py` | 4.2 | 🔴 Critical |
| `tools/who_api.py` | 4.3 | 🟡 Medium |
| `nodes/verify.py` | 4.4 | 🔴 Critical |
| `nodes/score.py` | 5.1 | 🔴 Critical |
| `nodes/guardrail.py` | 6.1 | 🟡 Medium |
| `nodes/dedup.py` | 7.1 | 🟡 Medium |
| `nodes/translate.py` | 10.1 | 🟡 Medium |
| `models/narrative_graph/neo4j_service.py` | 8.1 | 🟡 Medium |
| `models/narrative_graph/campaign_detector.py` | 8.2 | 🟡 Medium |
| `models/amplification/features.py` | 9.1 | 🟢 Low |
| `models/amplification/train.py` | 9.2 | 🟢 Low |
| `models/amplification/predict.py` | 9.3 | 🟢 Low |
| `models/red_team/adversarial_agent.py` | 11.1 | 🟢 Low |
| `tests/test_pipeline.py` | 12.1 | 🔴 Critical |
| `tests/test_verdict.py` | 12.2 | 🟡 Medium |
| `requirements.txt` | 1.5 | 🔴 Critical |

---

## Implementation Order Summary

```
H0–H6   ▸ State + Schema + Graph Skeleton + Prompts + Requirements
H6–H14  ▸ Kafka Ingest + NLP Extraction
H10–H22 ▸ LLM Verdict + Kafka Output
H14–H24 ▸ Verification Toolkit (FCAT, Tavily, WHO — parallel)
H22–H30 ▸ Confidence + Risk Scoring
H24–H32 ▸ Satire/Tone/Dedup Guardrails
H30–H38 ▸ Pinecone Semantic Dedup
H32–H44 ▸ Neo4j Narrative Graph + Campaign Detection
H38–H50 ▸ XGBoost Amplification Model
H44–H54 ▸ NLLB-200 Multilingual Translation
H50–H60 ▸ Red Team Adversarial Testing
H54–H64 ▸ End-to-End Testing + Tuning
```

---

## 🤖 LLM Backbone Recommendation: Claude Sonnet 4 vs Gemini

### The Short Answer

> **Claude Sonnet 4 is NOT free.** It's a paid API at ~$3/M input tokens, ~$15/M output tokens. For a hackathon, **Google Gemini 2.0 Flash** is the better choice — it has a very generous free tier and excellent structured JSON output.

### Full Comparison

| Factor | Claude Sonnet 4 | Gemini 2.0 Flash | Gemini 2.5 Flash |
|---|---|---|---|
| **Free tier** | ❌ No free tier (pay-per-token) | ✅ **15 RPM, 1M TPM, 1500 RPD free** | ✅ **10 RPM, 250K TPM, 500 RPD free** |
| **Cost (paid)** | $3 / $15 per M tokens (in/out) | $0.10 / $0.40 per M tokens | $0.15 / $3.50 per M tokens |
| **JSON output** | Good (needs prompt engineering) | ✅ Native `response_mime_type: application/json` | ✅ Native JSON mode |
| **Speed** | ~30-50 tok/s | ✅ ~150+ tok/s (very fast) | ~80-100 tok/s |
| **Reasoning quality** | ✅ Excellent | Good for fact-checking | ✅ Excellent (thinking model) |
| **Context window** | 200K tokens | 1M tokens | 1M tokens |
| **Rate limits (free)** | N/A | Very generous for hackathon | Moderate |
| **SDK** | `anthropic` | `google-genai` | `google-genai` |

### My Recommendation for This Hackathon

**Use Gemini 2.0 Flash as the primary LLM backbone.** Here's why:

1. **Free = zero risk**: You won't burn through API credits during 72 hours of testing. With Claude, a few hundred test runs can cost $5-20+.

2. **Speed matters for real-time**: Gemini 2.0 Flash is 3-5x faster than Claude Sonnet. For a real-time misinformation system where latency matters (the problem statement says "before it spreads"), this is a significant advantage.

3. **Native JSON mode**: Gemini supports `response_mime_type: "application/json"` which guarantees valid JSON output. With Claude, you need prompt engineering and sometimes get markdown-wrapped JSON that breaks parsing.

4. **1M context window**: 5x larger than Claude's 200K. Useful if evidence documents are long.

5. **15 RPM free tier is enough**: For a hackathon demo, you're processing maybe 1-5 claims per minute. 15 RPM is plenty.

### If You Want the Best of Both Worlds

Use **Gemini 2.0 Flash as primary** and keep Claude as an optional upgrade:

```python
# In agent config / .env
LLM_PROVIDER=gemini          # or "claude"
GEMINI_API_KEY=xxx            # Free from Google AI Studio
ANTHROPIC_API_KEY=xxx         # Optional, paid
```

The `requirements.txt` already includes both SDKs. We can build an abstraction layer that lets you swap between them with a single env var.

### How to Get Gemini API Key (Free)

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with Google account
3. Click "Get API Key" → "Create API key"
4. Done — immediately usable, no billing setup needed

### Code Change Impact

If we go with Gemini, the only files affected are:
- `nodes/verdict.py` — LLM call (use `google-genai` instead of `anthropic`)
- `models/red_team/adversarial_agent.py` — LLM call
- `prompts/verdict_system.txt` — prompt stays the same (model-agnostic)
- `.env` — add `GEMINI_API_KEY` instead of `ANTHROPIC_API_KEY`

**No impact on any other role** — the verdict JSON output schema stays identical regardless of which LLM generates it.

