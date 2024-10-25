# This must be run from within the /docs directory
# NOTE: The mock datakit.json in this repository is required to run this
# Ensure venv is activated and typer is installed:
# source ../.venv/bin/activate
typer ../cli/main.py utils docs --name "dk" --output README.md
