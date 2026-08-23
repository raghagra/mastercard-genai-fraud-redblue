import argparse
import sys

from src.features.build_features import build_feature_dataset, feature_columns


def main() -> int:
    parser = argparse.ArgumentParser(description="Build model-ready features.")
    parser.parse_args()

    rows = build_feature_dataset()
    print(f"features={len(rows)}")
    print(f"feature_columns={len(feature_columns(rows))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
