import argparse
import json
import sys

from src.mutate.review import accepted_mutations, list_mutation_candidates, list_mutation_reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="List mutation candidates and reviews for an iteration.")
    parser.add_argument("iteration_id")
    args = parser.parse_args()

    payload = {
        "iteration_id": args.iteration_id,
        "candidates": list_mutation_candidates(args.iteration_id),
        "reviews": list_mutation_reviews(args.iteration_id),
        "accepted": accepted_mutations(args.iteration_id),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

