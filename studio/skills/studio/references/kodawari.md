# Kodawari

Kodawari is a Japanese word for a personal, almost stubborn devotion to getting the details right
in your own way. A film has it when you can tell that the maker put heart, effort and thought into
it, and when you can tell at once who made it. Those are one quality, not two. The signature comes
out of the care: hundreds of small decisions only this director would make, because they cared
about things nobody asked for. Care without signature is polish, beautiful and anonymous.
Signature without care is mannerism, a trick you recognise that doesn't move you.

This reference is the process for giving a film or a series kodawari. It is opt-in. Most films
are well served by `taste.md` alone, and that stays the default. Kodawari costs days of the
director's attention, not minutes, because the director has to see work, react and come back.

## Decide whether this film deserves it

Turn it on with `"kodawari": true` in `video.json` (or `studio new NAME --kodawari`) only when one
of these is true, and write the reason in the brief:

- It is the first film of a series that will have a recurring world, cast or look.
- It is the series' flagship, the film people will judge the series by.
- The director asked for it.

A one-off explainer, a quick update or a film whose series already has a bible does not need the
full process. A film made with `studio new --from` a kodawari film inherits the flag, the bible
and the ledger. It only adds what is new, and it reads the bible instead of running the routes again.

With the flag on, `studio shoot` refuses to start until `research/kodawari/bible.md` exists, and every
chapter job carries the bible next to the style frames.

## Two sources: the director and the subject

Kodawari has two sources, and a film needs both. **The director:** `taste.md` holds the rules the
director has settled. The ledger (below) holds the reactions that are not yet rules. **The
subject:** its real mechanisms, its nouns and its motions (packets, queues, workers, handshakes,
a slow disk). The motifs come from the subject, which is how 3Blue1Brown's pictures and
Ciechanowski's mechanisms become recognisable without any decoration.

The test for every choice is Tufte's: if a personal touch carries no meaning, cut it. A
charming character who has nothing to do with the mechanism is a failure even if the director
likes it. The small workers in "Where is the page made?" worked because they *are* the server's
processes. They queue, they fetch and they hand a finished page back.

## The process

**1. Fill the box.** Before designing anything, collect raw material in
`research/kodawari/box.md` (Twyla Tharp keeps a box for each dance). From the director: work they love in
any medium, with what they love about it in their own words, and the relevant `taste.md` rules.
From the subject: the real nouns and motions it is made of, from primary sources. Summaries of the
subject give generic pictures; the mechanism itself gives specific ones.

**2. Write the spine.** One plain sentence that every later choice answers to, for example "a
small, kind city of workers moving real traffic at night". Write it before drawing. It is not a
tagline and is never spoken; it is a test.

**3. Make routes, not variations.** Make three to five routes that differ in kind: different
worlds, different ways of drawing, different ideas of who the characters are. Not one idea in
five colour schemes. Four rounds of code-drawn character variations failed this way ("too
similar", "generic blobs", "flat"). Make each route cheap: one still, a two-second motion test, an
eight-bar music sketch, one narrated sentence. Put all the routes side by side on one page at the
same size. Bill Buxton's rule: many cheap sketches before one polished design.

Describe characters by personality before drawing them. One-liners such as "tiny but proud",
"very old and very slow, guards the heavy book" and "mostly pocket" produced characters the
director loved. Prompts that only described body shapes were "so lame". When code can't reach the
quality a route needs, write prompts for an image generator, have the director run them, and add
the results with `studio asset add` so their source is recorded. The director owns the design
idea; Studio owns the rig, the acting and the consistency.

**4. Ask for reactions, not specifications.** People recognise their taste when they see it; they
can't list it in advance (Brian Eno). Show the routes and ask what feels like them, what doesn't,
and why. Record every reaction in `research/kodawari/ledger.md`: the date, what was shown, the
director's words, the verdict and the reason. The reasons outlast the pictures, and the ledger
lets later films predict a choice before asking. Treat early versions as Pixar's "ugly babies":
the notes are honest and about the work, and the director decides.

Expect a mix. The director may love one route's world and another's characters. That is a
finding, not a failure. Combine them deliberately and show the combination.

**5. Write the bible.** `research/kodawari/bible.md` is what the rest of Studio obeys. Keep it short
enough to read in two minutes:

- **Spine:** the sentence from step 2.
- **Palette:** colours with one meaning each, for the dark and light grounds.
- **Line and drawing:** line weight, ink colour, wobble, what is drawn by hand and what stays
  crisp (screens and their content stay crisp).
- **Motion and acting:** how things move and how characters act, such as wind-up and catch,
  hesitation and small habits. The director liked the acting more than the drawings.
- **Cast:** each character, what it stands for in the mechanism, its personality in one line and
  its acting habits.
- **World:** the ground, the landscape and the props, drawn in the same hand as the cast.
- **Sound and music:** the music character and the settled mix level, and any tactile sounds
  particular to this world.
- **Narration:** any rules beyond `script.md`. Kodawari never means poetic narration.
- **Never:** a short list of things this world must not do, each with its reason.
- **Kit:** where the shared visual code lives and which version this film uses.

Bring the whole world to the same hand, not only the cast. The new cast first sat on a flat
UI-navy background with geometric props and clashed with it, until the ground and the props were
redrawn in the cast's line.

Build a new visual kit version *next to* the current one, never over it, so the director can
always go back. A shipped film keeps the kit it was made with.

**6. Prove it on one scene.** Before remaking or shooting a whole film, render the style frames
(`story.md`) in the bible's look. Put one of them beside the same moment drawn the generic way
(`taste.md` alone), unlabelled and in random order, and ask which one is theirs. Record the answer
in the ledger and the style-frame manifest. Shoot only after the director picks the kodawari frame
and can name a detail in it that also explains the subject.

## Delightful or tacky

Delight is specificity the subject earns: a worker who hesitates because the database is slow,
a palette taken from the real thing, a character whose habit is the mechanism's behaviour. Tacky
is ornament added on top: puns, winking mascots, "fun fact" asides, poetic imagery for a plain
subject, personality that gets in front of the explanation. When unsure, cut it. The rules in
`taste.md` still apply: windows only for a programmer at work, and pictures as plain as the subject.

## Keep it a series' asset

The bible and the ledger belong to the series, not to one film. `studio new --from` copies
`research/kodawari/bible.md`, `research/kodawari/ledger.md` and the flag. A later film adds to the
ledger and changes the bible only through a new reaction from the director, recorded with its
reason. When a reaction turns into a lasting preference for every film, not only this series,
fold it into `taste.md` and log it in `taste/notes.md`.

## Done

- The bible exists and is short. Given two bibles from different subjects, a reader who hasn't
  seen either film can say which film each describes.
- The routes are different in kind: someone who wasn't there calls them different worlds, not
  versions of one.
- Every bible line traces to a ledger entry or a subject fact.
- The director picked the kodawari frame in the blind comparison and named a detail that both
  feels like theirs and explains the subject.
