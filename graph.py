# ml-agent/agent/graph.py  (DIFF — add geo_tagger to your existing graph)
# Only the new lines are shown with comments. Merge into your existing graph.py

from langgraph.graph import StateGraph, END
from agent.state import AgentState

# existing imports ...
from agent.nodes.ingest    import ingest_node
from agent.nodes.extract   import extract_node
from agent.nodes.translate import translate_node
from agent.nodes.dedup     import dedup_node
from agent.nodes.verify    import verify_node
from agent.nodes.score     import score_node
from agent.nodes.guardrail import guardrail_node
from agent.nodes.verdict   import verdict_node
from agent.nodes.output    import output_node

# ── NEW IMPORT ───────────────────────────────────────────────────────────────
from agent.nodes.geo_tagger import geo_tagger_node


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # existing nodes
    g.add_node("ingest",    ingest_node)
    g.add_node("translate", translate_node)
    g.add_node("extract",   extract_node)
    g.add_node("dedup",     dedup_node)
    g.add_node("verify",    verify_node)
    g.add_node("score",     score_node)
    g.add_node("guardrail", guardrail_node)
    g.add_node("verdict",   verdict_node)

    # ── NEW NODE ─────────────────────────────────────────────────────────────
    g.add_node("geo_tag",   geo_tagger_node)

    g.add_node("output",    output_node)

    # existing edges
    g.set_entry_point("ingest")
    g.add_edge("ingest",    "translate")
    g.add_edge("translate", "extract")
    g.add_edge("extract",   "dedup")
    g.add_edge("dedup",     "verify")
    g.add_edge("verify",    "score")
    g.add_edge("score",     "guardrail")
    g.add_edge("guardrail", "verdict")

    # ── NEW EDGE: verdict → geo_tag → output ─────────────────────────────────
    g.add_edge("verdict",   "geo_tag")    # was: g.add_edge("verdict", "output")
    g.add_edge("geo_tag",   "output")

    g.add_edge("output",    END)

    return g.compile()
