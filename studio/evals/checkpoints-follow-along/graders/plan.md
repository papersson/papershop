---
type: llm
weight: 3
---

PASS if the response does all of:
- records that the user wants to follow along (studio new with --checkpoints many, or checkpoints set to "many" in video.json);
- plans boards (rough frames per beat, `studio boards`) and an animatic against the real narration (`studio animatic`) BEFORE animating scenes, and stops to show the user both;
- plans to show the first finished chapter before building the rest, and cuts as chapters are done (unbuilt chapters showing their boards);
- still settles the narrative with the user before any script, and keeps the student script pass.
FAIL if it only shows the user a finished cut, animates before any boards or animatic, or asks the user to run commands.
