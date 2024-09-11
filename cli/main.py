import os
import json
import pickle
import typer
import docker
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import ntpath
from pathlib import Path
from ast import literal_eval
from typing import Optional, Any
from typing_extensions import Annotated
from rich import print
from rich.panel import Panel
from tabulate import tabulate
from opendatapy.datapackage import (
    ExecutionError,
    ResourceError,
    execute_datapackage,
    execute_view,
    load_resource_by_variable,
    write_resource,
)
from opendatapy.helpers import find_by_name


app = typer.Typer()


client = docker.from_env()


# Assume we are always at the datapackage root
# TODO: Validate we actually are, and that this is a datapackage
DATAPACKAGE_PATH = os.getcwd()
RESOURCES_PATH = DATAPACKAGE_PATH + "/resources"
ALGORITHMS_PATH = DATAPACKAGE_PATH + "/algorithms"
CONFIGURATIONS_PATH = DATAPACKAGE_PATH + "/configurations"
VIEWS_PATH = DATAPACKAGE_PATH + "/views"


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
    """Return the default algorithm for the current datapackage"""
    with open(f"{DATAPACKAGE_PATH}/datapackage.json", "r") as f:
        return json.load(f)["algorithms"][0]


def get_default_configuration() -> str:
    """Return the default configuration for the current datapackage"""
    return get_default_algorithm() + ".default"


# Commands


@app.command()
def run(
    configuration_name: Annotated[
        Optional[str],
        typer.Argument(help="The name of the configuration to run"),
    ] = get_default_configuration(),
) -> None:
    """Run the specified configuration"""
    # Execute algorithm container and print any logs
    print(f"[bold]=>[/bold] Executing [bold]{configuration_name}[/bold]")

    try:
        logs = execute_datapackage(
            client,
            configuration_name,
            base_path=DATAPACKAGE_PATH,
        )
    except ExecutionError as e:
        print(type(e.logs))
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

    print(
        (
            f"[bold]=>[/bold] Executed [bold]{configuration_name}[/bold] "
            "successfully"
        )
    )


@app.command()
def view_table(
    variable_name: Annotated[
        str,
        typer.Argument(
            help="Name of variable to view",
            show_default=False,
        ),
    ],
    configuration_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target configuration",
            show_default=True,
        ),
    ] = get_default_configuration(),
) -> None:
    """Print a tabular data variable"""
    resource = load_resource_by_variable(
        variable_name,
        configuration_name,
        base_path=DATAPACKAGE_PATH,
    )

    if "tabular-data-resource" in resource.profile:
        print(tabulate(resource.data, headers="keys", tablefmt="github"))
    else:
        print(f"[red]Can't view non-tabular resource {resource['name']}[/red]")
        exit(1)


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
    print(f"[bold]=>[/bold] Generating [bold]{view_name}[/bold] view")

    try:
        logs = execute_view(client, view_name, base_path=DATAPACKAGE_PATH)
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

    with open(f"{VIEWS_PATH}/{view_name}.p", "rb") as f:
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
    configuration_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target configuration",
            show_default=True,
        ),
    ] = get_default_configuration(),
) -> None:
    """Load data into configuration variable"""
    # Load resource into TabularDataResource object
    resource = load_resource_by_variable(
        variable_name,
        configuration_name,
        base_path=DATAPACKAGE_PATH,
    )

    # Read CSV into resource
    print(f"[bold]=>[/bold] Reading {path}")
    resource.data = pd.read_csv(path)

    # Write to resource
    write_resource(resource, base_path=DATAPACKAGE_PATH)

    print("[bold]=>[/bold] Resource successfully loaded!")


@app.command()
def set_param(
    variable_name: Annotated[
        str,
        typer.Argument(
            help="Name of parameter variable to populate",
            show_default=False,
        ),
    ],
    param_name: Annotated[
        str,
        typer.Argument(
            help="Name of parameter to set",
            show_default=False,
        ),
    ],
    param_value: Annotated[
        str,  # Workaround for union types not being supported by Typer yet
        # Union[str, int, float, bool],
        typer.Argument(
            help="Value to set",
            show_default=False,
        ),
    ],
    configuration_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target configuration",
            show_default=True,
        ),
    ] = get_default_configuration(),
) -> None:
    """Set a parameter value"""
    # Parse value (workaround for Typer not supporting Union types :<)
    param_value = dumb_str_to_type(param_value)

    # Load param resource
    resource = load_resource_by_variable(
        variable_name,
        configuration_name,
        base_path=DATAPACKAGE_PATH,
    )

    # Check it's a param resource
    if resource.profile != "parameter-tabular-data-resource":
        print(
            (
                f"[red]Resource [bold]{resource.name}[/bold] is not of "
                'type "parameters"[/red]'
            )
        )
        exit(1)

    # If data is not populated, something has gone wrong
    if not resource:
        print(
            (
                f"[red]Parameter resource [bold]{resource.name}[/bold] "
                '"data" field is empty. Try running "ods reset"?[/red]'
            )
        )
        exit(1)

    print(
        (
            f"[bold]=>[/bold] Setting parameter [bold]{param_name}[/bold] to "
            f"value [bold]{param_value}[/bold]"
        )
    )

    # Set parameter value (initial guess)
    try:
        # This will generate a key error if param_name doesn't exist
        # The assignment doesn't unfortunately
        resource.data.loc[param_name]  # Ensure param_name row exists
        resource.data.loc[param_name, "init"] = param_value
    except KeyError:
        print(
            (
                f'[red]Could not find parameter "{param_name}" in resource '
                f"[bold]{resource.name}[/bold][/red]"
            )
        )
        exit(1)

    # Write resource
    write_resource(resource, base_path=DATAPACKAGE_PATH)

    print(
        (
            f"[bold]=>[/bold] Successfully set parameter [bold]{param_name}"
            f"[/bold] value to [bold]{param_value}[/bold] in parameter "
            f"resource [bold]{resource.name}[/bold]"
        )
    )


@app.command()
def set_var(
    variable_name: Annotated[
        str,
        typer.Argument(
            help="Name of variable to set",
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
    configuration_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target configuration",
            show_default=True,
        ),
    ] = get_default_configuration(),
) -> None:
    """Set a variable value"""
    # Parse value (workaround for Typer not supporting Union types :<)
    variable_value = dumb_str_to_type(variable_value)

    # Load variable
    configuration_path = f"{CONFIGURATIONS_PATH}/{configuration_name}.json"

    with open(configuration_path, "r") as f:
        configuration = json.load(f)

    # Get algorithm name from configuration
    algorithm_name = configuration_name.split(".")[0]

    # Load signature
    with open(f"{ALGORITHMS_PATH}/{algorithm_name}.json", "r") as f:
        signature = find_by_name(json.load(f)["signature"], variable_name)

    type_map = {
        "string": str,
        "boolean": bool,
        "number": float | int,
    }

    # Check the value is of the expected type for this variable
    # Raise some helpful errors
    if signature.get("profile") == "tabular-data-resource":
        print('[red]Use command "load" for tabular data resource[/red]')
        exit(1)
    elif signature.get("profile") == "parameter-tabular-data-resource":
        print('[red]Use command "set-param" for parameter resource[/red]')
        exit(1)
    # Specify False as fallback value here to avoid "None"s leaking through
    elif type_map.get(signature["type"], False) != type(variable_value):
        print(f"[red]Variable value must be of type {signature['type']}[/red]")
        exit(1)

    # If this variable has an enum, check the value is allowed
    if signature.get("enum", False):
        allowed_values = [i["value"] for i in signature["enum"]]
        if variable_value not in allowed_values:
            print(f"[red]Variable value must be one of {allowed_values}[/red]")
            exit(1)

    # Check if nullable
    if not signature["null"]:
        if not variable_value:
            print("[red]Variable value cannot be null[/red]")
            exit(1)

    # Set value
    find_by_name(configuration["data"], variable_name)[
        "value"
    ] = variable_value

    # Write variables
    with open(configuration_path, "w") as f:
        json.dump(configuration, f, indent=2)

    print(
        (
            f"[bold]=>[/bold] Successfully set [bold]{variable_name}[/bold] "
            "variable"
        )
    )


@app.command()
def reset():
    """Reset datapackage to clean state

    Removes all run outputs and resets configurations to default
    """
    # Remove all data and schemas from tabular-data-resources
    print("[bold]=>[/bold] Checking tabular data resources")
    resource_pathlist = Path(RESOURCES_PATH).rglob("*.json")

    for path in resource_pathlist:
        with open(path, "r") as f:
            resource_obj = json.load(f)

        if resource_obj["profile"] == "parameter-tabular-data-resource":
            if resource_obj["data"] != resource_obj["defaultData"]:
                print(f"  - Resetting parameters {resource_obj['name']}")
                resource_obj["data"] = resource_obj["defaultData"]
        elif resource_obj["profile"] == "tabular-data-resource":
            if resource_obj["data"] or resource_obj["schema"]:
                print(f"  - Resetting resource {resource_obj['name']}")
                resource_obj["data"] = []
                resource_obj["schema"] = {}
        else:
            print(
                (
                    f"[red]Unable to reset resource "
                    f"[bold]{resource_obj['name']}[/bold] with unrecognised "
                    f"resource profile [bold]{resource_obj['profile']}[/bold]"
                    "[/red]"
                )
            )
            exit(1)

        with open(path, "w") as f:
            json.dump(resource_obj, f, indent=2)

    # Remove view render artefacts - .png, .p
    print("[bold]=>[/bold] Checking view artefacts")
    for file in os.scandir(VIEWS_PATH):
        if file.path.endswith(".png") or file.path.endswith(".p"):
            print(f"  - Removed {ntpath.basename(file.path)}")
            os.remove(file.path)

    print("[bold]=>[/bold] Checking variables in configuration")
    configurations_pathlist = Path(CONFIGURATIONS_PATH).rglob("*.json")

    for path in configurations_pathlist:
        if path.stem.endswith("default"):
            # Keep the default configuration, reset values to defaults
            # Load configuration
            with open(path, "r") as f:
                configuration = json.load(f)

            # Get algorithm name to determine which algorithm signature to load
            algorithm_name = str(path.stem).split(".")[0]

            # Load algorithm signature for this configuration
            with open(f"{ALGORITHMS_PATH}/{algorithm_name}.json", "r") as f:
                signature = json.load(f)["signature"]

            for variable in configuration["data"]:
                # Reset variables to default values from signature
                variable.update(
                    find_by_name(signature, variable["name"])["defaultData"]
                )

            # Write configuration
            with open(path, "w") as f:
                json.dump(configuration, f, indent=2)

            print(f"  - Reset {path.stem} values to default")
        else:
            # Delete any non-default  spaces
            os.remove(path)
            print(f"  - Removed {path.stem}")

    print("[bold]=>[/bold] Done!")


if __name__ == "__main__":
    app()
