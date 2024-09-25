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

* `init`: Initialise a datapackage algorithm run
* `load`: Load data into configuration variable
* `reset`: Reset datapackage to clean state
* `run`: Run the specified configuration
* `set-param`: Set a parameter value
* `set-var`: Set a variable value
* `view`: Render a view locally
* `view-table`: Print a tabular data variable

## `opends init`

Initialise a datapackage algorithm run

**Usage**:

```console
$ opends init [OPTIONS] [ALGORITHM_NAME]
```

**Arguments**:

* `[ALGORITHM_NAME]`: The name of the algorithm to initialise  [default: [default_algorithm_name]]

**Options**:

* `--help`: Show this message and exit.

## `opends load`

Load data into configuration variable

**Usage**:

```console
$ opends load [OPTIONS] VARIABLE_NAME PATH [RUN_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to populate  [required]
* `PATH`: Path to data to ingest (xml, csv)  [required]
* `[RUN_NAME]`: Name of target run

**Options**:

* `--help`: Show this message and exit.

## `opends reset`

Reset datapackage to clean state

Removes all run outputs and resets configurations to default

**Usage**:

```console
$ opends reset [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `opends run`

Run the specified configuration

**Usage**:

```console
$ opends run [OPTIONS] [RUN_NAME]
```

**Arguments**:

* `[RUN_NAME]`: The name of the run to execute

**Options**:

* `--help`: Show this message and exit.

## `opends set-param`

Set a parameter value

**Usage**:

```console
$ opends set-param [OPTIONS] VARIABLE_NAME PARAM_NAME PARAM_VALUE [RUN_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of parameter variable to populate  [required]
* `PARAM_NAME`: Name of parameter to set  [required]
* `PARAM_VALUE`: Value to set  [required]
* `[RUN_NAME]`: Name of target run

**Options**:

* `--help`: Show this message and exit.

## `opends set-var`

Set a variable value

**Usage**:

```console
$ opends set-var [OPTIONS] VARIABLE_NAME VARIABLE_VALUE [RUN_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to set  [required]
* `VARIABLE_VALUE`: Value to set  [required]
* `[RUN_NAME]`: Name of target run

**Options**:

* `--help`: Show this message and exit.

## `opends view`

Render a view locally

**Usage**:

```console
$ opends view [OPTIONS] VIEW_NAME [RUN_NAME]
```

**Arguments**:

* `VIEW_NAME`: The name of the view to render  [required]
* `[RUN_NAME]`: The name of the run to view

**Options**:

* `--help`: Show this message and exit.

## `opends view-table`

Print a tabular data variable

**Usage**:

```console
$ opends view-table [OPTIONS] VARIABLE_NAME [RUN_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to view  [required]
* `[RUN_NAME]`: Name of target run

**Options**:

* `--help`: Show this message and exit.
