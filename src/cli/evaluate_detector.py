import argparse
import json
import sys

from src.evaluate.reports import build_evaluation_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate detector scores.")
    parser.parse_args()

    report = build_evaluation_report()
    print(json.dumps(report["overall"], indent=2, sort_keys=True))
    print(f"bucket_groups={len(report['by_bucket'])}")
    print(f"subtype_groups={len(report['by_subtype'])}")
    print(f"errors={report['error_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
