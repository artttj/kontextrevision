# What the research actually says

Two studies are cited constantly for "keep your AGENTS.md short". They disagree.

| Paper | Finding |
|---|---|
| [Lulla et al., arXiv 2601.20404](https://arxiv.org/abs/2601.20404) | AGENTS.md helps: median runtime down 28.6%, output tokens down 16.6% |
| [Gloaguen et al., arXiv 2602.11988](https://arxiv.org/abs/2602.11988), ETH Zurich SRI | No completion benefit, over 20% higher inference cost |

The disagreement comes from what each measured. Gloaguen counted total inference
tokens including the file itself. Lulla counted output tokens and runtime once
the agent already had the context. They also tested different agent families,
Codex against Claude. Both are arXiv preprints. Neither has been peer reviewed.

Supporting work:

- [arXiv 2605.10039](https://arxiv.org/pdf/2605.10039), instruction adherence against four file-structure variables
- [arXiv 2606.20512](https://arxiv.org/pdf/2606.20512), probe-and-refine tuning of repository guidance
- [arXiv 2607.27250](https://arxiv.org/html/2607.27250v1), two-agent ablation on real repositories

## Measured against 250 real repositories

From this project's own corpus scan, documented in `docs/proof/`:

| Finding | Number |
|---|---|
| `AGENTS.md` median / p90 / largest | 1,027 / 4,100 / 28,430 tokens |
| `CLAUDE.md` median / p90 / largest | 1,387 / 5,692 / 28,592 tokens |
| `SOUL.md` median / p90 / largest | 641 / 2,665 / 4,599 tokens |
| Command references pointing at nothing | 3.6% |
| Sections in a single file, maximum | 92 |
| Files containing invisible Unicode | 0 of 250 |

## What to claim

Do not tell the user their agent will get faster. The evidence does not support
it and two preprints actively contradict each other on the point.

The defensible claim is narrower: these files are injected on every session, so a
line that does not change behavior bills them on every session. Report the token
delta and let the number carry the argument.
