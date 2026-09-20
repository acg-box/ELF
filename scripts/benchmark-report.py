#!/usr/bin/env python3
"""Publish the English decision report from one measured result bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark_report import publish


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if bundle.get("schema") != "elf.benchmark_bundle/v1":
        raise ValueError("input is not an ELF benchmark bundle")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(publish(bundle), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
