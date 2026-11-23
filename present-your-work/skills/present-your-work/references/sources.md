# Where the rules come from

Each rule traces to a source below. The sources are summarized only as far as the skill uses them.

## Short, and selected

- **Length raises confidence, not understanding.** Steyvers et al., "What Large Language Models
  Know and What People Think They Know" (Nature Machine Intelligence, 2025,
  [arXiv:2401.13835](https://arxiv.org/abs/2401.13835)). Longer explanations made people more
  confident in an answer without making them more accurate. Hence the word budget.
- **More detail can hide what matters.** Poursabzi-Sangdeh et al., "Manipulating and Measuring
  Model Interpretability" (CHI 2021, [arXiv:1802.07810](https://arxiv.org/abs/1802.07810)). Showing
  people more of a model's workings made them worse at noticing its mistakes, through overload.
  Hence selection over completeness, and no proof nobody asked for.

## Saying what the diff cannot

- **Explanations are contrastive, selected and causal.** Tim Miller, "Explanation in Artificial
  Intelligence: Insights from the Social Sciences" (Artificial Intelligence 267, 2019,
  [arXiv:1706.07269](https://arxiv.org/abs/1706.07269)). People ask why P rather than Q, want a
  few decisive causes rather than all of them, and expect the explanation to fit what they already
  believe. Hence the card's Why: the alternative rejected, the cause, not the chain of events.
- **A change description records what and why, for a reader who was not there.** Google's
  engineering practices, "Writing good CL descriptions"
  ([google.github.io/eng-practices](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)),
  and the Linux kernel's "Describe your changes"
  ([docs.kernel.org](https://docs.kernel.org/process/submitting-patches.html#describe-your-changes)),
  which also asks for the change's expected downsides and numbers for its tradeoffs.
- **Understanding is the product, not only the result.** William P. Thurston, "On Proof and
  Progress in Mathematics" (Bulletin of the AMS 30, 1994,
  [arXiv:math/9404236](https://arxiv.org/abs/math/9404236)): progress is measured by how far people
  understand, and a correct result nobody understands has delivered little of what matters. Hence
  the card's Key idea and Opaque lines.

## Order and economy

- **The answer first, after one clause of frame.** Barbara Minto, *The Pyramid Principle* (1987);
  the bottom line up front of US Army writing (AR 25-50); Joseph M. Williams, *Style: Lessons in
  Clarity and Grace*, on a short shared context before the point. Readers given the topic before a
  passage understand it far better than readers given it after (Bransford and Johnson, 1972,
  [doi:10.1016/S0022-5371(72)80006-9](https://doi.org/10.1016/S0022-5371%2872%2980006-9)).
- **Not the journey.** Simon Peyton Jones, "How to write a great research paper"
  ([Microsoft Research](https://www.microsoft.com/en-us/research/academic-program/write-great-research-paper/)):
  "Do not recapitulate your personal journey of discovery." Williams: most readers are not
  interested in how you thought through an issue. Hence the log rule.
- **Confess immediately.** Paul Halmos, "How to Write Mathematics" (1970): state a weakness where
  it matters, not at the end. Hence the catch beside the answer.
- **Concise, scannable, objective.** Morkes and Nielsen, "Concise, SCANNABLE, and Objective: How to
  Write for the Web" (1997, [NN/g](https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/)):
  concise text, scannable layout and objective language each measurably improved usability. Hence
  the word budget and the tone rule. Readers also prefer a middle density to maximal compression
  (Adams et al., "From Sparse to Dense: GPT-4 Summarization with Chain of Density Prompting", 2023,
  [arXiv:2309.04269](https://arxiv.org/abs/2309.04269)), hence a floor as well as a ceiling.
- **The concrete case before the name.** Worked examples outperform abstract instruction for
  readers new to a subject (Sweller's cognitive load theory; Barbieri et al., Educational
  Psychology Review, 2023). Hence one concrete case for the key idea.
- **Private names.** The curse of knowledge (Camerer, Loewenstein and Weber, Journal of Political
  Economy 97, 1989): someone who knows a thing cannot set it aside when judging what others know,
  so a writer cannot find their own private labels by rereading. Hence a script finds them.

## The voice

- **What marks text as machine-written today.** Wikipedia's "Signs of AI writing" (WikiProject AI
  Cleanup) catalogues the structures: negative parallelism ("not X, but Y"), the rule of three,
  trailing participial phrases, copula avoidance, colon reveals and bold lead-ins. Karl Weinmeister's
  evaluation of humanizer skills (2026, [method and catalogs](https://github.com/kweinmeister/scripts/tree/main/evals/humanizer-skills))
  measured current models against human writing on the same facts: *specifically* 5.4 times as
  often, *essential* 8.3 times, *though* 5 times, and *furthermore*, *vital* and *alongside* almost
  absent from the human text, while the old markers (*delve*, *tapestry*) had become rare. Hence
  the voice rule's word list, applied to clusters rather than single uses.
- **Drafting decides most of it.** The same evaluation found that a plain editing instruction
  ("Edit to remove signs of AI writing, if there are any. Keep the meaning, facts, and register")
  removed about a third of the tells while leaving 92% of human-written text untouched, that no
  editing skill escaped the trade-off between removing tells and rewriting good text, and that
  the drafting model mattered far more than any editing pass. Hence the voice rules in the drafting
  step and one light reread, not a heavy rewrite.
- **Rules that can be counted, and examples over bans.** Banned-word lists go stale and invite
  synonyms; countable constraints (one idea per sentence, a length limit) and examples of the
  target voice hold up better. Hence the sentence-length limit and `voice.md`.
- **Write close to speech.** William Zinsser, *On Writing Well*, and Paul Graham, "Write Simply"
  ([paulgraham.com](https://paulgraham.com/simply.html)): write the way you would say it to a
  friend. Hence a report told to the person, in the first person, with contractions.

## Handing work back

- **A structured handoff prevents errors at no cost in time.** Starmer et al., "Changes in
  Medical Errors after Implementation of a Handoff Program" (New England Journal of Medicine 371,
  2014, [doi:10.1056/NEJMsa1405556](https://doi.org/10.1056/NEJMsa1405556)): a handoff that gives
  the status, the action list and the contingencies cut medical errors by 23% across nine
  hospitals, with no longer handoffs. Hence the ending: what the reader now has to decide or do,
  and the if-then that would change it.
