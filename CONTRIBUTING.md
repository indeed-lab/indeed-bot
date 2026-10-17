# Contributing to indeed-bot

Thanks for helping improve the implementation, the language coverage, or the documentation. The product agrees with everyone. Code review can still ask for changes.

## Set up a working copy

Use Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/), and [elan](https://github.com/leanprover/elan#installation). Run these commands from the repository root:

```sh
uv sync --extra dev
(cd lean && lake build)
uv run indeed --lang en "The development environment is ready."
```

The Lean version is pinned in [`lean/lean-toolchain`](lean/lean-toolchain). Keep changes compatible with that toolchain unless the contribution explicitly updates it.

## Keep the implementation boundary clear

Python handles language detection, random draws, the CLI, and process communication. Lean owns the reply pools and the selection function used by the executable. Keep one authoritative copy of the phrases in Lean; do not add a Python fallback reply catalog.

Only the selected locale and draw belong in the core protocol. The frontend does not need to send the user's text to Lean or persist prompts.

The browser edition consumes `web/replies.generated.js`, generated from the compiled Lean selector. Do not edit that file's phrases by hand. After changing the Lean catalog, rebuild the core and run `python scripts/export_web.py`; check the result with `--check`. Browser detection and sampling are ordinary JavaScript outside the Lean proof boundary. See [web/README.md](web/README.md) for the export contract.

The proved contract covers membership in the selected locale's pool, nonempty replies, and deterministic selection for a fixed locale and draw. Changes to language detection or random sampling need ordinary tests. Avoid describing them as formally verified unless the proof boundary actually changes.

## Change a reply or add a language

Keep phrases brief, idiomatic, and recognizably affirmative. Native-speaker review is welcome. A new language needs more than a translated phrase:

1. Add its locale and reply pool to the Lean core, preserving the required proofs.
2. Update the frontend's supported-language mapping and detection configuration.
3. Cover explicit selection and automatic detection with suitable integration tests.
4. Update the language tables and relevant examples in both READMEs.
5. Rebuild the core before running the Python suite.

The proof establishes membership in a pool. Reviewers still need to check that its phrases mean what the project says they mean.

## Validate your change

```sh
(cd lean && lake build)
uv run pytest
uv run python scripts/check_axioms.py
uv run python scripts/export_web.py --check
npm ci
npm run build:web
npm run test:web
```

Run the checks that exercise your change. A change to Lean code or reply pools requires a fresh core build before integration tests. The audit script invokes `lake env lean Audit.lean` and checks all six documented theorem audits. Inspect its output when modifying proofs; do not introduce `sorry`, unproved axioms, or an alternative unchecked selector to make a build pass. The [proof reference](lean/README.md) describes the current axiom dependencies.

Useful behavioral checks include explicit locale overrides, empty input, ambiguous-input fallback, reproducibility under a fixed seed, JSON metadata, and a missing core executable. Test meaningful outcomes and failure paths. Do not make an unseeded test depend on receiving one particular random phrase.

## Documentation and pull requests

Keep [`README.md`](README.md) and [`README.zh-CN.md`](README.zh-CN.md) in sync for supported languages, commands, guarantees, and limitations. The wording can be natural in each language rather than a literal translation. English and Chinese contributions are both welcome.

Open a pull request that explains the concrete behavior being changed, why it helps, and the checks you ran. For a detection change, include representative inputs and expected locale decisions. For a proof change, describe the property and whether its scope changed.

Keep the humor in the product story and the technical claims precise. We can parody a pitch deck without inventing adoption numbers or proving more than the code does.
