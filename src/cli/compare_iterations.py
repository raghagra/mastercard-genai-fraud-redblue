import argparse
import json
import sys

from src.loop.compare_iterations import compare_iterations


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two closed-loop iterations.")
    parser.add_argument("baseline_iteration_id")
    parser.add_argument("candidate_iteration_id")
    args = parser.parse_args()

    comparison = compare_iterations(args.baseline_iteration_id, args.candidate_iteration_id)
    print(json.dumps(comparison, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
