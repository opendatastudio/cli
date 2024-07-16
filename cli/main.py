import os
import json
import pickle
import typer
import docker
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional
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
):
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
):
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
            show_default=False,
        ),
    ] = "default",
):
    """Load data into algorithm argument"""
    # Get name of resource and metaschema from specified argument
    with open(f"{ARGUMENTS_PATH}/{algorithm}.{argument_space}.json", "r") as f:
        argument_obj = find_by_name(json.load(f)["data"], argument)
        resource = argument_obj["resource"]
        metaschema = argument_obj["metaschema"]

    # Load resource with metaschema
    resource_path = f"{RESOURCES_PATH}/{resource}.json"
    with open(resource_path, "r") as rf, open(
        f"{METASCHEMAS_PATH}/{metaschema}.json", "r"
    ) as mf:
        resource_obj = json.load(rf)
        resource_obj["metaschema"] = json.load(mf)["schema"]

    # Load into Tabular Data object
    print(f'[bold]=>[/bold] Loading "{resource}" resource')
    table = TabularDataResource(resource=resource_obj)

    # Read CSV into resource
    print(f"[bold]=>[/bold] Reading {path}")
    table.data = pd.read_csv(path)

    # Write to resource
    print(f"[bold]=>[/bold] Writing to resource at {resource_path}")
    updated_resource = table.to_dict()
    updated_resource.pop("metaschema")  # Don't write metaschema
    with open(resource_path, "w") as f:
        json.dump(updated_resource, f, indent=2)

    print("[bold]=>[/bold] Resource successfully loaded!")


@app.command()
def reset():
    # Remove all run outputs from datapackage, reset to original state

    # Remove all data and schemas from resources

    # Remove view render artefacts - .png, .p
    pass


if __name__ == "__main__":
    app()
