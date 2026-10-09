---
tags: [interactive, desk, revision]
runs: 2
max_turns: 8
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
append_system_prompt: "You have no shell in this evaluation, so you cannot run commands or write files. Follow the skill and answer with your plan: the exact studio commands you would run in order, the files you would change, and what the user sees on the desk. Do not lead with what you cannot do."
---

We're working on my LSM-tree explainer in interactive mode (live engine, the desk is open, and
`studio wait` just returned this):

    1 new note:
    1. [2:13.3 s3_04 both] Explain exactly what runs are, and how they relate to the log on disk,
       if at all.  (id 7f2a91c0, cut 3)
       on screen: When the memtable fills up, flush it to disk as one sorted, immutable file.

Handle it.
