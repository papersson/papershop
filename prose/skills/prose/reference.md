# prose: grounding reference

Calibration for the `prose` skill: the tell catalog, the principles with attribution, and
before/after pairs. Distilled from the craft canon (Orwell, Strunk, Zinsser, Pinker, Sword,
Williams, Provost, Graham, McEnerney, Nielsen, Feynman, Scott Alexander, docs craft, and the
AI-tell literature). Every rule here is a heuristic toward clarity and honesty, not a law. Orwell's
sixth rule governs them all: break any of these sooner than say anything outright barbarous.

## The tells, in order of how reliably they damn a text

**Lexical.** Inflated cluster: *delve, crucial, pivotal, intricate, interplay, tapestry, testament,
underscore, showcase, vibrant, foster, garner, enhance, leverage, seamless, robust, align with,
bolster, illuminate, transcend, navigate, grapple, embody, intertwine.* Copula avoidance: "serves
as a", "stands as", "represents", "functions as" where "is" belongs (Wikipedia, "Signs of AI
Writing"). Marketing verbs: *boasts, offers, features* for *has*. None is wrong alone; the density
is the signature.

**Structural.** Negative parallelism ("Not only X, but also Y"). The rule of three (adjective,
adjective, and adjective). Participial synthesis: sentences ending "...highlighting the need for...",
"...underscoring the complexity of...", which perform analysis without making a claim. The
challenge/future-directions coda (achievement, vague challenge, unattributed experts, "looking
ahead... potential... collaboration") that appends to any topic. The grand human-condition sweep.
Hollow significance: *groundbreaking, invaluable, indelible, vital, profound, pioneering.*

**Statistical.** Low burstiness: uniform sentence length and shape; the same medium rhythm
throughout (GPTZero). Low perplexity: the high-probability word every time. Em-dash overuse. Caveat
(Pangram Labs): uniform density is correct in legal, medical, reference, and API-doc genres; there
it is not a tell.

## The pathologies behind the tells (why they fail)

- **Vagueness / abstraction.** "A mass of Latin words falls upon the facts like soft snow, blurring
  the outlines and covering up all the details" (Orwell).
- **Latinate inflation.** *Utilize, facilitate, constitute, exhibit* dress simple statements to
  sound impartial. "They work ceremonially, not semantically" (Becker).
- **Nominalization / zombie nouns.** *Implementation, operationalization, facilitation* drain the
  action and hide the actor (Sword). Fix by finding characters and actions (Williams).
- **Curse of knowledge.** "The better you know something, the less you remember about how hard it
  was to learn" (Pinker). The single best explanation for why good people write bad prose.
- **Clutter.** "Clutter is the disease of American writing" (Zinsser). Often evasion, not confusion.
- **Dead metaphors.** Phrases "used because they save people the trouble of inventing phrases for
  themselves" (Orwell): *toe the line, ride roughshod, swan song, hotbed.*
- **Ritual hedging.** "Somewhat, nearly, relatively, apparently peppering the prose" (Pinker) as
  armor, not as genuine uncertainty.
- **Metadiscourse.** "If you might add, add it. If it should be pointed out, point it out" (Zinsser).
- **Insincerity, the root.** "The great enemy of clear language is insincerity" (Orwell). Some bad
  writing can't be edited; the writer has to commit to a position.

## The principles, by theme

**Concreteness.** "Prefer the specific to the general, the definite to the vague, the concrete to
the abstract" (Strunk, Rule 12). Name the thing: not the dog, but the dog named Penny (Clark). The
concrete *is* the argument, not just the illustration (Strunk via Spencer).

**Cadence.** Vary sentence length deliberately; uniform length drones, variation sings (Provost).
Read it aloud and see if a human could say it without being a robot with no need to breathe
(Graham, Alexander). Parallelism is rhythm when chosen, monotony when accidental: the test is
whether you can say why the repetition is there.

**Coherence.** Given before new: open each sentence with something the reader already holds, then
extend into the new (Pinker). Connect through content; you rarely need "Furthermore" or
"Additionally". Follow the most interesting thread (Graham).

**Voice.** Write close to how you'd say it to a friend: "When you write something you wouldn't say,
you'll hear the clank as it hits the page" (Graham). Classic style treats writer and reader as
equals and makes the reader feel like a genius, not a dunce (Pinker; Thomas & Turner). Not
condescending ("you could not understand this"), not obsequious ("I hope this helps"). Style is
organic, not applied: "there is no style store" (Zinsser).

**Cutting.** "Vigorous writing is concise" (Strunk, Rule 13). "If it is possible to cut a word out,
always cut it out" (Orwell). Substitute down: *numerous → many, facilitate → ease, sufficient →
enough, attempt → try.* Prefer the active voice with a named actor, but keep the passive when the
agent is genuinely unknown or irrelevant (Strunk's own caveat; and Pullum's correction that Strunk
& White misidentify their own passive examples, so absorb the intuition, not the grammar). Apply
style rules in revision, never while drafting (Nielsen).

**Honesty.** "Useful writing makes claims that are as strong as they can be made without becoming
false" (Graham): "Pike's Peak is near the middle of Colorado", not "somewhere in Colorado".
Qualifications are precision tools, not shields; pick the one that correctly narrows the claim. "The
English language hates the slightest whiff of dishonesty... It punishes you by making your writing
worse" (Alexander). Acknowledge the limits of your knowledge plainly (Nielsen).

## Technical and explanatory writing

- **Build the reader's model, not a record of yours.** "Good writing isn't an intrinsic property of
  the text. It's a quality of the relationship between the reader and the text" (Nielsen). In
  professional writing the point is to change what the reader's community believes, not to display
  understanding: "Nobody cares what ideas you have" (McEnerney).
- **Scene before symbol.** Describe the experiment before naming "the rabbit illusion" (Pinker).
  Feynman: "even if you know all those names for [the bird], you still know nothing about the bird".
  Introduce a term only after the reader knows its referent. Start hard points with a concrete
  example; start very hard points with several (Alexander).
- **Demonstrate interest, don't announce it.** "Interesting", "notably", "importantly" "subtly
  signal the opposite" (Nielsen). Let the concrete image do the argumentative work.
- **Honesty is a technical requirement.** "The first principle is that you must not fool yourself,
  and you are the easiest person to fool" (Feynman). Cargo-cult prose uses "therefore", "this shows
  that" without the connective tissue.
- **Docs: separate by purpose, write for the human.** Tutorials teach (imperative, "we will"),
  reference is austere neutral description, explanation may carry opinion (Procida, Diataxis). Cut
  the minimizers: "simply", "easy", "just" punish the reader for whom it isn't (Google style guide).

## Before / after

**Nominalization.**
- Before: "I conducted an investigation of the rules governing effective rewriting practices."
- After: "I investigated rules for rewriting." (Nielsen)

**Abstraction → concrete.**
- Before: "He showed satisfaction as he took possession of his well-earned reward."
- After: "He grinned as he pocketed the coin." (Strunk, Rule 12)

**The full Latinate fog (what to undo).**
- Before: "Objective consideration of contemporary phenomena compels the conclusion that success or
  failure in competitive activities exhibits no tendency to be commensurate with innate capacity."
- After (the original it was inflated from): "I returned, and saw under the sun, that the race is
  not to the swift, nor the battle to the strong." (Orwell; Ecclesiastes)

**AI tell density.**
- Before: "Additionally, it is important to note that this groundbreaking approach not only enhances
  efficiency but also fosters a vibrant ecosystem, highlighting the crucial role of collaboration."
- After: state the one real claim, plainly: "The approach cuts build time by 40%."

**Copula avoidance.**
- Before: "The furnaces serve as a constant reminder of the camp's purpose."
- After: "The furnaces are a constant reminder of the camp's purpose." (Steere)

**Marketing verbs + rule of three.**
- Before: "The library boasts a comprehensive suite of features: seamless integration, robust
  performance, and intuitive design."
- After: "The library integrates in one line and stays fast under load."

**Ritual hedging.**
- Before: "And yet, on balance, affirmative action has, I think, been a qualified success."
- After: commit to the claim, with one real qualifier if warranted. (Zinsser's specimen of five
  hedges in thirteen words)

**Metadiscourse.**
- Before: "It is important to note that, while the foregoing analysis has shed light on several key
  dimensions, it is beyond the scope of this paper to provide a comprehensive account."
- After: delete it; the argument strengthens.

**Uniform rhythm.**
- Before: "AI is transforming industries. Models are becoming sophisticated. These offer benefits.
  Organizations are adopting them. The implications are significant." (every sentence 6-9 words)
- After: vary the lengths; let one sentence be three words and one carry a clause to a close.

**Passive with hidden agents.**
- Before: "The service is queried, and an acknowledgment is sent."
- After: "Send a query to the service. The server sends an acknowledgment." (Google style guide)

**Vague safety-seeking.**
- Before: "This is a complex issue with many factors to be considered."
- After: name the factors and take a position, or cut the sentence. (Graham)
