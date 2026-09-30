---
tags: [routing, footage]
runs: 2
max_turns: 8
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
append_system_prompt: "You have no shell in this evaluation, so you cannot run commands or write files. Follow the skill and answer with your plan: the decisions you make, the questions you would ask, the exact studio commands you would run in order, and what you would show the user at each gate. Do not lead with what you cannot do."
---

I have a 12-minute recording of a talk, talk.mp4. Cut it down to the good parts, take out the ums, and add captions.
