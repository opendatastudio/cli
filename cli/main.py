import os
import json
import pickle
import typer
import docker
import matplotlib
import matplotlib.pyplot as plt
from typing import Optional
from typing_extensions import Annotated


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
    if container is None:
        # Use container defined in view
        with open(f"{VIEWS_PATH}/{view}.json", "r") as f:
            container = json.load(f)["container"]

    # Execute view
    print(f"Generating {view} view...")

    container_log = client.containers.run(
        image=container,
        volumes=[f"{DATAPACKAGE_PATH}:/usr/src/app/datapackage"],
        environment={
            "VIEW": view,
        },
    )

    print(container_log.decode("utf-8").strip())

    print(f"Generated {view} view successfully")

    print("Loading interactive view in web browser...")
    matplotlib.use("WebAgg")

    with open(f"{VIEWS_PATH}/{view}.p", "rb") as f:
        # NOTE: The matplotlib version in CLI must be >= the version of
        # matplotlib used to generate the plot (which is chosen by the user)
        # So the CLI should be kept up to date at all times

        # Load matplotlib figure
        pickle.load(f)

    plt.show()


@app.command()
def reset():
    # Remove all outputs from datapackage
    pass


if __name__ == "__main__":
    app()
