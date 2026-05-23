#!/bin/zsh
cd "$(dirname "$0")"
uv run python main.py
echo
echo "Press Enter to close..."
read