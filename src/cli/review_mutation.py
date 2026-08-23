import argparse
import json
import sys

from src.mutate.review import review_mutation


def main() -> int:
    parser = argparse.ArgumentParser(description="Review one mutation candidate.")
    parser.add_argument("iteration_id")
    parser.add_argument("mutation_id")
    parser.add_argument("--decision", choices=["accepted", "rejected", "needs_changes"], required=True)
    parser.add_argument("--reviewer", default="cli")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    review = review_mutation(
        iteration_id=args.iteration_id,
        mutation_id=args.mutation_id,
        decision=args.decision,
        reviewer=args.reviewer,
        notes=args.notes,
    )
    print(json.dumps(review, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

