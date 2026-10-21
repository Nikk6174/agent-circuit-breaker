"""Example 3: the agent loop (decide, act, look at the result, decide again) with a fake LLM."""

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict, total=False):
    """What the agent knows so far: the question, its history, and where it stands."""

    question: str
    history: Annotated[list[str], operator.add]
    next_tool: str
    tool_input: str
    answer: str
    llm_calls: int
    max_llm_calls: int


def fake_llm(history: list[str]) -> str:
    """Pretend LLM: returns canned text, like a real model's reply to the history so far."""
    results = [line for line in history if line.startswith("RESULT")]
    if not results:
        return "CALL multiply 12 7"
    if len(results) == 1:
        return f"CALL add {results[-1].split()[-1]} 16"
    return f"ANSWER The total is {results[-1].split()[-1]}."


TOOLS = {
    "multiply": lambda a, b: a * b,
    "add": lambda a, b: a + b,
}


def decide(state: AgentState) -> dict:
    reply = fake_llm(state["history"])
    calls = state.get("llm_calls", 0) + 1
    # Real models return text too; the node turns it into structured fields the graph can route on.
    kind, _, rest = reply.partition(" ")
    if kind == "CALL":
        tool, _, args = rest.partition(" ")
        return {"llm_calls": calls, "next_tool": tool, "tool_input": args, "history": [reply]}
    return {"llm_calls": calls, "next_tool": "", "answer": rest, "history": [reply]}


def act(state: AgentState) -> dict:
    a, b = (int(x) for x in state["tool_input"].split())
    result = TOOLS[state["next_tool"]](a, b)
    return {"history": [f"RESULT {state['next_tool']} -> {result}"]}


def route_after_decide(state: AgentState) -> Literal["act", "__end__"]:
    if state.get("answer"):
        return END
    # Every trip around the loop is a paid LLM call in real life, so cap it.
    if state["llm_calls"] >= state["max_llm_calls"]:
        return END
    return "act"


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("decide", decide)
    builder.add_node("act", act)
    builder.add_edge(START, "decide")
    builder.add_conditional_edges("decide", route_after_decide, ["act", END])
    builder.add_edge("act", "decide")
    return builder.compile()


def main() -> None:
    graph = build_graph()
    result = graph.invoke({"question": "What is 12 * 7 + 16?", "history": [], "max_llm_calls": 5})
    for line in result["history"]:
        print(line)
    print(f"answer: {result.get('answer')!r} after {result['llm_calls']} LLM calls")


if __name__ == "__main__":
    main()
