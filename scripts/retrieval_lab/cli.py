"""Small explicit phase dispatcher; Docker lifecycle stays outside the experiment."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'ablation', 'backend', 'analyze'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--backend', choices=['qdrant', 'infinity', 'postgres'])
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    if args.phase == 'prepare':
        from .prepare import prepare
        prepare(args.root, args.receipts)
    elif args.phase == 'ablation':
        from .ablation import ablation
        ablation(args.root)
    elif args.phase == 'backend':
        from .benchmark import benchmark
        benchmark(args.root, args.backend)
    else:
        from .analyze import analyze
        analyze(args.root)
