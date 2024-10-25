# `dk`

**Usage**:

```console
$ dk [OPTIONS] COMMAND [ARGS]...
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

## `dk get-run`

Get the active run

**Usage**:

```console
$ dk get-run [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `dk init`

Initialise a datakit run

**Usage**:

```console
$ dk init [OPTIONS] [RUN_NAME]
```

**Arguments**:

* `[RUN_NAME]`: Name of the run you want to initialise in the format [algorithm].[run name]

**Options**:

* `--help`: Show this message and exit.

## `dk load`

Load data into configuration variable

**Usage**:

```console
$ dk load [OPTIONS] VARIABLE_NAME PATH
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to populate  [required]
* `PATH`: Path to data to ingest (xml, csv)  [required]

**Options**:

* `--help`: Show this message and exit.

## `dk new`

Generate a new datakit and algorithm scaffold

**Usage**:

```console
$ dk new [OPTIONS] ALGORITHM_NAME
```

**Arguments**:

* `ALGORITHM_NAME`: Name of the algorithm to generate  [required]

**Options**:

* `--help`: Show this message and exit.

## `dk reset`

Reset datakit to clean state

Removes all run outputs and resets configurations to default

**Usage**:

```console
$ dk reset [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `dk run`

Execute the active run

**Usage**:

```console
$ dk run [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `dk set`

Set a variable value

**Usage**:

```console
$ dk set [OPTIONS] VARIABLE_REF VARIABLE_VALUE
```

**Arguments**:

* `VARIABLE_REF`: Either a variable name, or a table reference in the format [resource name].[primary key].[column name]  [required]
* `VARIABLE_VALUE`: Value to set  [required]

**Options**:

* `--help`: Show this message and exit.

## `dk set-run`

Set the active run

**Usage**:

```console
$ dk set-run [OPTIONS] [RUN_NAME]
```

**Arguments**:

* `[RUN_NAME]`: Name of the run you want to enable

**Options**:

* `--help`: Show this message and exit.

## `dk show`

Print a variable value

**Usage**:

```console
$ dk show [OPTIONS] VARIABLE_NAME
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to print  [required]

**Options**:

* `--help`: Show this message and exit.

## `dk view`

Render a view locally

**Usage**:

```console
$ dk view [OPTIONS] VIEW_NAME
```

**Arguments**:

* `VIEW_NAME`: The name of the view to render  [required]

**Options**:

* `--help`: Show this message and exit.
