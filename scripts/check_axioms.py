#!/usr/bin/env python3
"""Compile the proof audit and reject missing audits or nonstandard axioms."""

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "Indeed.pool_length_pos",
    "Indeed.pool_member_nonempty",
    "Indeed.selectionIndex_lt",
    "Indeed.selectReply_mem",
    "Indeed.selectReply_nonempty",
    "Indeed.selectReply_deterministic",
}
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}


def main() -> int:
    result = subprocess.run(
        ["lake", "env", "lean", "Audit.lean"],
        cwd=ROOT / "lean",
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    if result.returncode:
        return result.returncode
    if "sorryAx" in output:
        print("Proof audit failed: an admitted proof was found.", file=sys.stderr)
        return 1
    audited = set()
    for name, axioms in re.findall(
        r"'([^']+)'\s+depends on axioms:\s*\[([^\]]*)\]", output
    ):
        audited.add(name)
        unexpected = {a.strip() for a in axioms.split(",") if a.strip()} - ALLOWED
        if unexpected:
            print(f"Unexpected axioms in {name}: {sorted(unexpected)}", file=sys.stderr)
            return 1
    audited.update(re.findall(r"'([^']+)'\s+does not depend on any axioms", output))
    if missing := EXPECTED - audited:
        print(f"Missing theorem audits: {sorted(missing)}", file=sys.stderr)
        return 1
    print(f"Verified {len(EXPECTED)} theorem audits; no custom axioms or admitted proofs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
