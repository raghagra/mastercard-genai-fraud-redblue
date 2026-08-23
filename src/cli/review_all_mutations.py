import argparse
import json
import sys

from src.mutate.review import review_all_mutations


def main() -> int:
    parser = argparse.ArgumentParser(description="Review all mutation candidates for an iteration.")
    parser.add_argument("iteration_id")
    parser.add_argument("--decision", choices=["accepted", "rejected", "needs_changes"], required=True)
    parser.add_argument("--reviewer", default="cli")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    reviews = review_all_mutations(
        iteration_id=args.iteration_id,
        decision=args.decision,
        reviewer=args.reviewer,
        notes=args.notes,
    )
    print(json.dumps({"review_count": len(reviews), "reviews": reviews}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
