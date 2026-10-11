"""Small explicit phase dispatcher; Docker lifecycle stays outside the experiment."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'ablation', 'backend', 'analyze', 'followup'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--native-run', type=Path)
    parser.add_argument('--fill-missing', action='store_true', help='Explicitly authorize missing exact-input embeddings through the budget gateway')
    parser.add_argument('--backend', choices=['qdrant', 'infinity', 'postgres'])
    parser.add_argument('--rounds', type=int, choices=range(1,4), default=3)
    args = parser.parse_args()
    if args.phase == 'prepare' and args.receipts is None:
        parser.error('prepare requires --receipts')
    if args.phase in {'backend', 'followup'} and args.backend is None:
        parser.error('database phases require --backend')
    args.root.mkdir(parents=True, exist_ok=True)
    if args.phase == 'prepare':
        from .prepare import prepare
        prepare(args.root, args.receipts, args.native_run, args.fill_missing)
    elif args.phase == 'ablation':
        from .ablation import ablation
        ablation(args.root)
    elif args.phase == 'backend':
        from .benchmark import benchmark
        benchmark(args.root, args.backend)
    elif args.phase == 'followup':
        from .followup import followup
        followup(args.root, args.backend, args.rounds)
    else:
        from .analyze import analyze
        analyze(args.root)
