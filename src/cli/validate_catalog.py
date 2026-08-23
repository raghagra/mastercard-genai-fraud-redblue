import json
import sys

from src.knowledge.validate_attack_cards import validate_attack_catalog


def main() -> int:
    result = validate_attack_catalog()

    print(f"checked={result.checked_count}")
    print(f"valid={str(result.valid).lower()}")
    print(json.dumps(result.summary, indent=2, sort_keys=True))

    if result.errors:
        print("errors:")
        for error in result.errors:
            print(f"- {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
