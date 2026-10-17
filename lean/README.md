# Formal guarantees

The Lean executable is the reply engine used by indeed-bot. The Python layer
detects a language and supplies a random draw; `indeed-core` selects the reply
from the catalogue in [`Indeed.lean`](Indeed.lean). There is no second copy of
the selector or phrase catalogue in Python.

## Build and audit

Lean **4.35.0** is pinned in `lean-toolchain`. There are no third-party Lean
dependencies. From this directory:

```sh
lake build
lake env lean Audit.lean
```

The first command checks the proofs and produces `.lake/build/bin/indeed-core`.
The second prints the kernel-level axiom dependencies of each guarantee.
Warnings are errors during the Lake build. The proofs contain no `sorry`,
`admit`, custom axioms, or `native_decide`.

## What is proved

| Theorem | Statement |
| --- | --- |
| `Indeed.pool_length_pos` | Every supported locale has a nonempty reply pool. |
| `Indeed.pool_member_nonempty` | Every string in a locale's pool is nonempty. |
| `Indeed.selectionIndex_lt` | `draw % pool.length` is always a valid index. |
| `Indeed.selectReply_mem` | The selected string belongs to the supplied locale's pool. |
| `Indeed.selectReply_nonempty` | The selected string is never empty. |
| `Indeed.selectReply_deterministic` | Equal locale and draw inputs produce equal reply text. |

The pure function `Indeed.selectReply` is used directly by `Main.lean`, which
serializes its result. The membership theorem therefore applies to the source
function compiled into the executable, rather than a separately maintained
model of that function.

The audit reports no axioms for four theorems. The two string-nonemptiness
theorems depend only on Lean's standard `propext` axiom. They do not introduce
an assumption that a selected string is in the pool.

## Proof boundary

The input locale is a member of the explicit `Locale` type, and the draw is an
arbitrary natural number. The proofs cover these pure values and the curated
catalogue. They do **not** establish:

- that language detection matches the user's actual language;
- that a caller's draws are random, unbiased, or unpredictable;
- that a sentence is semantically affirmative or that the user's claim is true;
- correctness of argument parsing, JSON encoding, subprocess transport,
  Python code, or the web interface.

As with ordinary compiled Lean programs, execution relies on the Lean compiler,
runtime, and operating system behaving correctly. The formal theorem is not an
end-to-end proof of the deployed application. Integration tests separately
exercise the executable's JSON protocol and the Python boundary.

## Executable protocol

```sh
.lake/build/bin/indeed-core catalog
.lake/build/bin/indeed-core reply zh 1
```

`catalog` emits one JSON object mapping locale codes to phrase arrays. `reply`
emits one JSON object:

```json
{"index":1,"locale":"zh","pool_size":5,"text":"太对了。"}
```

Supported locale codes: `en`, `zh`, `ja`, `ko`, `es`, `fr`, `de`, `pt`, `ru`,
`ar`. A draw must contain one or more ASCII decimal digits. Arbitrarily large
natural numbers are supported; leading zeroes are accepted. An invalid command,
locale, or draw produces a JSON object with an `error` string on stderr and
exit status `2`, with no normal output. `--help`, `-h`, and `help` print usage
and exit successfully.

The catalogue is the single source of truth. To add a locale or edit its
phrases, update `Locale`, its parsing/serialization, `locales`, and `pool`, then
rebuild, rerun the audit, and run the repository's integration tests.
