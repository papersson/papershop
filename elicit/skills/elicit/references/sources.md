# Where the rules come from

Each rule in the skill traces to a source below or to the tests described in `../DESIGN.md`. The sources are summarized only as far as the skill uses
them. Numbers come from the papers' own text and tables, read in October 2026.

## Answering only the question asked

- Wu and Fard, HumanEvalComm (2024, arXiv:2406.00215). Given ambiguous, inconsistent or incomplete
  coding problems, more than 60% of responses still wrote code instead of asking a question.
- Laban, Hayashi, Zhou and Neville, LLMs Get Lost in Multi-Turn Conversation (2025,
  arXiv:2505.06120). On underspecified multi-turn tasks performance fell 39% on average; models
  commit to early assumptions. Giving all the information in one turn largely restores it.
- Zhang, Knox and Choi, Modeling Future Conversation Turns to Teach LLMs to Ask Clarifying
  Questions (ICLR 2025, arXiv:2410.13788). Preference labelling judges a reply on its prior
  context, which rewards answering over asking.
- Vero et al., BaxBench (ICML 2025, arXiv:2502.11844). Exploit-tested backends: about half of
  the correct programs were exploitable. Models are "capable but not attending" to security; a
  reminder naming the scenario's CWEs gave the best security but cost functional correctness.

Used for: settling the questions an expert would ask first, reaching the fields the request does not
name, and keeping functional checks beside hardening ones.

## Self-critique works only against something

- Huang et al., Large Language Models Cannot Self-Correct Reasoning Yet (ICLR 2024,
  arXiv:2310.01798). Intrinsic self-correction did not help and sometimes hurt (GPT-4 on GSM8K,
  95.5 to 89.0). Stating the requirements in the first prompt scored 81.8 in one call against
  67.0 after seven rounds of self-correction.
- Gou et al., CRITIC (ICLR 2024, arXiv:2305.11738). Critique with tools gained 7.7 F1 on QA; the
  same loop without tools changed F1 by -0.03 and +2.33.
- Tyen et al., LLMs cannot find reasoning errors, but can correct them given the error location
  (2023, arXiv:2311.08516). The bottleneck is finding the error.
- Cook et al., TICKing All the Boxes (2024, arXiv:2410.03608). Self-refinement against generated
  yes/no checklists gained 7.8 points on LiveBench reasoning where plain Self-Refine degraded.
- Tony et al., Prompting Techniques for Secure Code Generation (ACM TOSEM, arXiv:2407.07064).
  Naming specific CWEs cut weaknesses about 60%; a security-focused critique-and-revise pass cut
  them 78% for GPT-4. Recognizing a known weakness class is easier than finding a reasoning error.

Used for: criteria written into the brief before the work, and checks that name specific weakness
classes rather than asking generally for care.

## Personas and the prompter's apparent level

- Zheng et al., When "A Helpful Assistant" Is Not Really Helpful (Findings of EMNLP 2024,
  arXiv:2311.10054). 162 personas on multiple-choice MMLU gave no accuracy gain over no persona.
- Kim, Yang and Jung, Persona is a Double-edged Sword (2024, arXiv:2408.08631). Role-play prompts
  degraded reasoning on 7 of 12 datasets.
- Tony et al. (above). The "act as a security expert" style prompt produced the most weaknesses of
  every technique tested.
- Xu et al., ExpertPrompting (2023, arXiv:2305.14688). An instruction-specific description of what
  an expert would attend to was preferred by a GPT-4 judge, on answers about 27% longer.
- Poole-Dayan, Roy and Kabbara (2024, arXiv:2406.17737) and Perez et al. (2022, arXiv:2212.09251).
  Answer quality drops for users who appear less educated or less fluent.

Used for: the panel's principles written into the brief instead of a role given to the doer, and
naming the purpose and audience first. None of these studies tests open-ended thoroughness, which is
the case this skill targets.
