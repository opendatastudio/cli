import os
import time
import shutil
import json
import re
import pickle
import typer
import docker
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from ast import literal_eval
from typing import Optional, Any
from typing_extensions import Annotated
from rich import print
from rich.panel import Panel
from tabulate import tabulate
from datakitpy.datakit import (
    ExecutionError,
    ResourceError,
    execute_datakit,
    execute_view,
    init_resource,
    load_resource_by_variable,
    write_resource,
    update_resource,
    load_run_configuration,
    write_run_configuration,
    load_variable,
    load_variable_signature,
    load_datakit_configuration,
    write_datakit_configuration,
    load_algorithm,
    write_algorithm,
    get_algorithm_name,
    RUN_DIR,
    RELATIONSHIPS_FILE,
    VIEW_ARTEFACTS_DIR,
)
from datakitpy.helpers import find_by_name, find


app = typer.Typer(no_args_is_help=True)


client = docker.from_env()


# Assume we are always at the datakit root
# TODO: Validate we actually are, and that this is a datakit
DATAKIT_PATH = os.getcwd()  # Root datakit path
CONFIG_FILE = f"{DATAKIT_PATH}/.datakit"
RUN_EXTENSION = ".run"


# Helpers


def dumb_str_to_type(value) -> Any:
    """Parse a string to any Python type"""
    # Stupid workaround for Typer not supporting Union types :<
    try:
        return literal_eval(value)
    except ValueError:
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        else:
            return value


def get_default_algorithm() -> str:
    """Return the default algorithm for the current datakit"""
    return load_datakit_configuration(base_path=DATAKIT_PATH)["algorithms"][0]


def load_config():
    """Load CLI configuration file"""
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def get_active_run():
    try:
        return load_config()["run"]
    except FileNotFoundError:
        print('[red]No active run is set. Have you run "dk init"?[/red]')
        exit(1)


def write_config(run_name):
    """Write updated CLI configuration file"""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"run": run_name}, f, indent=2)


def run_exists(run_name):
    """Check if specified run exists"""
    run_dir = RUN_DIR.format(base_path=DATAKIT_PATH, run_name=run_name)
    return os.path.exists(run_dir) and os.path.isdir(run_dir)


def get_full_run_name(run_name):
    """Validate and return full run name"""
    if run_name is not None:
        # Check the run_name matches the pattern [algorithm].[name] or
        # [algorithm]
        pattern = re.compile(r"^([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)$")

        algorithms = load_datakit_configuration()["algorithms"]

        if not pattern.match(run_name) and run_name not in algorithms:
            print(f'[red]"{run_name}" is not a valid run name[/red]')
            print(
                "[red]Run names must match the format: "
                r"\[algorithm].\[name][/red]"
            )
            print(
                "[red]Did you forget to add your algorithm to "
                "datakit.json?[/red]"
            )
            exit(1)

        algorithm_name = get_algorithm_name(run_name)
        datakit_algorithms = load_datakit_configuration(
            base_path=DATAKIT_PATH
        )["algorithms"]

        if get_algorithm_name(run_name) not in datakit_algorithms:
            print(
                f'[red]"{algorithm_name}" is not a valid datakit '
                "algorithm[/red]"
            )
            print(
                "[red]Available datakit algorithms: "
                f"{datakit_algorithms}[/red]"
            )
            exit(1)

        return run_name + RUN_EXTENSION
    else:
        return get_default_algorithm() + RUN_EXTENSION


def execute_relationship(run_name: str, variable_name: str) -> None:
    """Execute any relationships applied to the given source variable"""
    # Load run configuration for modification
    run = load_run_configuration(run_name)

    print(
        f"[bold]=>[/bold] Executing relationship for variable {variable_name}"
    )

    # Load associated relationship
    try:
        with open(
            RELATIONSHIPS_FILE.format(
                base_path=DATAKIT_PATH,
                algorithm_name=get_algorithm_name(run_name),
            ),
            "r",
        ) as f:
            relationship = find(
                json.load(f)["relationships"], "source", variable_name
            )
    except FileNotFoundError:
        # No relationships to execute, return
        return

    if relationship is None:
        # No relationship for specified variable found, return
        return

    # Apply relationship rules
    for rule in relationship["rules"]:
        if rule["type"] == "change":
            # Currently the only type of "change" rule we have is one that
            # mirrors the schema from the source to other resources, so assume
            # this is the case here

            # TODO: This will need to change in the future

            source = load_resource_by_variable(
                run_name=run_name,
                variable_name=variable_name,
                base_path=DATAKIT_PATH,
                as_dict=True,
            )

            for target in rule["targets"]:
                update_resource(
                    run_name=run_name,
                    resource_name=target["name"],
                    schema=source["schema"],
                    base_path=DATAKIT_PATH,
                )

        elif rule["type"] == "value":
            # Check if this rule applies to current run configuration state

            # Get source variable value
            value = load_variable(
                run_name=run_name,
                variable_name=variable_name,
                base_path=DATAKIT_PATH,
            )["value"]

            # If the source variable value matches the rule value, execute
            # the relationship
            if value in rule["values"]:
                for target in rule["targets"]:
                    if "disabled" in target:
                        # Set target variable disabled value
                        target_variable = load_variable(
                            run_name=run_name,
                            variable_name=target["name"],
                            base_path=DATAKIT_PATH,
                        )

                        target_variable["disabled"] = target["disabled"]

                    if target["type"] == "resource":
                        # Set target resource data and schema
                        target_resource = load_resource_by_variable(
                            run_name=run["name"],
                            variable_name=target["name"],
                            base_path=DATAKIT_PATH,
                            as_dict=True,
                        )

                        if "data" in target:
                            print(
                                " [bold]*[/bold] Setting "
                                f"{target_resource['name']} data"
                            )
                            target_resource["data"] = target["data"]

                        if "schema" in target:
                            print(
                                " [bold]*[/bold] Setting "
                                f"{target_resource['name']} schema"
                            )
                            target_resource["schema"] = target["schema"]

                        write_resource(
                            run_name=run["name"],
                            resource=target_resource,
                            base_path=DATAKIT_PATH,
                        )
                    elif target["type"] == "value":
                        # Set target variable value
                        target_variable = find_by_name(
                            run["data"]["inputs"] + run["data"]["outputs"],
                            target["name"],
                        )

                        if "value" in target:
                            print(
                                f" [bold]*[/bold] Setting {target['name']} "
                                f"value from {target_variable['value']} to "
                                f"{target['value']}"
                            )
                            target_variable["value"] = target["value"]

                        if "metaschema" in target:
                            print(
                                f" [bold]*[/bold] Setting {target['name']} "
                                "metaschema from "
                                f"{target_variable['metaschema']} "
                                f"to {target['metaschema']}"
                            )
                            target_variable["metaschema"] = target[
                                "metaschema"
                            ]
                    else:
                        raise NotImplementedError(
                            (
                                'Only "resource" and "value" type rule '
                                "targets are implemented"
                            )
                        )

        else:
            raise NotImplementedError("Only value-based rules are implemented")

    # Write modified run configuration
    write_run_configuration(run, base_path=DATAKIT_PATH)


# Commands


@app.command()
def init(
    run_name: Annotated[
        Optional[str],
        typer.Argument(
            help=(
                "Name of the run you want to initialise in the format "
                "[algorithm].[run name]"
            )
        ),
    ] = None,
) -> None:
    """Initialise a datakit run"""
    run_name = get_full_run_name(run_name)

    # Check directory doesn't already exist
    if run_exists(run_name):
        print(f"[red]{run_name} already exists[/red]")
        exit(1)

    # Create run directory
    run_dir = RUN_DIR.format(base_path=DATAKIT_PATH, run_name=run_name)
    os.makedirs(f"{run_dir}/resources")
    os.makedirs(f"{run_dir}/views")
    print(f"[bold]=>[/bold] Created run directory: {run_dir}")

    algorithm_name = get_algorithm_name(run_name)
    algorithm = load_algorithm(algorithm_name, base_path=DATAKIT_PATH)

    # Generate default run configuration
    run = {
        "name": run_name,
        "title": f"Run configuration for {algorithm_name}",
        "profile": "datakit-run",
        "algorithm": f"{algorithm_name}",
        "container": f'{algorithm["container"]}',
        "data": {
            "inputs": [],
            "outputs": [],
        },
    }

    # Create run configuration and initialise resources
    for variable in algorithm["signature"]["inputs"]:
        # Add variable defaults to run configuration
        run["data"]["inputs"].append(
            {
                "name": variable["name"],
                **variable["default"],
            }
        )

        # Initialise associated resources
        if variable["type"] == "resource":
            resource_name = variable["default"]["resource"]

            init_resource(
                run_name=run["name"],
                resource_name=resource_name,
                base_path=DATAKIT_PATH,
            )

            print(f"[bold]=>[/bold] Generated input resource: {resource_name}")

    for variable in algorithm["signature"]["outputs"]:
        # Add variable defaults to run configuration
        run["data"]["outputs"].append(
            {
                "name": variable["name"],
                **variable["default"],
            }
        )

        # Initialise associated resources
        if variable["type"] == "resource":
            resource_name = variable["default"]["resource"]

            init_resource(
                run_name=run["name"],
                resource_name=resource_name,
                base_path=DATAKIT_PATH,
            )

            print(f"[bold]=>[/bold] Generated input resource: {resource_name}")

    # Write generated configuration
    write_run_configuration(run, base_path=DATAKIT_PATH)

    print(f"[bold]=>[/bold] Generated default run configuration: {run_name}")

    # Add default run to datakit.json
    datakit = load_datakit_configuration(base_path=DATAKIT_PATH)
    datakit["runs"].append(run_name)
    write_datakit_configuration(datakit, base_path=DATAKIT_PATH)

    # Write current run name to config
    write_config(run_name)


@app.command()
def set_run(
    run_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of the run you want to enable"),
    ] = None,
) -> None:
    """Set the active run"""
    run_name = get_full_run_name(run_name)

    if run_exists(run_name):
        # Set to active run
        write_config(run_name)
    else:
        print(f"[red]{run_name} does not exist[/red]")


@app.command()
def get_run() -> None:
    """Get the active run"""
    print(f"[bold]{get_active_run()}[/bold]")


@app.command()
def run() -> None:
    """Execute the active run"""
    run_name = get_active_run()

    # Execute algorithm container and print any logs
    print(f"[bold]=>[/bold] Executing [bold]{run_name}[/bold]")

    try:
        logs = execute_datakit(
            client,
            run_name,
            base_path=DATAKIT_PATH,
        )
    except ExecutionError as e:
        print(
            Panel(
                e.logs,
                title="[bold red]Execution error[/bold red]",
            )
        )
        print("[red]Container execution failed[/red]")
        exit(1)

    if logs:
        print(
            Panel(
                logs,
                title="[bold]Execution container output[/bold]",
            )
        )

    print(f"[bold]=>[/bold] Executed [bold]{run_name}[/bold] successfully")


@app.command()
def show(
    variable_name: Annotated[
        str,
        typer.Argument(
            help="Name of variable to print",
            show_default=False,
        ),
    ],
) -> None:
    """Print a variable value"""
    run_name = get_active_run()

    # Load algorithum signature to check variable type
    signature = load_variable_signature(
        run_name=run_name,
        variable_name=variable_name,
        base_path=DATAKIT_PATH,
    )

    if signature["type"] == "resource":
        # Variable is a tabular data resource
        resource = load_resource_by_variable(
            run_name=run_name,
            variable_name=variable_name,
            base_path=DATAKIT_PATH,
        )

        print(
            tabulate(
                resource.to_dict()["data"],
                headers="keys",
                tablefmt="rounded_grid",
            )
        )
    else:
        # Variable is a simple string/number/bool value
        variable = load_variable(
            run_name=run_name,
            variable_name=variable_name,
            base_path=DATAKIT_PATH,
        )

        print(
            Panel(
                str(variable["value"]),
                title=f"{variable_name}",
                expand=False,
            )
        )


@app.command()
def view(
    view_name: Annotated[
        str,
        typer.Argument(
            help="The name of the view to render", show_default=False
        ),
    ],
) -> None:
    """Render a view locally"""
    run_name = get_active_run()

    print(f"[bold]=>[/bold] Generating [bold]{view_name}[/bold] view")

    try:
        logs = execute_view(
            docker_client=client,
            run_name=run_name,
            view_name=view_name,
            base_path=DATAKIT_PATH,
        )
    except ResourceError as e:
        print("[red]" + e.message + "[/red]")
        exit(1)
    except ExecutionError as e:
        print(
            Panel(
                e.logs,
                title="[bold red]View execution error[/bold red]",
            )
        )
        print("[red]View execution failed[/red]")
        exit(1)

    if logs:
        print(
            Panel(
                logs,
                title="[bold]View container output[/bold]",
            )
        )

    print(
        f"[bold]=>[/bold] Successfully generated [bold]{view_name}[/bold] view"
    )

    print(
        "[blue][bold]=>[/bold] Loading interactive view in web browser[/blue]"
    )

    matplotlib.use("WebAgg")

    with open(
        VIEW_ARTEFACTS_DIR.format(base_path=DATAKIT_PATH, run_name=run_name)
        + f"/{view_name}.p",
        "rb",
    ) as f:
        # NOTE: The matplotlib version in CLI must be >= the version of
        # matplotlib used to generate the plot (which is chosen by the user)
        # So the CLI should be kept up to date at all times

        # Load matplotlib figure
        pickle.load(f)

    plt.show()


@app.command()
def load(
    variable_name: Annotated[
        str,
        typer.Argument(
            help="Name of variable to populate",
            show_default=False,
        ),
    ],
    path: Annotated[
        str,
        typer.Argument(
            help="Path to data to ingest (xml, csv)", show_default=False
        ),
    ],
) -> None:
    """Load data into configuration variable"""
    run_name = get_active_run()

    # Load resource into TabularDataResource object
    resource = load_resource_by_variable(
        run_name=run_name,
        variable_name=variable_name,
        base_path=DATAKIT_PATH,
    )

    # Read CSV into resource
    print(f"[bold]=>[/bold] Reading {path}")
    resource.data = pd.read_csv(path)

    # Write to resource
    write_resource(
        run_name=run_name, resource=resource, base_path=DATAKIT_PATH
    )

    # Execute any applicable relationships
    execute_relationship(
        run_name=run_name,
        variable_name=variable_name,
    )

    print("[bold]=>[/bold] Resource successfully loaded!")


@app.command()
def set(
    variable_ref: Annotated[
        str,
        typer.Argument(
            help=(
                "Either a variable name, or a table reference in the format "
                "[resource name].[primary key].[column name]"
            ),
            show_default=False,
        ),
    ],
    variable_value: Annotated[
        str,  # Workaround for union types not being supported by Typer yet
        # Union[str, int, float, bool],
        typer.Argument(
            help="Value to set",
            show_default=False,
        ),
    ],
) -> None:
    """Set a variable value"""
    run_name = get_active_run()

    # Parse value (workaround for Typer not supporting Union types :<)
    variable_value = dumb_str_to_type(variable_value)

    if "." in variable_ref:
        # Variable reference is a table reference

        # Check the variable_ref matches the pattern:
        # [resource].[primary key].[column]
        pattern = re.compile(
            r"^([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)$"
        )

        if not pattern.match(variable_ref):
            print(
                "[red]Variable name argument must be either a variable name "
                "or a table reference in the format "
                r"\[resource name].\[primary key].\[column name][/red]"
            )
            exit(1)

        # Parse variable and row/col names
        variable_name, row_name, col_name = variable_ref.split(".")

        # Load param resource
        resource = load_resource_by_variable(
            run_name=run_name,
            variable_name=variable_name,
            base_path=DATAKIT_PATH,
        )

        # Check it's a tabular data resource
        if resource.profile != "tabular-data-resource":
            print(
                f"[red]Resource [bold]{resource.name}[/bold] is not of type "
                '"tabular-data-resource"[/red]'
            )
            exit(1)

        # If data is not populated, something has gone wrong
        if not resource:
            print(
                f'[red]Parameter resource [bold]{resource.name}[/bold] "data" '
                'field is empty. Try running "dk reset"?[/red]'
            )
            exit(1)

        print(
            f"[bold]=>[/bold] Setting table value at row [bold]{row_name}"
            f"[/bold] and column [bold]{col_name}[/bold] to "
            f"[bold]{variable_value}[/bold]"
        )

        # Set table value
        try:
            # This will generate a key error if row_name doesn't exist
            # The assignment doesn't unfortunately
            resource.data.loc[row_name]  # Ensure row exists
            resource.data.loc[row_name, col_name] = variable_value
        except KeyError:
            print(
                f'[red]Could not find row "{row_name}" or column "{col_name}" '
                f"in resource [bold]{resource.name}[/bold][/red]"
            )
            exit(1)

        # Write resource
        write_resource(
            run_name=run_name, resource=resource, base_path=DATAKIT_PATH
        )

        print(
            f"[bold]=>[/bold] Successfully set table value at row "
            f"[bold]{row_name}[/bold] and column [bold]{col_name}[/bold] to "
            f"[bold]{variable_value}[/bold] in resource [bold]{resource.name}"
            "[/bold]"
        )
    else:
        # Variable reference is a simple variable name
        variable_name = variable_ref

        # Load variable signature
        signature = load_variable_signature(
            run_name, variable_name, base_path=DATAKIT_PATH
        )

        # Convenience dict mapping opendatakit types to Python types
        type_map = {
            "string": [str],
            "boolean": [bool],
            "number": [float, int],
        }

        # Check the value is of the expected type for this variable
        # Raise some helpful errors
        if signature.get("profile") == "tabular-data-resource":
            print('[red]Use command "load" for tabular data resource[/red]')
            exit(1)
        elif "parameter-tabular-data-resource" in signature.get("profile", ""):
            print('[red]Use command "set-param" for parameter resource[/red]')
            exit(1)
        # Specify False as fallback value here to avoid "None"s leaking through
        elif not (type(variable_value) in type_map.get(signature["type"], [])):
            print(
                f"[red]Variable value must be of type {signature['type']}"
                "[/red]"
            )
            exit(1)

        # If this variable has an enum, check the value is allowed
        if signature.get("enum", False):
            allowed_values = [i["value"] for i in signature["enum"]]
            if variable_value not in allowed_values:
                print(
                    f"[red]Variable value must be one of {allowed_values}"
                    "[/red]"
                )
                exit(1)

        # Check if nullable
        if not signature["null"]:
            if not variable_value:
                print("[red]Variable value cannot be null[/red]")
                exit(1)

        # Load run configuration
        run = load_run_configuration(run_name, base_path=DATAKIT_PATH)

        # Set variable value
        find_by_name(
            run["data"]["inputs"] + run["data"]["outputs"], variable_name
        )["value"] = variable_value

        # Write configuration
        write_run_configuration(run, base_path=DATAKIT_PATH)

        # Execute any relationships applied to this variable value
        execute_relationship(
            run_name=run_name,
            variable_name=variable_name,
        )

        print(
            f"[bold]=>[/bold] Successfully set [bold]{variable_name}[/bold] "
            "variable"
        )

    show(variable_name)


@app.command()
def reset():
    """Reset datakit to clean state

    Removes all run outputs and resets configurations to default
    """
    # Remove all run directories
    for f in os.scandir(DATAKIT_PATH):
        if f.is_dir() and f.path.endswith(".run"):
            print(f"[bold]=>[/bold] Deleting [bold]{f.name}[/bold]")
            shutil.rmtree(f.path)

    # Remove all run references from datakit.json
    datakit = load_datakit_configuration(base_path=DATAKIT_PATH)
    datakit["runs"] = []
    write_datakit_configuration(datakit, base_path=DATAKIT_PATH)

    # Remove CLI config
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)


@app.command()
def new(
    algorithm_name: Annotated[
        str,
        typer.Argument(
            help="Name of the algorithm to generate",
            show_default=False,
        ),
    ],
) -> None:
    """Generate a new datakit and algorithm scaffold"""
    # Create new datakit directory
    datakit_name = f"{algorithm_name}-datakit"
    datakit_dir = f"{DATAKIT_PATH}/{datakit_name}"
    algorithm_dir = f"{datakit_dir}/{algorithm_name}"

    if not os.path.exists(datakit_dir):
        os.makedirs(datakit_dir)
        os.makedirs(algorithm_dir)
    else:
        print(f'[red]Directory named "{datakit_name}" already exists[/red]')
        exit(1)

    current_time = int(time.time())

    datakit = {
        "title": "New datakit",
        "description": "A new datakit",
        "profile": "datakit",
        "algorithms": [algorithm_name],
        "runs": [],
        "repository": {},
        "created": current_time,
        "updated": current_time,
    }

    algorithm = {
        "name": algorithm_name,
        "title": "New algorithm",
        "profile": "datakit-algorithm",
        "code": "algorithm.py",
        "container": "datakits/python-run-base:latest",
        "signature": {
            "inputs": [
                {
                    "name": "x",
                    "title": "X",
                    "description": "An input variable",
                    "type": "number",
                    "null": False,
                    "default": {"value": 42},
                },
            ],
            "outputs": [
                {
                    "name": "result",
                    "title": "Result",
                    "description": "An output variable",
                    "type": "number",
                    "null": True,
                    "default": {"value": None},
                },
            ],
        },
    }

    algorithm_code = '''def main(x):
    """An algorithm that multiplies the input variable by 2"""
    return {
        "result": x*2,
    }'''

    write_datakit_configuration(datakit, base_path=datakit_dir)
    write_algorithm(algorithm, base_path=datakit_dir)
    with open(f"{datakit_dir}/{algorithm_name}/algorithm.py", "x") as f:
        f.write(algorithm_code)

    print(f"[bold]=>[/bold] Successfully created [bold]{datakit_name}[/bold]")


if __name__ == "__main__":
    app()
