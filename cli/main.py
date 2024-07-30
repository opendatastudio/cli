import os
import json
import pickle
import typer
import docker
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import ntpath
import time
from pathlib import Path
from ast import literal_eval
from typing import Optional, Any, List, Dict
from typing_extensions import Annotated
from rich import print
from rich.panel import Panel
from tabulate import tabulate
from opendatafit.resources import TabularDataResource
from opendatafit.helpers import find_by_name


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


def load_resource(
    algorithm: str, argument: str, argument_space: str = "default"
) -> dict:
    """Load a resource object for a specified argument"""
    print(
        f"[bold]=>[/bold] Finding resource for argument "
        f"[bold]{argument}[/bold]"
    )
    # Get name of resource and metaschema from specified argument
    with open(f"{ARGUMENTS_PATH}/{algorithm}.{argument_space}.json", "r") as f:
        argument_obj = find_by_name(json.load(f)["data"], argument)
        if argument_obj is None:
            raise ValueError(
                (
                    f"Can't find argument named [bold]{argument}[/bold] in "
                    f"argument space [bold]{argument_space}[/bold]"
                )
            )
        resource = argument_obj["resource"]
        metaschema = argument_obj["metaschema"]

    # Load resource with metaschema
    print(f"[bold]=>[/bold] Loading resource [bold]{resource}[/bold]")
    resource_path = f"{RESOURCES_PATH}/{resource}.json"
    with open(resource_path, "r") as rf, open(
        f"{METASCHEMAS_PATH}/{metaschema}.json", "r"
    ) as mf:
        resource_obj = json.load(rf)
        resource_obj["metaschema"] = json.load(mf)["schema"]

        # Load external schema
        if resource_obj["schema"] == "metaschema":
            # Copy metaschema to schema
            resource_obj["schema"] = resource_obj["metaschema"]
            # Label schema as metaschema copy so we don't overwrite it when
            # writing back to resource
            resource_obj["schema"]["type"] = "metaschema"

    return resource_obj


def write_resource(resource: dict) -> None:
    """Write updated resource to file"""
    resource_path = f"{RESOURCES_PATH}/{resource['name']}.json"

    print(f"[bold]=>[/bold] Writing to resource at {resource_path}")

    resource.pop("metaschema")  # Don't write metaschema

    if resource["schema"].get("type") == "metaschema":
        resource["schema"] = "metaschema"  # Don't write metaschema copy

    with open(resource_path, "w") as f:
        json.dump(resource, f, indent=2)

    # Update modified time in datapackage.json
    with open(f"{DATAPACKAGE_PATH}/datapackage.json", "r") as f:
        dp = json.load(f)

    dp["updated"] = int(time.time())

    with open(f"{DATAPACKAGE_PATH}/datapackage.json", "w") as f:
        json.dump(dp, f, indent=2)


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
        print(f"[red][bold]=> {image}[/bold] container execution failed[/red]")
        exit(1)


def get_default_algorithm() -> str:
    """Return the default algorithm for the current datapackage"""
    with open(f"{DATAPACKAGE_PATH}/datapackage.json", "r") as f:
        return json.load(f)["algorithms"][0]


# Commands


@app.command()
def run(
    algorithm: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the algorithm to run", show_default=False
        ),
    ] = get_default_algorithm(),
    arguments: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the argument space to pass to the algorithm"
        ),
    ] = "default",
    container: Annotated[
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
    if container is None:
        # Get default container for the specified argument space
        with open(f"{ARGUMENTS_PATH}/{algorithm}.{arguments}.json", "r") as f:
            container = json.load(f)["container"]

    # Execute algorithm container and print any logs
    print(
        f"[bold]=>[/bold] Executing [bold]{algorithm}[/bold] with "
        f"[bold]{arguments}[/bold] argument space in container "
        f"[bold]{container}[/bold]"
    )

    run_container_and_print_logs(
        image=container,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "ALGORITHM": algorithm,
            "CONTAINER": container,
            "ARGUMENTS": arguments,
        },
        panel_title="Algorithm container output",
    )

    print(f"[bold]=>[/bold] Executed [bold]{algorithm}[/bold] successfully")


@app.command()
def view_table(
    argument: Annotated[
        str,
        typer.Argument(
            help="Name of argument to view",
            show_default=False,
        ),
    ],
    algorithm: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    resource = load_resource(algorithm, argument, argument_space)

    if "tabular-data-resource" in resource["profile"]:
        print(tabulate(resource["data"], headers="keys", tablefmt="github"))
    else:
        print(
            f"[red][bold]=>[/bold]Can't view non-tabular resource "
            f"{resource['name']}[/red]"
        )
        exit(1)


@app.command()
def view(
    view: Annotated[
        str,
        typer.Argument(
            help="The name of the view to render", show_default=False
        ),
    ],
    container: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the container to render the view in",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Render a view locally"""
    # Load view json
    with open(f"{VIEWS_PATH}/{view}.json", "r") as f:
        view_json = json.load(f)

    # Check required resources are populated
    for resource in view_json["resources"]:
        with open(f"{RESOURCES_PATH}/{resource}.json", "r") as f:
            if not json.load(f)["data"]:
                raise ValueError(
                    f"""Can't render view with empty resource {resource}. \
                        Have you executed the datapackage?"""
                )

    if container is None:
        # Use container defined in view
        container = view_json["container"]

    # Execute view
    print(f"[bold]=>[/bold] Generating [bold]{view}[/bold] view")

    run_container_and_print_logs(
        image=container,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "VIEW": view,
        },
        panel_title="View container output",
    )

    print(f"[bold]=>[/bold] Successfully generated [bold]{view}[/bold] view")

    print(
        "[blue][bold]=>[/bold] Loading interactive view in web browser[/blue]"
    )

    matplotlib.use("WebAgg")

    with open(f"{VIEWS_PATH}/{view}.p", "rb") as f:
        # NOTE: The matplotlib version in CLI must be >= the version of
        # matplotlib used to generate the plot (which is chosen by the user)
        # So the CLI should be kept up to date at all times

        # Load matplotlib figure
        pickle.load(f)

    plt.show()


@app.command()
def load(
    argument: Annotated[
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
    algorithm: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Load data into algorithm argument"""
    # Load resource into TabularDataResource object
    resource_obj = load_resource(algorithm, argument, argument_space)
    table = TabularDataResource(resource=resource_obj)

    # Read CSV into resource
    print(f"[bold]=>[/bold] Reading {path}")
    table.data = pd.read_csv(path)

    # Write to resource
    write_resource(table.to_dict())

    print("[bold]=>[/bold] Resource successfully loaded!")


@app.command()
def set_param(
    argument: Annotated[
        str,
        typer.Argument(
            help="Name of parameter argument to populate",
            show_default=False,
        ),
    ],
    name: Annotated[
        str,
        typer.Argument(
            help="Name of parameter to set",
            show_default=False,
        ),
    ],
    value: Annotated[
        str,  # Workaround for union types not being supported by Typer yet
        # Union[str, int, float, bool],
        typer.Argument(
            help="Value to set",
            show_default=False,
        ),
    ],
    algorithm: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Set a parameter value"""
    # Parse value (workaround for Typer not supporting Union types :<)
    value = dumb_str_to_type(value)

    # Load param resource
    resource = load_resource(algorithm, argument, argument_space)

    # Check it's a param resource
    if resource.get("profile") != "parameter-tabular-data-resource":
        raise ValueError(
            f"Resource \"{resource['name']}\" is not of type \"parameters\""
        )

    # If data is not populated, something has gone wrong
    if not resource["data"]:
        raise ValueError(
            f"Parameter resource {resource['name']} \"data\" field is empty. "
            'Try running "opendata-cli reset"?'
        )

    print(
        f"[bold]=>[/bold] Setting parameter [bold]{name}[/bold] to value "
        f"[bold]{value}[/bold]"
    )

    # Set parameter value (initial guess)
    try:
        find_by_name(resource["data"], name)["init"] = value
    except TypeError:
        raise ValueError(
            f'Could not find parameter "{name}" in resource '
            f"\"{resource['name']}\""
        )

    # Write resource
    write_resource(resource)

    print(
        (
            f"[bold]=>[/bold] Successfully set parameter [bold]{name}[/bold] "
            f"value to [bold]{value}[/bold] in parameter resource "
            f"[bold]{resource['name']}[/bold]"
        )
    )


@app.command()
def set_arg(
    argument: Annotated[
        str,
        typer.Argument(
            help="Name of argument to set",
            show_default=False,
        ),
    ],
    value: Annotated[
        str,  # Workaround for union types not being supported by Typer yet
        # Union[str, int, float, bool],
        typer.Argument(
            help="Value to set",
            show_default=False,
        ),
    ],
    algorithm: Annotated[
        Optional[str],
        typer.Argument(help="Name of target algorithm", show_default=False),
    ] = get_default_algorithm(),
    argument_space: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    """Set an argument value"""
    # Parse value (workaround for Typer not supporting Union types :<)
    value = dumb_str_to_type(value)

    # Load argument
    argument_space_path = f"{ARGUMENTS_PATH}/{algorithm}.{argument_space}.json"

    with open(argument_space_path, "r") as f:
        argument_space = json.load(f)

    # Load interface
    with open(f"{ALGORITHMS_PATH}/{algorithm}.json", "r") as f:
        interface = find_by_name(json.load(f)["interface"], argument)

    type_map = {
        "string": str,
        "boolean": bool,
        "number": float | int,
    }

    # Check the value is of the expected type for this argument
    # Raise some helpful errors
    if interface.get("profile") == "tabular-data-resource":
        raise ValueError('Use command "load" for tabular data resource')
    elif interface.get("profile") == "parameter-tabular-data-resource":
        raise ValueError('Use command "set-param" for parameter resource')
    # Specify False as fallback value here to avoid "None"s leaking through
    elif type_map.get(interface["type"], False) != type(value):
        raise ValueError(f"Argument value must be of type {interface['type']}")

    # If this argument has an enum, check the value is allowed
    if interface.get("enum", False):
        allowed_values = [i["value"] for i in interface["enum"]]
        if value not in allowed_values:
            raise ValueError(f"Argument value must be one of {allowed_values}")

    # TODO: CHECK NULL IF NULL NOT ALLOWED

    # Set value
    find_by_name(argument_space["data"], argument)["value"] = value

    # Write arguments
    with open(argument_space_path, "w") as f:
        json.dump(argument_space, f, indent=2)


@app.command()
def reset():
    """Remove all run outputs from datapackage - reset to empty state"""
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
            raise ValueError(
                f"Unable to reset resource "
                f"[bold]{resource_obj['name']}[/bold] with unrecognised "
                f"resource profile [bold]{resource_obj['profile']}[/bold]"
            )

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
