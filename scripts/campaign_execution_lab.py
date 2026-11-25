"""Run the versioned synthetic B2B journey offline, optionally saving its JSON evidence."""
import argparse
import json
from pathlib import Path

from app.campaign_lab import replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(replay(), indent=2, ensure_ascii=False, allow_nan=False)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
