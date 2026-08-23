import argparse
import sys

from src.detect.score import score_feature_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Score feature rows with the baseline detector.")
    parser.parse_args()

    rows = score_feature_rows()
    print(f"scores={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
