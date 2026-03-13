import sys
from langgraph.graph import StateGraph, END
from .state import AgentState

from nodes.ingest import ingest_node
from nodes.extract import extract_node
from nodes.translate import translate_node
from nodes.dedup import dedup_node
from nodes.verify import verify_node
from nodes.score import score_node
from nodes.enrich import enrich_node
from nodes.guardrail import guardrail_node
from nodes.verdict import verdict_node
from nodes.output import output_node


def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest", ingest_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("translate", translate_node)
    workflow.add_node("dedup", dedup_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("score", score_node)
    workflow.add_node("enrich", enrich_node)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("verdict", verdict_node)
    workflow.add_node("output", output_node)

    # Pipeline flow:
    # ingest -> translate -> extract -> dedup -> verify ->
    # score -> enrich -> guardrail -> verdict -> output
    workflow.add_edge("ingest", "translate")
    workflow.add_edge("translate", "extract")
    workflow.add_edge("extract", "dedup")
    workflow.add_edge("dedup", "verify")
    workflow.add_edge("verify", "score")
    workflow.add_edge("score", "enrich")
    workflow.add_edge("enrich", "guardrail")
    workflow.add_edge("guardrail", "verdict")
    workflow.add_edge("verdict", "output")
    workflow.add_edge("output", END)

    workflow.set_entry_point("ingest")

    return workflow.compile()

graph = create_graph()
