---
type: llm
weight: 3
---

PASS if the response does all of:
- records that the user wants to follow along (studio new with --mode interactive, or "mode": "interactive" in video.json);
- opens the desk (`studio desk`) and runs `studio wait` in the background so each note reaches the builder, and keeps the desk's status line current;
- builds in the foreground chapter by chapter (unbuilt chapters show their boards), saying when each chapter is ready on the desk, and takes notes as they arrive: start, a scoped change, checks, then resolve with a one-line reply;
- still settles the narrative with the user before any script, and keeps the student script pass.
FAIL if it only shows the user a finished cut, hands the build to an unattended background agent, or asks the user to run commands.
