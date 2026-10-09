---
type: llm
weight: 3
---

PASS if the response does all of:
- marks the note as being worked on (`studio notes VIDEO --start 7f2a91c0`) and keeps the desk's status line current;
- treats it as a local note in chapter 3: changes SCRIPT.md's narration there (for example a sentence on what a run is and how it relates to the write-ahead log, which it covers and which is then truncated) and the chapter's scene (`scenes/s3.js` or the clip's live scene), re-narrating so only changed paragraphs re-voice, with cues on the spoken phrase (`c.phrase`);
- runs `studio check` (or the incremental check) on the changed chapter and looks at a still before answering;
- resolves the note with a one-line reply saying what changed (`studio notes VIDEO --resolve 7f2a91c0 --reply "..."`) and starts `studio wait` again.
FAIL if it changes other chapters without reason, renders a full final cut instead of checking the change, resolves without checking, or asks the user to run commands.
