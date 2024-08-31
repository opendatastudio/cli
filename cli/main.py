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
from typing import Optional, Any, List, Dict
from typing_extensions import Annotated
from rich import print
from rich.panel import Panel
from tabulate import tabulate
from opendatapy.datapackage import (
    load_resource_by_argument,
    write_resource,
)
from opendatapy.helpers import find_by_name


app = typer.Typer()


client = docker.from_env()


# Assume we are always at the datapackage root
# TODO: Validate we actually are, and that this is a datapackage
DATAPACKAGE_PATH = os.getcwd()
RESOURCES_PATH = DATAPACKAGE_PATH + "/resources"
METASCHEMAS_PATH = DATAPACKAGE_PATH + "/metaschemas"
ALGORITHMS_PATH = DATAPACKAGE_PATH + "/algorithms"
ARGUMENTS_PATH = DATAPACKAGE_PATH + "/arguments"
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


def run_container_and_print_logs(
    image: str,
    volumes: List[str],
    environment: Dict[str, str],
    panel_title: str,
) -> None:
    # We have to detach to get access to the container object and its logs
    # in the event of an error
    container = client.containers.run(
        image=image,
        volumes=volumes,
        environment=environment,
        detach=True,
    )

    # Block until container is finished running
    ret = container.wait()

    # Print container logs
    if container.logs():
        print(
            Panel(
                container.logs().decode("utf-8").strip(),
                title=panel_title,
            )
        )

    if ret["StatusCode"] != 0:
        print(f"[red][bold]{image}[/bold] container execution failed[/red]")
        exit(1)


def get_default_algorithm() -> str:
    """Return the default algorithm for the current datapackage"""
    with open(f"{DATAPACKAGE_PATH}/datapackage.json", "r") as f:
        return json.load(f)["algorithms"][0]


# Commands


@app.command()
def run(
    algorithm_name: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the algorithm to run", show_default=False
        ),
    ] = get_default_algorithm(),
    argument_space_name: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the argument space to pass to the algorithm"
        ),
    ] = "default",
    container_name: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the container to run in", show_default=False
        ),
    ] = None,
) -> None:
    """Run an algorithm

    By default, the run command executes the algorithm with the container
    defined in the specified argument space
    """
    if container_name is None:
        # Get default container for the specified argument space
        with open(
            f"{ARGUMENTS_PATH}/{algorithm_name}.{argument_space_name}.json",
            "r",
        ) as f:
            container_name = json.load(f)["container"]

    # Execute algorithm container and print any logs
    print(
        (
            f"[bold]=>[/bold] Executing [bold]{algorithm_name}[/bold] with "
            f"[bold]{argument_space_name}[/bold] argument space in container "
            f"[bold]{container_name}[/bold]"
        )
    )

    run_container_and_print_logs(
        image=container_name,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "ALGORITHM": algorithm_name,
            "CONTAINER": container_name,
            "ARGUMENTS": argument_space_name,
        },
        panel_title="Algorithm container output",
    )

    print(
        f"[bold]=>[/bold] Executed [bold]{algorithm_name}[/bold] successfully"
    )


@app.command()
def view_table(
    argument_name: Annotated[
        str,
        typer.Argument(
            help="Name of argument to view",
            show_default=False,
        ),
    ],
    algorithm_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Print a tabular data argument"""
    resource = load_resource_by_argument(
        algorithm_name,
        argument_name,
        argument_space_name,
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
    container_name: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the container to render the view in",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Render a view locally"""
    # Load view json
    with open(f"{VIEWS_PATH}/{view_name}.json", "r") as f:
        view = json.load(f)

    # Check required resources are populated
    for resource_name in view["resources"]:
        with open(f"{RESOURCES_PATH}/{resource_name}.json", "r") as f:
            if not json.load(f)["data"]:
                print(
                    (
                        f"[red]Can't render view with empty resource "
                        f"{resource_name}. Have you executed the datapackage?"
                        "[/red]"
                    )
                )
                exit(1)

    if container_name is None:
        # Use container defined in view
        container_name = view["container"]

    # Execute view
    print(f"[bold]=>[/bold] Generating [bold]{view_name}[/bold] view")

    run_container_and_print_logs(
        image=container_name,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "VIEW": view_name,
        },
        panel_title="View container output",
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
    argument_name: Annotated[
        str,
        typer.Argument(
            help="Name of argument to populate",
            show_default=False,
        ),
    ],
    path: Annotated[
        str,
        typer.Argument(
            help="Path to the data to ingest (xml, csv)", show_default=False
        ),
    ],
    algorithm_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Load data into algorithm argument"""
    # Load resource into TabularDataResource object
    resource = load_resource_by_argument(
        algorithm_name,
        argument_name,
        argument_space_name,
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
    argument_name: Annotated[
        str,
        typer.Argument(
            help="Name of parameter argument to populate",
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
    algorithm_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Set a parameter value"""
    # Parse value (workaround for Typer not supporting Union types :<)
    param_value = dumb_str_to_type(param_value)

    # Load param resource
    resource = load_resource_by_argument(
        algorithm_name,
        argument_name,
        argument_space_name,
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
def set_arg(
    argument_name: Annotated[
        str,
        typer.Argument(
            help="Name of argument to set",
            show_default=False,
        ),
    ],
    argument_value: Annotated[
        str,  # Workaround for union types not being supported by Typer yet
        # Union[str, int, float, bool],
        typer.Argument(
            help="Value to set",
            show_default=False,
        ),
    ],
    algorithm_name: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Set an argument value"""
    # Parse value (workaround for Typer not supporting Union types :<)
    argument_value = dumb_str_to_type(argument_value)

    # Load argument
    argument_space_path = (
        f"{ARGUMENTS_PATH}/{algorithm_name}.{argument_space_name}.json"
    )

    with open(argument_space_path, "r") as f:
        argument_space = json.load(f)

    # Load interface
    with open(f"{ALGORITHMS_PATH}/{algorithm_name}.json", "r") as f:
        interface = find_by_name(json.load(f)["interface"], argument_name)

    type_map = {
        "string": str,
        "boolean": bool,
        "number": float | int,
    }

    # Check the value is of the expected type for this argument
    # Raise some helpful errors
    if interface.get("profile") == "tabular-data-resource":
        print('[red]Use command "load" for tabular data resource[/red]')
        exit(1)
    elif interface.get("profile") == "parameter-tabular-data-resource":
        print('[red]Use command "set-param" for parameter resource[/red]')
        exit(1)
    # Specify False as fallback value here to avoid "None"s leaking through
    elif type_map.get(interface["type"], False) != type(argument_value):
        print(f"[red]Argument value must be of type {interface['type']}[/red]")
        exit(1)

    # If this argument has an enum, check the value is allowed
    if interface.get("enum", False):
        allowed_values = [i["value"] for i in interface["enum"]]
        if argument_value not in allowed_values:
            print(f"[red]Argument value must be one of {allowed_values}[/red]")
            exit(1)

    # Check if nullable
    if not interface["null"]:
        if not argument_value:
            print("[red]Argument value cannot be null[/red]")
            exit(1)

    # Set value
    find_by_name(argument_space["data"], argument_name)[
        "value"
    ] = argument_value

    # Write arguments
    with open(argument_space_path, "w") as f:
        json.dump(argument_space, f, indent=2)

    print(
        (
            f"[bold]=>[/bold] Successfully set [bold]{argument_name}[/bold] "
            "argument"
        )
    )


@app.command()
def reset():
    """Reset datapackage to clean state

    Removes all run outputs and resets argument spaces to default
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

    # TODO:
    # Reset arguments to argument defaults??? or interface defaults????
    print("[bold]=>[/bold] Checking arguments")
    arguments_pathlist = Path(ARGUMENTS_PATH).rglob("*.json")

    for path in arguments_pathlist:
        if path.stem.endswith("default"):
            # Keep the default argument space, reset values to defaults
            # Load argument space
            with open(path, "r") as f:
                argument_space = json.load(f)

            # Get algorithm name to determine which algorithm interface to load
            algorithm_name = str(path.stem).split(".")[0]

            # Load interface for this argument space
            with open(f"{ALGORITHMS_PATH}/{algorithm_name}.json", "r") as f:
                interface = json.load(f)["interface"]

            for argument in argument_space["data"]:
                # Reset argument to default values
                argument.update(
                    find_by_name(interface, argument["name"])["defaultData"]
                )

            # Write argument space
            with open(path, "w") as f:
                json.dump(argument_space, f, indent=2)

            print(f"  - Reset {path.stem} values to default")
        else:
            # Delete any non-default argument spaces
            os.remove(path)
            print(f"  - Removed {path.stem}")

    print("[bold]=>[/bold] Done!")


if __name__ == "__main__":
    app()
