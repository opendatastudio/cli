import typer
from typing_extensions import Annotated

from typing import Optional

app = typer.Typer()


@app.command()
def run(
    algorithm: Annotated[
        str,
        typer.Argument(
            help="The name of the algorithm to run", show_default=False
        ),
    ],
    container: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the container to run in", show_default=False
        ),
    ] = None,
    arguments: Annotated[
        Optional[str],
        typer.Argument(
            help="The name of the argument space to pass to the algorithm"
        ),
    ] = "default",
):
    """Run an algorithm

    By default, the run command executes the algorithm with the container
    defined in the algorithm definition and the default argument space
    """
    print(f"Hello {algorithm}, {container}, {arguments}")


@app.command()
def view(view: Annotated[str, typer.Argument(help="", show_default=False)]):
    """Render a view locally"""
    raise NotImplementedError("Not yet implemented")


if __name__ == "__main__":
    app()
