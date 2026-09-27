---
name: zelinqa
description: "Conduct a goal-driven qualification conversation with the Zelinqa MCP server: get the next useful question, report the answer, track progress and record the outcome. Not for general chat or for configuring a domain."
---

# Zelinqa

Use this skill when the Zelinqa MCP server is configured and the task is to
qualify a need, a lead or a request through questions. Read `zelinqa://guide`
first; it is the reference.

1. `zelinqa_start` with a unique, non-personal conversation name: it returns
   the first question.
2. Ask it in your own voice, wait for the person, then `zelinqa_next_question`
   with their exact words or the exact choice labels: it returns the next question.
3. Repeat until the reply says to stop or the objective is achieved, then
   `zelinqa_feedback` with the real result.

`zelinqa_add_context`, `zelinqa_adjust` and `zelinqa_status` help along the way
and consume no turn. Never invent an answer, an outcome, a value or an ID; keep
warnings visible; never ask the person for a session ID or an API key.
