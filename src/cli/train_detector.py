import argparse
import json
import sys

from src.detect.train import train_baseline_detector


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the baseline fraud detector.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    metrics = train_baseline_detector(seed=args.seed)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

