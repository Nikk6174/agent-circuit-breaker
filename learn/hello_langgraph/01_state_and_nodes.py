"""Example 1: a typed state, two plain-Python nodes, and the edges between them."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class NoteState(TypedDict, total=False):
    """The shared notebook every node reads from and writes to."""

    text: str
    word_count: int
    summary: str


def count_words(state: NoteState) -> dict:
    # A node returns only the keys it changed; LangGraph merges them into the state.
    return {"word_count": len(state["text"].split())}


def summarise(state: NoteState) -> dict:
    return {"summary": f"{state['word_count']} words, starting with {state['text'].split()[0]!r}"}


def build_graph():
    builder = StateGraph(NoteState)
    builder.add_node("count_words", count_words)
    builder.add_node("summarise", summarise)
    builder.add_edge(START, "count_words")
    builder.add_edge("count_words", "summarise")
    builder.add_edge("summarise", END)
    # compile() checks the wiring (e.g. no edge to a missing node) and returns something runnable.
    return builder.compile()


def main() -> None:
    graph = build_graph()
    result = graph.invoke({"text": "the agent called the model again and again"})
    print(result)


if __name__ == "__main__":
    main()
