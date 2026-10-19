# Part 01: Foundation

## Where we are

This is the first part, so we have only an idea. By the end we will have an organised project,
a settings file, code that reads it, and tests that prove it hangs together.

## What this part adds and why

A developer starts an AI agent tidying support tickets on Friday evening and goes home. Around
midnight it hits a ticket it can't handle. It asks the language model what to do, tries a tool,
the tool fails, it asks again. Nobody is watching. Each attempt costs a few cents. By Monday it
has made two hundred thousand calls, the bill is thousands of dollars, and nothing got tidied.

An AI agent is a program that asks a large language model (an LLM: a model that reads text and
writes text back) "what should I do next?", does it, shows the model the result, and asks again.
Picture an intern who phones their manager after every step. That loop lets agents handle
situations nobody programmed for, but it has no natural end. A stuck intern keeps calling, and
every call is billed.

Your house solves a similar problem with a fuse box: when one circuit draws too much current,
that one fuse trips, the rest of the house stays on, and someone checks before flipping it back.
Our project is a fuse box for agents, built from four pieces:

- **The gate** stands between the agent and the LLM provider. Every call passes through it,
  like current through a fuse.
- **The store** is the gate's memory: how many steps each run has taken, how much it has spent,
  which calls it has made.
- **The investigator** is itself a small agent, built with LangGraph (a library for building
  agents as a graph of steps). When a run gets paused, it reads the history and works out why.
- **Human approval** means nothing drastic happens without a person saying yes.

They fit together like this. The gate checks each call against some rules. If a rule trips,
the gate pauses just that one run and drops an "incident" onto a queue (a waiting line of work).
The investigator picks it up, explains what went wrong and suggests what to do. A human
approves or rejects, and the answer travels back to the gate, which resumes or stops the run.

Why start with structure and config instead of the exciting bits? Because everything later
depends on two decisions we want to make once: where each piece lives, and where the numbers
live. "Stop after 25 steps" is a business decision, not a programming one. Scattered through
the code, such numbers get forgotten; in one settings file, changing one is a reviewable edit.

## How it works

Follow the data. It starts in `config/settings.yaml`, which has three sections. `limits` holds
the maximum steps per run, the budget per run in dollars, and how many identical calls count as
a loop. `pricing` holds the price per thousand tokens (a token is a chunk of text, about
three-quarters of a word, and it is what providers bill by), with separate input and output
prices because providers charge differently for each. `rules` holds one on/off switch per rule.

Next, `src/breaker/config/loader.py` reads the file with PyYAML's `safe_load`, which turns YAML
into plain Python dictionaries without running any code hidden in it. Then it checks environment
variables, named values your shell hands to every program it starts. A variable called
`BREAKER_<SECTION>__<KEY>` replaces the matching setting. On AWS this is how we will change
settings, rather than editing files inside a container.

Environment variables are always text, so the loader converts each to the type the YAML used.
If you misspell a variable name, the loader refuses to start. That is a deliberate trade-off: a
startup crash is annoying, but a typo that silently does nothing could leave a budget limit
different from the one you think you set.

Finally, the loader packs everything into frozen dataclasses (`Settings`, `Limits`, `Pricing`).
"Frozen" means they can't be changed after creation, so no code can quietly raise a limit
halfway through a run.

## How it connects to the rest

The other packages (gate, store, rules, investigator, queue, notify) are empty for now, like
labelled boxes before moving day. Later parts fill them in, and all of them will take their
limits from `load_settings()`. `CLAUDE.md` records our ground rules, including AWS safety.

## Try it

From the `agent-circuit-breaker` folder, run:

```bash
uv run pytest
```

Four tests should pass. Now break something on purpose: in `config/settings.yaml`, rename
`max_steps_per_run` to `max_step_per_run`, rerun the tests and read the error. Put it back. Then
try a misspelled override (in PowerShell, set it with `$env:BREAKER_LIMITS__MAX_STEP="5"`):

```bash
BREAKER_LIMITS__MAX_STEP=5 uv run python -c "from breaker.config import load_settings; load_settings()"
```

It fails loudly instead of ignoring you.

## What comes next

Part 02 builds the store, the gate's memory. Before the gate can decide anything, it needs to
write down "run 42 has taken 12 steps and spent $0.80". We'll define the store as a small
interface with a simple local version, so we can later swap in an AWS database without changing
its callers. Memory comes before judgement, so the store comes before the rules and the gate.

## Check yourself

1. Why does it matter that the gate pauses one run rather than stopping the whole agent system?
2. What could go wrong if the loader silently ignored environment variables it did not recognise?
3. Why do we keep separate prices for input and output tokens instead of one price?
