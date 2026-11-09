# The click list

The click list is the whole page in words: chapters, and for each click the one thing that changes
and, only where the picture cannot say it, a caption. It is the story reel: shown to the reader and
changed until they approve, before anything is built. `new_page.py` prints it, lints it, and
builds the starter page from it. `check.py` holds the finished page to it.

## The format

```json
{
  "title": "How a hash table finds a key",
  "cover": true,
  "chapters": ["Seven fruits go into eight buckets", "Looking up fig"],
  "notes": ["Speaker notes for chapter 1.", "For chapter 2."],
  "clicks": [
    {"chapter": 1, "change": "Eight empty buckets appear, numbered 0 to 7",
     "caption": "An example table with eight empty buckets, numbered 0 to 7.",
     "object": "table", "state": "empty"},
    {"chapter": 2, "change": "The remainder glides across to bucket 5"}
  ]
}
```

- `title`: the page title, and the cover's text when `cover` is `true`.
- `cover`: `true` for a page that will be presented, or a string to open on a question instead.
- `chapters`: plain short sentences, no numbers. Clicks name them by number, counting from 1.
- `notes`: optional speaker notes, one string per chapter, shown with N.
- `clicks[].change`: what the reader sees change, in words. Required. If it needs "and", it is two
  clicks.
- `clicks[].caption`: optional. One sentence, at most 12 words, no dashes or semicolons. Leave it
  out when the picture says it.
- `clicks[].object` and `clicks[].state`: filled in while building, naming the object and state
  that make the click. `check.py` then checks the page against them.
- `clicks[].clear`: `true` for a click that only empties the stage mid-chapter (`keep` lists ids to
  leave).

`python3 -I scripts/new_page.py clicks.json --markdown` prints the list the way the reader will
follow it, then one line per problem. Show that markdown, not the JSON.

## What makes a good list

- **One real case kept throughout.** The same key, request or order from the first click to the
  last. When the second chapter wants a different case (a miss after a hit), keep everything else
  the same: same table, same bucket.
- **One idea per chapter.** If a chapter's title needs "and", it is two chapters.
- **Each click one visible change toward that idea.** "The key's three bytes appear" is a click.
  "The key is hashed" is not: say what the reader sees.
- **15 to 25 clicks.** Fewer usually means the page should be a sentence or a diagram. More usually
  means two pages.
- **The concrete before the general.** The rule ("the cost is one bucket's length") comes after
  the reader has watched one bucket being walked.
- **Captions spent where words are needed.** A cause, a consequence, what a number means. Read the
  list aloud with only the captions: they should tell the story's turns, not narrate every step.
- **A closing chapter in code**, where the topic has code: the same steps, with margin numbers that
  are the clicks which showed each line.

## Showing it for approval

Print the markdown and ask the reader to change anything: order, wording, a click to cut. Say how
many clicks it is and which chapter carries the main point. Change it until they approve it. Then
save it as the page directory's `clicks.json` (the build does this) and treat it as the contract:
when a caption changes while building, change it here too, because `check.py` reports any click
that has drifted from the approved list.

## Converting an existing deck or document

When the job is to turn someone's slides or document into a walkthrough, the job is a faithful
copy, and the click list is where faithfulness is checked:

- Every slide in order, the cover included, one chapter per slide unless the author says otherwise.
- Every title word for word, as the chapter title (`title_problems` may flag a number in front: ask
  before dropping it).
- Every number from the source's own data, not re-derived.
- Speaker notes carried into `notes`.
- Do not reword, drop or add anything without asking. The author chose those words with care and
  will notice. A caption longer than 12 words is a question for the author, not a licence to
  rewrite.

Improvements (a running example, a click split in two, a caption cut) go to the author as
suggestions after the faithful copy works.
