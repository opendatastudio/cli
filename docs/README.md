# `ods`

**Usage**:

```console
$ ods [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `load`: Load data into configuration variable
* `reset`: Reset datapackage to clean state
* `run`: Run the specified configuration
* `set-param`: Set a parameter value
* `set-var`: Set a variable value
* `view`: Render a view locally
* `view-table`: Print a tabular data variable

## `ods load`

Load data into configuration variable

**Usage**:

```console
$ ods load [OPTIONS] VARIABLE_NAME PATH [CONFIGURATION_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to populate  [required]
* `PATH`: Path to data to ingest (xml, csv)  [required]
* `[CONFIGURATION_NAME]`: Name of target configuration  [default: [default_algorithm_name].default]

**Options**:

* `--help`: Show this message and exit.

## `ods reset`

Reset datapackage to clean state

Removes all run outputs and resets configurations to default

**Usage**:

```console
$ ods reset [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `ods run`

Run the specified configuration

**Usage**:

```console
$ ods run [OPTIONS] [CONFIGURATION_NAME]
```

**Arguments**:

* `[CONFIGURATION_NAME]`: The name of the configuration to run  [default: [default_algorithm_name].default]

**Options**:

* `--help`: Show this message and exit.

## `ods set-param`

Set a parameter value

**Usage**:

```console
$ ods set-param [OPTIONS] VARIABLE_NAME PARAM_NAME PARAM_VALUE [CONFIGURATION_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of parameter variable to populate  [required]
* `PARAM_NAME`: Name of parameter to set  [required]
* `PARAM_VALUE`: Value to set  [required]
* `[CONFIGURATION_NAME]`: Name of target configuration  [default: [default_algorithm_name].default]

**Options**:

* `--help`: Show this message and exit.

## `ods set-var`

Set a variable value

**Usage**:

```console
$ ods set-var [OPTIONS] VARIABLE_NAME VARIABLE_VALUE [CONFIGURATION_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to set  [required]
* `VARIABLE_VALUE`: Value to set  [required]
* `[CONFIGURATION_NAME]`: Name of target configuration  [default: [default_algorithm_name].default]

**Options**:

* `--help`: Show this message and exit.

## `ods view`

Render a view locally

**Usage**:

```console
$ ods view [OPTIONS] VIEW_NAME
```

**Arguments**:

* `VIEW_NAME`: The name of the view to render  [required]

**Options**:

* `--help`: Show this message and exit.

## `ods view-table`

Print a tabular data variable

**Usage**:

```console
$ ods view-table [OPTIONS] VARIABLE_NAME [CONFIGURATION_NAME]
```

**Arguments**:

* `VARIABLE_NAME`: Name of variable to view  [required]
* `[CONFIGURATION_NAME]`: Name of target configuration  [default: [default_algorithm_name].default]

**Options**:

* `--help`: Show this message and exit.
