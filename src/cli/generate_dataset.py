import argparse
import sys

from src.generate.pipeline import generate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic fraud datasets.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-attack-card", type=int, default=1)
    parser.add_argument("--benign-count", type=int, default=500)
    args = parser.parse_args()

    dataset = generate_dataset(
        seed=args.seed,
        per_attack_card=args.per_attack_card,
        benign_count=args.benign_count,
    )

    print(f"transactions={len(dataset.transactions)}")
    print(f"customers={len(dataset.customers)}")
    print(f"merchants={len(dataset.merchants)}")
    print(f"devices={len(dataset.devices)}")
    print(f"attack_instances={len(dataset.attack_instances)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
