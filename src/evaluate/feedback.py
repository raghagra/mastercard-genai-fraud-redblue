from collections import Counter
from typing import Any


def summarize_feedback_candidates(error_rows: list[dict[str, str]]) -> dict[str, Any]:
    false_negatives = [row for row in error_rows if row.get("label") == "1"]
    false_positives = [row for row in error_rows if row.get("label") == "0"]

    return {
        "false_negative_buckets": dict(Counter(row.get("attack_bucket", "") for row in false_negatives)),
        "false_negative_subtypes": dict(Counter(row.get("attack_subtype", "") for row in false_negatives)),
        "false_positive_count": len(false_positives),
        "false_negative_count": len(false_negatives),
    }

