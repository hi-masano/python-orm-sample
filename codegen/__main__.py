"""python -m codegen <command>  — 全生成物の唯一の生成入口."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from codegen import api_gen, checksums, er_gen, models_gen
from codegen.render import CodegenError

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codegen")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("models", "er", "api", "all"):
        sub.add_parser(name)
    rec = sub.add_parser("checksum-record")
    rec.add_argument("path")
    sub.add_parser("checksum-verify")
    args = parser.parse_args(argv)
    try:
        if args.cmd in ("models", "er", "all"):
            models_gen.generate(ROOT)
        if args.cmd in ("er", "all"):
            er_gen.generate(ROOT)
        if args.cmd in ("api", "all"):
            api_gen.generate(ROOT)
        if args.cmd == "checksum-record":
            checksums.record(ROOT, Path(args.path))
        if args.cmd == "checksum-verify":
            errors = checksums.verify(ROOT)
            for e in errors:
                print(f"migration checksum error: {e}", file=sys.stderr)
            return 1 if errors else 0
    except CodegenError as e:
        print(f"codegen error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
