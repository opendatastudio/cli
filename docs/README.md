# `opends`

**Usage**:

```console
$ opends [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `get-run`: Get the active run
* `init`: Initialise a datakit run
* `load`: Load data into configuration variable
* `new`: Generate a new datakit and algorithm scaffold
* `reset`: Reset datakit to clean state
* `run`: Execute the active run
* `set`: Set a variable value
* `set-run`: Set the active run
* `show`: Print a variable value
* `view`: Render a view locally

## `opends get-run`

Get the active run

**Usage**:

```console
$ opends get-run [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `opends init`

Initialise a datakit run

**Usage**:

```console
$ opends init [OPTIONS] [RUN_NAME]
```

**Arguments**:

* `[RUN_NAME]`: Name of the run you want to initialise in the format [algorithm].[run name]

**Options**:

* `--help`: Show this message and exit.

## `opends load`

Load data into configuration variable

**Usage**:

```console
$ opends load [OPTIONS] VARIABLE_NAME PATH
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to populate  [required]
* `PATH`: Path to data to ingest (xml, csv)  [required]

**Options**:

* `--help`: Show this message and exit.

## `opends new`

Generate a new datakit and algorithm scaffold

**Usage**:

```console
$ opends new [OPTIONS] ALGORITHM_NAME
```

**Arguments**:

* `ALGORITHM_NAME`: Name of the algorithm to generate  [required]

**Options**:

* `--help`: Show this message and exit.

## `opends reset`

Reset datakit to clean state

Removes all run outputs and resets configurations to default

**Usage**:

```console
$ opends reset [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `opends run`

Execute the active run

**Usage**:

```console
$ opends run [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `opends set`

Set a variable value

**Usage**:

```console
$ opends set [OPTIONS] VARIABLE_REF VARIABLE_VALUE
```

**Arguments**:

* `VARIABLE_REF`: Either a variable name, or a table reference in the format [resource name].[primary key].[column name]  [required]
* `VARIABLE_VALUE`: Value to set  [required]

**Options**:

* `--help`: Show this message and exit.

## `opends set-run`

Set the active run

**Usage**:

```console
$ opends set-run [OPTIONS] [RUN_NAME]
```

**Arguments**:

* `[RUN_NAME]`: Name of the run you want to enable

**Options**:

* `--help`: Show this message and exit.

## `opends show`

Print a variable value

**Usage**:

```console
$ opends show [OPTIONS] VARIABLE_NAME
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to print  [required]

**Options**:

* `--help`: Show this message and exit.

## `opends view`

Render a view locally

**Usage**:

```console
$ opends view [OPTIONS] VIEW_NAME
```

**Arguments**:

* `VIEW_NAME`: The name of the view to render  [required]

**Options**:

* `--help`: Show this message and exit.
