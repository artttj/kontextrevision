# What 250 real agent instruction files look like

**Date:** 2026-08-16
**Author:** Artem Iagovdik
**Method:** GitHub code search for `AGENTS.md`, `CLAUDE.md`, `SOUL.md`, one file per repo, 250 repos. Scanned with `scan.py`. Command claims verified against each repo's real `package.json` and `Makefile`.

Every number here survived a deliberate attempt to break it. Two of my first four "findings" turned out to be false and were thrown out. That process is documented at the bottom, because it is the most useful part.

## Size

These files are injected into the system prompt on **every session**. Size is a recurring cost, not a one-time one.

| File | Median | p90 | Largest |
|---|---|---|---|
| `AGENTS.md` (n=100) | 1,027 tok | 4,100 tok | 28,430 tok |
| `CLAUDE.md` (n=100) | 1,387 tok | 5,692 tok | 28,592 tok |
| `SOUL.md` (n=50) | 641 tok | 2,665 tok | 4,599 tok |

Median sections per file: 9. Largest: **92 sections in one file.**

Corpus total: 465,901 tokens across 250 files.

### The clearest example

[`joe-bell/cva`](https://github.com/joe-bell/cva) (6,874★) ships an **8,176-token `AGENTS.md`**. Nothing is wrong with it. It is simply read, in full, at the start of every session anybody runs against that repo.

## Dead commands

Instruction files tell agents which commands to run. Some of those commands do not exist.

| Runner | Files checked | Commands checked | Dead |
|---|---|---|---|
| npm/yarn/pnpm | 26 | 129 | 6 (4.7%) |
| make | 20 | 94 | 2 (2.1%) |

**8 of 223 verifiable command references (3.6%) point at nothing.** A further 11 files with `make` commands were **skipped rather than judged**, because their Makefiles could not be fully resolved (see methodology).

### Verified cases

| Repo | File says | Reality |
|---|---|---|
| [RedHatInsights/insights-chrome](https://github.com/RedHatInsights/insights-chrome) | `npm run test:e2e` (CLAUDE.md:134) | No such script. `package.json` has `test:playwright`, `test:ct`. No workspaces. |
| [egraphs-good/egglog](https://github.com/egraphs-good/egglog) (817★) | `make major` | Makefile has no includes. Targets are `all`, `nightly`, `test`, `coverage`, `doctest`, `nits`, `docs`, `graphs`, `json`. |
| [thumbor/libthumbor](https://github.com/thumbor/libthumbor) | `make test`, `make flake8` | Makefile has no includes. Targets are `unit`, `coverage`, `setup`, `black`, `pylint`, `lint`. |

## Two things that turned out not to be problems

**Invisible Unicode: 0 of 250 files.** Zero-width spaces, non-breaking spaces, and Unicode tag characters appear in none of them. A separate scan of 85 local instruction files also found zero. 335 files, no hits. A planned scrubbing feature was cut on this evidence.

**Cross-repo copy-paste: 2.8% of files.** Only 32 byte-identical blocks appear in more than one repo, touching 7 of 250 files. People are writing these files themselves rather than copying templates.

## Methodology, including what went wrong

The first measurement claimed **12.9%** of commands were dead. That number was wrong twice over.

**Error 1: prose parsed as commands.** The extractor matched `make sure` and `npm run ...` in ordinary sentences. Fixed with a stopword filter. 12.9% → 11.6%.

**Error 2: Makefile includes not followed.** The first run reported that Google's [`config-sync`](https://github.com/GoogleContainerTools/config-sync) referenced three `make` targets that did not exist. All three exist in `Makefile.build`, which the root Makefile includes at line 330. Following includes one level: 11.6% → 8.9%.

**Error 3: nested includes and git submodules.** Even one-level include-following was not enough.

- [`openshift/ocm-agent`](https://github.com/openshift/ocm-agent): targets live **two levels deep**, in `boilerplate/openshift/osd-container-image/standard.mk`. Reported as missing. They exist.
- [`exoscale/cli`](https://github.com/exoscale/cli): `go.mk` is a **git submodule**, so its contents 404 over raw HTTP. Reported as missing. They exist.

Both were false accusations against real companies, caught before publication. The final measurement refuses to judge any Makefile it cannot fully resolve, which is why 11 files are skipped rather than counted. **8.9% → 3.6%.**

**Error 4: fenced code blocks parsed as headings.** A `# comment` inside a ```` ``` ```` block was treated as a real ATX heading. This inflated the section counts (the "largest file" appeared to have 146 sections; it has 92) and leaked comment text verbatim into a digest that is supposed to never contain file bodies.

**Error 5: prose matched as commands.** `make sense`, `make progress`, and `pytest suite` were all being counted as command references. Command extraction is now restricted to inline code spans and fenced blocks, with trailing `# comments` stripped.

Final: **12.9% → 3.6%.** The headline number dropped by 72% under scrutiny. Every drop came from a bug that would have produced a false public claim about somebody's repository.

## Reproducing

```bash
python3 skills/kontextrevision/scripts/scan.py <path>
```

Emits a JSON digest per file: role, byte size, token estimate, section headings with whitespace-stable content hashes, referenced commands, referenced paths. Never emits file bodies, so a 250-file corpus stays readable in one pass.
