---
type: llm
weight: 3
---

PASS if the response treats this as an EXPLAINER driven by the AUTHOR (the user knows the subject), and does all of:
- plans to record the repo as the video's source (studio new with --source) and to explore the repo first for material, citing its files;
- settles a narrative (question, answer, a chain of claims) with the user BEFORE building any script or animation, asking at most a few questions;
- does not plan fresh-context reviewer rounds by default (the user's notes are the review), and mentions showing stills or a cut on a review page where the user leaves notes.
FAIL if it starts building immediately, insists on reviewers or research passes as the default, or ignores the repo.
