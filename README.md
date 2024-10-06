# opendata.studio CLI

A command line client for running opendata.studio dataflows.

View usage documentation at [docs/README.md](https://github.com/opendatastudio/cli/blob/main/docs/README.md).


## Development

To install and test locally, navigate to the dataflow directory you want to
test.
```
cd /path/to/dataflow
```

Create a virtualenv and install the CLI via pip in local mode:
```
python -m venv .venv
source .venv/bin/activate
pip install -e [/path/to/cli]
```

You can now run the CLI script with:
```
opends
```
