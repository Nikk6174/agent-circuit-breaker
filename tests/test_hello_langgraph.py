"""Tests for the standalone LangGraph examples in learn/hello_langgraph/."""

import importlib.util
from pathlib import Path

from langgraph.types import Command

EXAMPLES = Path(__file__).resolve().parent.parent / "learn" / "hello_langgraph"


def load(filename: str):
    # The files start with digits, so they cannot be imported with a normal import statement.
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), EXAMPLES / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_flows_through_both_nodes():
    graph = load("01_state_and_nodes.py").build_graph()
    result = graph.invoke({"text": "one two three"})
    assert result["word_count"] == 3
    assert result["summary"] == "3 words, starting with 'one'"


def test_loop_retries_then_stops_at_the_limit():
    graph = load("02_conditional_routing.py").build_graph()
    lucky = graph.invoke({"max_attempts": 5, "succeeds_on": 2, "log": []})
    hopeless = graph.invoke({"max_attempts": 5, "succeeds_on": 0, "log": []})
    assert lucky["attempts"] == 2 and lucky["log"][-1] == "finish: done"
    assert hopeless["attempts"] == 5 and hopeless["log"][-1].startswith("give_up")


def test_agent_alternates_llm_and_tool_until_it_answers():
    graph = load("03_tool_and_fake_llm.py").build_graph()
    result = graph.invoke({"question": "12 * 7 + 16?", "history": [], "max_llm_calls": 5})
    assert result["answer"] == "The total is 100."
    assert result["llm_calls"] == 3
    assert [line.split()[0] for line in result["history"]] == [
        "CALL",
        "RESULT",
        "CALL",
        "RESULT",
        "ANSWER",
    ]


def test_graph_pauses_for_human_and_resumes_with_answer():
    graph = load("04_checkpoint_and_pause.py").build_graph()
    config = {"configurable": {"thread_id": "t1"}}

    paused = graph.invoke({"run_id": "run-7"}, config)
    assert "run-7" in paused["__interrupt__"][0].value["proposal"]
    assert graph.get_state(config).next == ("ask_human",)
    assert "outcome" not in paused

    result = graph.invoke(Command(resume="yes"), config)
    assert result["approved"] is True
    assert result["outcome"].startswith("done: stop run run-7")
