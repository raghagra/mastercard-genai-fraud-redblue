import json
import sys

from src.genai.gateway import GenAIGateway


def main() -> int:
    gateway = GenAIGateway()
    print(json.dumps(gateway.health(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
