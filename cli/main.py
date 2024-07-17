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


@app.command()
def run(
    algorithm: Annotated[
        str,
        typer.Argument(
            help="The name of the algorithm to run", show_default=False
        ),
    ],
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
        # Use container defined in argument space
        with open(f"{ARGUMENTS_PATH}/{algorithm}.{arguments}.json", "r") as f:
            container = json.load(f)["container"]

    # Execute algorithm
    client.containers.run(
        image=container,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "ALGORITHM": algorithm,
            "CONTAINER": container,
            "ARGUMENTS": arguments,
        },
    )

    print(f"Executed {algorithm} algorithm successfully")


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

    container_log = client.containers.run(
        image=container,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "VIEW": view,
        },
    )

    print(
        Panel(
            container_log.decode("utf-8").strip(),
            title="View container output",
        )
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
    algorithm: Annotated[
        str,
        typer.Argument(help="Name of target algorithm", show_default=False),
    ],
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
    algorithm: Annotated[
        str,
        typer.Argument(help="Name of target algorithm", show_default=False),
    ],
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
    if resource.get("type") != "parameters":
        raise ValueError(
            f"Resource \"{resource['name']}\" is not of type \"parameters\""
        )

    # If data is not populated, populate with defaults from metaschema first
    print(f'[bold]=>[/bold] Setting parameter "{name}" to value {value}')
    if not resource["data"]:
        resource["data"] = [
            {
                field["name"]: field.get("default", None)
                for field in resource["metaschema"]["fields"]
            }
        ]

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
            f'[bold]=>[/bold] Successfully set parameter "{name}" value to '
            f"{value} in parameter resource \"{resource['name']}\""
        )
    )


def set_arg(
    algorithm: Annotated[
        str,
        typer.Argument(help="Name of target algorithm", show_default=False),
    ],
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
    argument_space: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target argument space",
            show_default=True,
        ),
    ] = "default",
) -> None:
    # TODO: Set arg (e.g. enum, etc.)
    # (make sure to validate type and value if enum)
    pass


@app.command()
def reset():
    """Remove all run outputs from datapackage - reset to empty state"""
    # Remove all data and schemas from tabular-data-resources
    print("[bold]=>[/bold] Checking tabular data resources")
    resource_pathlist = Path(RESOURCES_PATH).rglob("*.json")

    for path in resource_pathlist:
        with open(path, "r") as f:
            resource_obj = json.load(f)

        if resource_obj["profile"] == "tabular-data-resource":
            if resource_obj.get("type") == "parameters":
                # Don't overwrite external schema reference
                # TODO: Do we just set the data to defaults here?
                if resource_obj["data"]:
                    print(f"  - Resetting parameters {resource_obj['name']}")
                    resource_obj["data"] = []
            else:
                if resource_obj["data"] or resource_obj["schema"]:
                    print(f"  - Resetting resource {resource_obj['name']}")
                    resource_obj["data"] = []
                    resource_obj["schema"] = {}

            with open(path, "w") as f:
                json.dump(resource_obj, f, indent=2)

    # Remove view render artefacts - .png, .p
    print("[bold]=>[/bold] Checking view artefacts")
    for file in os.scandir(VIEWS_PATH):
        if file.path.endswith(".png") or file.path.endswith(".p"):
            print(f"  - Removed {ntpath.basename(file.path)}")
            os.remove(file.path)

    print("[bold]=>[/bold] Done!")


def load_resource(
    algorithm: str, argument: str, argument_space: str = "default"
) -> dict:
    """Load a resource object for a specified argument"""
    print(f"[bold]=>[/bold] Finding resource for argument {argument}")
    # Get name of resource and metaschema from specified argument
    with open(f"{ARGUMENTS_PATH}/{algorithm}.{argument_space}.json", "r") as f:
        argument_obj = find_by_name(json.load(f)["data"], argument)
        if argument_obj is None:
            raise ValueError(
                (
                    f'Can\'t find argument named "{argument}" in argument '
                    f'space "{argument_space}"'
                )
            )
        resource = argument_obj["resource"]
        metaschema = argument_obj["metaschema"]

    # Load resource with metaschema
    print(f'[bold]=>[/bold] Loading resource "{resource}"')
    resource_path = f"{RESOURCES_PATH}/{resource}.json"
    with open(resource_path, "r") as rf, open(
        f"{METASCHEMAS_PATH}/{metaschema}.json", "r"
    ) as mf:
        resource_obj = json.load(rf)
        resource_obj["metaschema"] = json.load(mf)["schema"]

    return resource_obj


def write_resource(resource: dict) -> None:
    """Write updated resource to file"""
    resource_path = f"{RESOURCES_PATH}/{resource['name']}.json"
    print(f"[bold]=>[/bold] Writing to resource at {resource_path}")
    resource.pop("metaschema")  # Don't write metaschema
    with open(resource_path, "w") as f:
        json.dump(resource, f, indent=2)


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


if __name__ == "__main__":
    app()
