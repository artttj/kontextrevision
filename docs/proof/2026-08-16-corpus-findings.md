# What 250 real agent instruction files look like

**Date:** 2026-08-16
**Author:** Artem Iagovdik

## Method

The corpus contains 100 `AGENTS.md`, 100 `CLAUDE.md`, and 50 `SOUL.md` files
from 250 distinct repositories. Files came from GitHub code search in API result
order, with one file retained per repository across the whole sample. Each file
was fetched from its repository's current default branch and scanned with
`scan.py`.

The corpus was re-measured after section identity changed from one normalized
body hash to separate exact and normalized hashes. Preserving source line
endings raised the largest `SOUL.md` estimate and corpus total. Section and
command counts remained unchanged.

Token counts use the scanner's documented character-count estimate. The p90 is
the nearest-rank 90th percentile. GitHub search order and repository contents
change, so these figures describe the dated snapshot rather than a permanent
population estimate.

## Size

| File | Count | Median | p90 | Largest |
|---|---:|---:|---:|---:|
| `AGENTS.md` | 100 | 1,044 tok | 4,100 tok | 28,430 tok |
| `CLAUDE.md` | 100 | 1,387 tok | 5,095 tok | 28,592 tok |
| `SOUL.md` | 50 | 641 tok | 2,647 tok | 4,710 tok |

The corpus contains an estimated 473,460 tokens. The median file has 9 Markdown
sections, and the largest has 92.

[`joe-bell/cva`](https://github.com/joe-bell/cva) remains the clearest large-file
example in the sample at an estimated 8,176 tokens.

## Commands are references, not verdicts

The revised extractor found 738 recognized command references across the 250
files. This is not a missing-command count.

Determining whether a command exists requires resolving the repository's actual
manifest. Makefile includes can nest, and included paths can live in git
submodules that are unavailable through a raw file request. Package scripts can
also be inherited through workspaces. The scanner reports references for later
inspection and does not claim that any command is broken.

Earlier measurement attempts demonstrated why that boundary matters:

- prose such as `make sure` can resemble a command without code-span filtering
- one-level Makefile inspection misses nested includes
- raw HTTP cannot see files stored only in a git submodule
- fenced shell comments can resemble Markdown headings

The published missing-command percentage was removed after command extraction
expanded. Reusing it with a broader parser would mix two different measurements.

## Negative check

None of the 250 files contained zero-width spaces, zero-width joiners,
byte-order marks, or non-breaking spaces. The project does not include an
invisible-Unicode cleanup feature on this evidence.

## Reproducing the scan

```bash
python3 skills/kontextrevision/scripts/scan.py <downloaded-corpus-root>
```

The scanner emits file roles, scopes, harness coverage, per-harness token tiers,
load conditions, byte sizes, token estimates, normalized full-file hashes, exact
and normalized section hashes, recognized commands, and referenced paths. It
never emits file bodies.
