"""Example 4: a checkpointer saves progress so a graph can pause for a human and resume later."""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class IncidentState(TypedDict, total=False):
    """A paused run, what we propose to do about it, and what the human said."""

    run_id: str
    proposal: str
    approved: bool
    outcome: str


def investigate(state: IncidentState) -> dict:
    return {"proposal": f"stop run {state['run_id']}: it repeated the same call 4 times"}


def ask_human(state: IncidentState) -> dict:
    # On resume LangGraph re-runs this node from the top, and interrupt() then returns the
    # human's answer. So anything before interrupt() runs twice: keep side effects after it.
    answer = interrupt({"question": "Approve this action?", "proposal": state["proposal"]})
    return {"approved": str(answer).strip().lower() in {"y", "yes"}}


def act(state: IncidentState) -> dict:
    if state["approved"]:
        return {"outcome": f"done: {state['proposal']}"}
    return {"outcome": "rejected: run left paused for a human to look at"}


def build_graph(checkpointer=None):
    builder = StateGraph(IncidentState)
    builder.add_node("investigate", investigate)
    builder.add_node("ask_human", ask_human)
    builder.add_node("act", act)
    builder.add_edge(START, "investigate")
    builder.add_edge("investigate", "ask_human")
    builder.add_edge("ask_human", "act")
    builder.add_edge("act", END)
    # Without a checkpointer there is nowhere to save the paused state, so interrupt() fails.
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def main() -> None:
    graph = build_graph()
    # The thread_id names this conversation; resuming with the same id picks up where it stopped.
    config = {"configurable": {"thread_id": "incident-1"}}

    paused = graph.invoke({"run_id": "run-42"}, config)
    question = paused["__interrupt__"][0].value
    print("Paused. Next step waiting:", graph.get_state(config).next)
    print("Proposal:", question["proposal"])

    answer = input(f"{question['question']} [yes/no] ")
    result = graph.invoke(Command(resume=answer), config)
    print(result["outcome"])


if __name__ == "__main__":
    main()
