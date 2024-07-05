import typer
from typing_extensions import Annotated
import git

from typing import Optional

app = typer.Typer()

@app.command()
def run(
        name: Annotated[str, typer.Argument(help="Algorithm to run", show_default=False)],
        container: Annotated[Optional[str], typer.Argument(help="Container to run algorithm", show_default=False)] = None,
        argument_space: Annotated[str, typer.Argument(help="Argument space to use for algorithm")] = "default"
        ):
    """
    Some documentation here

    By default, the run command executes the algorithm with the container
    defined in the algorithm definition
    """
    repo = git.Repo('.', search_parent_directories=True)
    print(repo.working_tree_dir)
    print(f"Hello {name}, {argument_space}")

@app.command()
def view(name: str):
    """
    Some documentation here
    """
    print(f"Bye {name}!")

if __name__ == "__main__":
    app()
