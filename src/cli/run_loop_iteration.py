import argparse
import json
import sys

from src.loop.run_iteration import run_closed_loop_iteration


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one closed-loop red-team/blue-team iteration.")
    parser.add_argument("--iteration-id", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-attack-card", type=int, default=1)
    parser.add_argument("--benign-count", type=int, default=500)
    parser.add_argument("--realism-profile", choices=["baseline", "overlap"], default="overlap")
    parser.add_argument("--review-source-iteration-id", default=None)
    args = parser.parse_args()

    summary = run_closed_loop_iteration(
        iteration_id=args.iteration_id,
        seed=args.seed,
        per_attack_card=args.per_attack_card,
        benign_count=args.benign_count,
        realism_profile=args.realism_profile,
        review_source_iteration_id=args.review_source_iteration_id,
    )
    print(json.dumps(
        {
            "iteration_id": summary["iteration_id"],
            "counts": summary["counts"],
            "evaluation_overall": summary["evaluation_overall"],
            "failure_summary": summary["failure_summary"],
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
