#!/usr/bin/env python3
"""Pure wordcount CLI for skills that do not ship storyctl.

Import uses this to snapshot already-written chapter length.  It loads the
local ``wordcount_core.py`` copy and never reaches into another skill.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence


def _load_core() -> Any:
    path = Path(__file__).with_name("wordcount_core.py")
    spec = importlib.util.spec_from_file_location("story_wordcount_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("TOOL_UNAVAILABLE: wordcount_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load_core()


class CliArgumentError(ValueError):
    pass


class StructuredArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliArgumentError(message)


def _json_line(payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    sys.stdout.buffer.write(rendered.encode("utf-8"))
    sys.stdout.buffer.flush()


def _build_parser() -> StructuredArgumentParser:
    parser = StructuredArgumentParser(prog="wordcount_cli.py")
    commands = parser.add_subparsers(dest="command", required=True)
    wordcount = commands.add_parser("wordcount")
    wordcount_commands = wordcount.add_subparsers(dest="wordcount_command", required=True)
    measure = wordcount_commands.add_parser("measure")
    measure.add_argument("--file", required=True)
    measure.add_argument("--chapter")
    measure.add_argument("--case-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(argv) if argv is not None else sys.argv[1:]
    try:
        args = _build_parser().parse_args(raw)
    except CliArgumentError as exc:
        _json_line(
            core.invalid_wordcount_result("INVALID_ARGUMENT", case_id=str(exc))
        )
        return 2
    try:
        body = Path(args.file).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _json_line(
            {
                "schema": core.MEASUREMENT_SCHEMA,
                "metric": core.METRIC,
                "chapter": args.chapter,
                "case_id": args.case_id,
                "actual": None,
                "status": "invalid",
                "invalid_reason": "INVALID_FILE",
            }
        )
        return 2
    result = core.measure_wordcount(
        body, chapter=args.chapter, case_id=args.case_id
    )
    _json_line(result)
    return 2 if result.get("status") == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
