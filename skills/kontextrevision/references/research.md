# What the research actually says

Studies of repository instruction files disagree on whether the files improve
coding outcomes. The defensible conclusion is not that shorter is always better.
It is that guidance should preserve specific knowledge the agent cannot reliably
discover and avoid requirements that do not help the task.

## Direct evidence

| Paper | Setting | Finding |
|---|---|---|
| [Lulla et al., arXiv 2601.20404](https://arxiv.org/abs/2601.20404) | 124 pull requests across 10 repositories | Adding `AGENTS.md` was associated with 28.6% lower median runtime and 16.6% fewer output tokens, with comparable completion behavior. |
| [Gloaguen et al., arXiv 2602.11988](https://arxiv.org/abs/2602.11988) | SWE-bench Lite plus 138 CTXbench tasks across several agents and models | Generated context files produced no statistically significant completion gain and raised cost by 20–23%. Human files performed 2.4% better than no context on average, but that difference was not statistically significant. |
| [McMillan, arXiv 2605.10039](https://arxiv.org/abs/2605.10039) | 1,650 Claude Code sessions and 16,050 function-level observations | File size, instruction position, file architecture, and adjacent conflicts produced no detectable adherence differences within the tested conditions. |
| [Shepard and Albrecht, arXiv 2606.20512](https://arxiv.org/abs/2606.20512) | SWE-bench Verified with Qwen3.5-35B-A3B | Probe-refined guidance reached a 33.0% mean resolve rate, compared with 28.3% for its static starting point and 25.5% without guidance. The result is tied to one tuning method and primary model. |
| [Khatri, arXiv 2607.27250](https://arxiv.org/abs/2607.27250) | 288 Claude Code and Codex runs over 17 tasks from 3 repositories | Context strategy did not measurably change correctness. The small task and repository sample limits generalization. |

These studies count different costs, use different agents, and test different
kinds of guidance. Lulla measures runtime and output tokens after context is
available. Gloaguen includes the wider inference cost and finds that instructions
change behavior by increasing exploration and testing. Shepard and Albrecht test
guidance refined against synthetic bug probes rather than ordinary static files.
McMillan manipulates file structure, while Khatri ablates context strategy on a
small set of real tasks.

All five are preprints. Their disagreement is evidence against a universal
performance promise, not evidence that repository guidance never matters.

## Adjacent evidence

- [Liu et al., Lost in the Middle](https://arxiv.org/abs/2307.03172) shows that
  long-context retrieval depends on the position of relevant information. Its
  question-answering and retrieval tasks do not test coding-agent instruction
  files.
- [Robinette et al., VerIFY](https://aclanthology.org/2026.findings-eacl.254/)
  measures instruction-following failures in long multi-turn contexts. It is
  peer reviewed, but evaluates open-source conversational models rather than
  repository coding tasks.
- [Jiang et al., LLMLingua](https://aclanthology.org/2023.emnlp-main.825/) and
  [LongLLMLingua](https://aclanthology.org/2024.acl-long.91/) show that learned
  prompt compression can reduce cost while preserving or improving results on
  their benchmarks. Token-level learned compression is not equivalent to an
  editorial rewrite of `AGENTS.md`.

This work explains plausible mechanisms for distraction and compression, but it
does not establish that shortening an instruction file improves coding outcomes.

## Measured against 250 real repositories

From this project's own corpus scan, documented in `docs/proof/`:

| Finding | Number |
|---|---|
| `AGENTS.md` median / p90 / largest | 1,044 / 4,100 / 28,430 tokens |
| `CLAUDE.md` median / p90 / largest | 1,387 / 5,095 / 28,592 tokens |
| `SOUL.md` median / p90 / largest | 641 / 2,647 / 4,710 tokens |
| Recognized command references | 738, without a missing-command verdict |
| Sections in a single file, maximum | 92 |
| Files containing invisible Unicode | 0 of 250 |

## What to claim

Do not promise that revision makes an agent smarter or faster. Do not use file
length alone as a quality score. Preserve operational knowledge that is specific
to the repository, remove redundant or ineffective context, report the token
delta, and let users evaluate whether the remaining instructions change behavior.
