"""Render an approved local storyboard file with the same renderer as Studio."""

import argparse
from pathlib import Path

from app.storyboard_preview import STYLES, render, visual_direction

__all__ = ["render", "visual_direction"]

if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("destination", type=Path)
    cli.add_argument("--style", choices=STYLES, required=True, help="Illustration direction chosen by the editor")
    args = cli.parse_args()
    render(args.source, args.destination, args.style)
