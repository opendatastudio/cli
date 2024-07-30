# opendata-cli

A command line client for running opendata.studio datapackages.

View usage documentation at [docs/README.md](docs/README.md).


## Development

To install and test locally, navigate to the datapackage directory you want to
test.
```
cd /path/to/datapackage
```

Create a virtualenv and install the CLI via pip in local mode:
```
python -m venv .venv
source .venv/bin/activate
pip install -e [/path/to/cli]
```

You can now run the CLI script with:
```
opendata-cli
```
