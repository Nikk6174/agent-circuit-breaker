# Part 02: Hello LangGraph

## Where we are

Part 01 gave us the project's skeleton: package folders, a settings file, a loader and tests.
The `investigator` folder will hold an agent built with LangGraph, so first we learn the tool
in throwaway examples under `learn/hello_langgraph/`, kept out of `src/` because they are
practice, not product.

## What this part adds and why

LangGraph lets us describe an agent as a **graph**. Forget the maths meaning. Think of a recipe
drawn as a flowchart on the fridge. Each box is a step ("chop onions"), each arrow says what
comes next, and a notebook lies open on the counter where every step reads what it needs and
writes down what it did. In LangGraph the boxes are **nodes** (ordinary Python functions), the
arrows are **edges**, and the notebook is the **state** (a dictionary whose shape we declare up
front).

Why not a plain `while` loop? Agents need three things a bare loop makes awkward: branching on
what just happened, a guaranteed stop, and pausing for hours to wait for a human. LangGraph
gives each a name and a place.

## How it works

`01_state_and_nodes.py` is the smallest useful graph. `NoteState` is a `TypedDict`, a dictionary
with declared keys and types, so the notebook has a fixed layout. `count_words` and `summarise`
are plain functions that take the state and return only the keys they changed; LangGraph merges
that update into the notebook. We connect `START → count_words → summarise → END`, then call
`compile()`, which checks the wiring and gives back something we can `invoke()`.

`02_conditional_routing.py` adds a **conditional edge**: an arrow whose destination is chosen
at run time. After `try_it`, the router function `route_after_try` looks at the state and returns
the name of the next node: `finish` if it worked, `give_up` if we have run out of attempts, or
back to `plan` to try again. That backward arrow is a loop, and a loop is exactly where an
agent burns money. So the state carries an `attempts` counter and a `max_attempts` limit, and
the router checks it every time round. The limit arrives with the input rather than being
written into the graph, just as our real limits come from config. This file also shows a
**reducer**: `log` is marked `Annotated[list[str], operator.add]`, which tells LangGraph to
append each node's entries rather than overwrite the list.

You might ask: doesn't LangGraph stop runaway graphs itself? It has a recursion limit, but in
the installed version (1.2.16) it defaults to 10,007 steps. That protects your computer from
spinning forever, not your wallet. Our own small counter is the real stop.

`03_tool_and_fake_llm.py` is the shape of every agent. `decide` asks `fake_llm`, a function
returning canned text, what to do. The reply is either `CALL multiply 12 7` or `ANSWER ...`.
The node turns that text into fields the graph can route on. If there is a tool to call, the
router sends us to `act`, which runs the tool and writes the result into `history`; an edge
leads straight back to `decide`, which now sees the result and decides again. A fake LLM costs
nothing and always answers the same, so the loop is easy to watch and test. The trade-off: it
never surprises us the way a real model will. We meet those surprises later, behind the gate.

`04_checkpoint_and_pause.py` adds memory and patience. A **checkpointer** saves the state after
every step, like a save point in a video game; `InMemorySaver` keeps those saves in a Python
dictionary. Each conversation gets a `thread_id`, the name of its save slot. Inside `ask_human`,
`interrupt(...)` stops the graph *before* `act` runs and hands a question back to whoever called
`invoke()`. Later, we call `invoke(Command(resume="yes"), config)` with the same `thread_id`,
and the graph carries on from the saved point. One catch: on resume, LangGraph re-runs
`ask_human` from its top, so code placed before `interrupt()` runs twice. Keep side effects
after it. And because `InMemorySaver` lives in memory, a restart loses every paused graph,
which is fine for learning but will not do in production.

## How it connects to the rest

The investigator will be a graph like these: it reads a paused run's history from the store,
loops between a real LLM and tools with a step limit (example 2), records its recommendation
with its reasoning, then pauses for human approval (example 4). Part 12 builds that pause for
real, with a checkpointer that survives restarts.

## Try it

From the `agent-circuit-breaker` folder:

```bash
uv run python learn/hello_langgraph/02_conditional_routing.py
uv run python learn/hello_langgraph/04_checkpoint_and_pause.py
uv run pytest
```

The second command pauses and asks you to approve; answer `yes`, then run it again and answer
`no`. Now break something on purpose: in `02_conditional_routing.py`, delete the two lines that
check `max_attempts` in `route_after_try` and rerun it. The `succeeds_on=0` job now never
finishes; watch it run until LangGraph's own limit throws a `GraphRecursionError` after
thousands of steps. Imagine every one of those steps had been a paid LLM call. Put the lines
back.

## What comes next

Part 03 builds the store, the gate's memory, which records how many steps each run has taken
and how much it has spent. The investigator you have just practised for will need that history
to read, and the rules and gate will need it to judge anything. So the store comes first.

## Check yourself

1. In example 2, what decides whether the arrow out of `try_it` goes forwards or backwards?
2. Why does example 4 fail if you compile the graph without a checkpointer?
3. If `ask_human` sent an email before calling `interrupt()`, what would happen on resume?
