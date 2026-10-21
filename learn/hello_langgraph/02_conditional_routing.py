"""Example 2: a router picks the next node, with a loop back that a counter is sure to end."""

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RetryState(TypedDict, total=False):
    """State for a job that may need several attempts."""

    attempts: int
    max_attempts: int
    # Which attempt will succeed (0 means never), so we can test both endings.
    succeeds_on: int
    succeeded: bool
    # The reducer (operator.add) appends each node's entries instead of replacing the list.
    log: Annotated[list[str], operator.add]


def plan(state: RetryState) -> dict:
    attempt = state.get("attempts", 0) + 1
    return {"attempts": attempt, "log": [f"plan: attempt {attempt}"]}


def try_it(state: RetryState) -> dict:
    ok = state["attempts"] == state["succeeds_on"]
    return {"succeeded": ok, "log": [f"try: {'worked' if ok else 'failed'}"]}


def finish(state: RetryState) -> dict:
    return {"log": ["finish: done"]}


def give_up(state: RetryState) -> dict:
    return {"log": [f"give_up: stopped after {state['attempts']} attempts"]}


def route_after_try(state: RetryState) -> Literal["finish", "give_up", "plan"]:
    if state["succeeded"]:
        return "finish"
    # The safety stop: without this check a job that never succeeds would loop forever.
    if state["attempts"] >= state["max_attempts"]:
        return "give_up"
    return "plan"


def build_graph():
    builder = StateGraph(RetryState)
    builder.add_node("plan", plan)
    builder.add_node("try_it", try_it)
    builder.add_node("finish", finish)
    builder.add_node("give_up", give_up)
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "try_it")
    builder.add_conditional_edges("try_it", route_after_try, ["finish", "give_up", "plan"])
    builder.add_edge("finish", END)
    builder.add_edge("give_up", END)
    return builder.compile()


def main() -> None:
    graph = build_graph()
    # The limit comes in with the input, the way the real project reads limits from config.
    for succeeds_on in (3, 0):
        result = graph.invoke({"max_attempts": 5, "succeeds_on": succeeds_on, "log": []})
        print(f"succeeds_on={succeeds_on}:")
        for line in result["log"]:
            print("  ", line)


if __name__ == "__main__":
    main()
