"""Small, composable command-line interface for Indeed-as-a-Service."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .bot import IndeedBot, Reply
from .core import CoreError
from .detection import SUPPORTED_LANGUAGES


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="indeed",
        description="Stochastic wording. Deterministic agreement. All local, with a Lean-verified response core.",
    )
    parser.add_argument("text", nargs="?", help="Text to agree with; reads stdin if omitted and piped.")
    parser.add_argument("--lang", choices=["auto", *SUPPORTED_LANGUAGES], default="auto", help="Response language (default: auto).")
    parser.add_argument("--seed", type=int, help="Use a repeatable pseudo-random sequence for demos and tests.")
    parser.add_argument("--json", action="store_true", help="Print response and routing metadata as JSON.")
    parser.add_argument("--interactive", action="store_true", help="Read one message per line until /quit or EOF.")
    parser.add_argument("--languages", action="store_true", help="List the supported language codes and exit.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _print_reply(reply: Reply, as_json: bool) -> None:
    print(json.dumps(reply.to_dict(), ensure_ascii=False) if as_json else reply.text)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; keep diagnostics on stderr and machine output on stdout."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.languages:
        if args.json:
            print(json.dumps(SUPPORTED_LANGUAGES, ensure_ascii=False))
        else:
            for code, name in SUPPORTED_LANGUAGES.items():
                print(f"{code:2}  {name}")
        return 0
    if args.interactive and args.text is not None:
        parser.error("positional text cannot be combined with --interactive")
    if not args.interactive and args.text is None:
        if sys.stdin.isatty():
            parser.error("provide text, pipe stdin, or use --interactive")
        args.text = sys.stdin.read()
    if not args.interactive and not args.text.strip():
        parser.error("input must contain non-whitespace text")
    try:
        bot = IndeedBot(seed=args.seed)
        if not args.interactive:
            _print_reply(bot.reply(args.text, language=args.lang), args.json)
            return 0
        if sys.stdin.isatty():
            print("Indeed. Type /quit to exit. Prompts are not saved.", file=sys.stderr)
        while True:
            if sys.stdin.isatty():
                print("> ", end="", file=sys.stderr, flush=True)
            line = sys.stdin.readline()
            if not line or line.strip() == "/quit":
                break
            if line.strip():
                _print_reply(bot.reply(line.rstrip("\n"), language=args.lang), args.json)
        return 0
    except KeyboardInterrupt:
        return 130
    except (CoreError, ValueError) as error:
        print(f"indeed: {error}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
