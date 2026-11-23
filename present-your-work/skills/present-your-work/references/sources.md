# Where the rules come from

Each rule traces to a source below. The sources are summarized only as far as the skill uses them.

## Making checking cheaper than trusting

- **Explanations raise acceptance whether the answer is right or wrong.** Bansal et al., "Does the
  Whole Exceed its Parts? The Effect of AI Explanations on Complementary Team Performance" (CHI
  2021, [arXiv:2006.14779](https://arxiv.org/abs/2006.14779)). Confidence information helped
  teams; explanations mostly raised agreement with the AI, wrong answers included. Hence: tie each
  claim to its evidence rather than argue for it.
- **Explanations help when they make verification cheaper.** Vasconcelos et al., "Explanations
  Can Reduce Overreliance on AI Systems During Decision-Making" (CSCW 2023,
  [arXiv:2212.06823](https://arxiv.org/abs/2212.06823)). Hence evidence in the sentence that makes
  the claim, where checking it costs the least.
- **Length raises trust without raising accuracy.** Steyvers et al., "What Large Language Models
  Know and What People Think They Know" (Nature Machine Intelligence, 2025,
  [arXiv:2401.13835](https://arxiv.org/abs/2401.13835)). Longer explanations raised people's
  confidence in an answer, not their accuracy; wording that matched the model's own confidence
  narrowed the gap. Hence the word budget and the evidence states.
- **More detail can hide errors.** Poursabzi-Sangdeh et al., "Manipulating and Measuring Model
  Interpretability" (CHI 2021, [arXiv:1802.07810](https://arxiv.org/abs/1802.07810)). A more
  transparent model made people worse at catching its mistakes. Hence selection over completeness.
- **"Tests pass" is weak evidence on its own.** Patches that pass a benchmark's tests can still
  differ from the correct behaviour (Wang, Pradel and Liu, "Are 'Solved Issues' in SWE-bench Really
  Solved Correctly?", 2025, [arXiv:2503.15223](https://arxiv.org/abs/2503.15223)), and agents can
  make tests pass by changing them (Zhong et al., "ImpossibleBench", 2025,
  [arXiv:2510.20270](https://arxiv.org/abs/2510.20270)). Hence the rule that changed test files
  are named.

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

## Handing work back

- **A structured handoff prevents errors at no cost in time.** Starmer et al., "Changes in
  Medical Errors after Implementation of a Handoff Program" (New England Journal of Medicine 371,
  2014, [doi:10.1056/NEJMsa1405556](https://doi.org/10.1056/NEJMsa1405556)): a handoff that gives
  the status, the action list and the contingencies cut medical errors by 23% across nine
  hospitals, with no longer handoffs. Hence the ending: what the reader now has to decide or do,
  and the if-then that would change it.
