#!/bin/bash
# Convenience wrapper for running imagesearch CLI

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the CLI with all arguments
python -m imagesearch.cli "$@"