# This must be run from within the /docs directory
# NOTE: The mock datapackage.json in this repository is required to run this
# Ensure venv is activated and typer is installed:
# source ../.venv/bin/activate
typer ../cli/main.py utils docs --name "opendata-cli" --output README.md
