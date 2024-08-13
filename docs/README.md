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

* `load`: Load data into algorithm argument
* `reset`: Reset datapackage to clean state
* `run`: Run an algorithm
* `set-arg`: Set an argument value
* `set-param`: Set a parameter value
* `view`: Render a view locally
* `view-table`: Print a tabular data argument

## `ods load`

Load data into algorithm argument

**Usage**:

```console
$ ods load [OPTIONS] ARGUMENT_NAME PATH [ALGORITHM_NAME] [ARGUMENT_SPACE_NAME]
```

**Arguments**:

* `ARGUMENT_NAME`: Name of argument to populate  [required]
* `PATH`: Path to the data to ingest (xml, csv)  [required]
* `[ALGORITHM_NAME]`: Name of target algorithm
* `[ARGUMENT_SPACE_NAME]`: Name of target argument space  [default: default]

**Options**:

* `--help`: Show this message and exit.

## `ods reset`

Reset datapackage to clean state

Removes all run outputs and resets argument spaces to default

**Usage**:

```console
$ ods reset [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `ods run`

Run an algorithm

By default, the run command executes the algorithm with the container
defined in the specified argument space

**Usage**:

```console
$ ods run [OPTIONS] [ALGORITHM] [ARGUMENTS] [CONTAINER]
```

**Arguments**:

* `[ALGORITHM]`: The name of the algorithm to run
* `[ARGUMENTS]`: The name of the argument space to pass to the algorithm  [default: default]
* `[CONTAINER]`: The name of the container to run in

**Options**:

* `--help`: Show this message and exit.

## `ods set-arg`

Set an argument value

**Usage**:

```console
$ ods set-arg [OPTIONS] ARGUMENT VALUE [ALGORITHM] [ARGUMENT_SPACE]
```

**Arguments**:

* `ARGUMENT`: Name of argument to set  [required]
* `VALUE`: Value to set  [required]
* `[ALGORITHM]`: Name of target algorithm
* `[ARGUMENT_SPACE]`: Name of target argument space  [default: default]

**Options**:

* `--help`: Show this message and exit.

## `ods set-param`

Set a parameter value

**Usage**:

```console
$ ods set-param [OPTIONS] ARGUMENT NAME VALUE [ALGORITHM] [ARGUMENT_SPACE]
```

**Arguments**:

* `ARGUMENT`: Name of parameter argument to populate  [required]
* `NAME`: Name of parameter to set  [required]
* `VALUE`: Value to set  [required]
* `[ALGORITHM]`: Name of target algorithm
* `[ARGUMENT_SPACE]`: Name of target argument space  [default: default]

**Options**:

* `--help`: Show this message and exit.

## `ods view`

Render a view locally

**Usage**:

```console
$ ods view [OPTIONS] VIEW [CONTAINER]
```

**Arguments**:

* `VIEW`: The name of the view to render  [required]
* `[CONTAINER]`: The name of the container to render the view in

**Options**:

* `--help`: Show this message and exit.

## `ods view-table`

Print a tabular data argument

**Usage**:

```console
$ ods view-table [OPTIONS] ARGUMENT_NAME [ALGORITHM_NAME] [ARGUMENT_SPACE_NAME]
```

**Arguments**:

* `ARGUMENT_NAME`: Name of argument to view  [required]
* `[ALGORITHM_NAME]`: Name of target algorithm
* `[ARGUMENT_SPACE_NAME]`: Name of target argument space  [default: default]

**Options**:

* `--help`: Show this message and exit.
