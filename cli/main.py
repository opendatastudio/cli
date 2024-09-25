import os
import shutil
import json
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
from opendatapy.datapackage import (
    ExecutionError,
    ResourceError,
    execute_datapackage,
    execute_view,
    load_resource_by_variable,
    write_resource,
    load_run_configuration,
    write_run_configuration,
    load_datapackage_configuration,
    write_datapackage_configuration,
    load_algorithm,
    VIEW_ARTEFACTS_DIR,
)
from opendatapy.helpers import find_by_name, find


app = typer.Typer()


client = docker.from_env()


# Assume we are always at the datapackage root
# TODO: Validate we actually are, and that this is a datapackage
DATAPACKAGE_PATH = os.getcwd()


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


def get_default_run() -> str:
    """Return the default configuration for the current datapackage"""
    return load_datapackage_configuration(base_path=DATAPACKAGE_PATH)["runs"][
        0
    ]


def get_default_algorithm() -> str:
    """Return the default algorithm for the current datapackage"""
    return load_datapackage_configuration(base_path=DATAPACKAGE_PATH)[
        "algorithms"
    ][0]


def execute_relationship(run_name: str, variable_name: str) -> None:
    """Execute any relationships applied to the given source variable"""
    # Load run configuration for modification
    run = load_run_configuration(run_name)

    # Load associated relationship
    with open(f"{get_default_algorithm()}/algorithm.json", "r") as f:
        relationship = find(
            json.load(f)["relationships"], "source", variable_name
        )

    # Apply relationship rules
    for rule in relationship["rules"]:
        if rule["type"] == "value":
            # Check if this rule applies to current run configuration state

            # Get source variable value
            value = find_by_name(run["data"], variable_name)["value"]

            # If the source variable value matches the rule value, execute
            # the relationship
            if value in rule["values"]:
                for target in rule["targets"]:
                    if "disabled" in target:
                        # Set target variable disabled value
                        target_variable = find_by_name(
                            run["data"], target["name"]
                        )
                        target_variable["disabled"] = target["disabled"]

                    if target["type"] == "resource":
                        # Set target resource data
                        target_resource = load_resource_by_variable(
                            run_name=run["name"],
                            variable_name=target["name"],
                            base_path=DATAPACKAGE_PATH,
                            as_dict=True,
                        )

                        target_resource["data"] = target["data"]

                        write_resource(
                            run_name=run["name"],
                            resource=target_resource,
                            base_path=DATAPACKAGE_PATH,
                        )
                    elif target["type"] == "value":
                        # Set target variable value
                        target_variable = find_by_name(
                            run["data"], target["name"]
                        )
                        target_variable["value"] = target["value"]
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
    write_run_configuration(run, base_path=DATAPACKAGE_PATH)


# Commands


@app.command()
def init(
    algorithm_name: Annotated[
        Optional[str],
        typer.Argument(help="The name of the algorithm to initialise"),
    ] = get_default_algorithm(),
) -> None:
    """Initialise a datapackage algorithm run"""
    # Create run directory
    run_dir = f"{DATAPACKAGE_PATH}/{algorithm_name}.run"
    os.makedirs(f"{run_dir}/resources")
    os.makedirs(f"{run_dir}/views")
    print(f"[bold]=>[/bold] Created run directory: {run_dir}")

    algorithm = load_algorithm(algorithm_name, base_path=DATAPACKAGE_PATH)

    # Generate default run configuration
    run = {
        "name": "bindfit.run",
        "title": f"Default run configuration for {algorithm_name} algorithm",
        "profile": "opends-run",
        "algorithm": f"{algorithm_name}",
        "container": f'{algorithm["container"]}',
        "data": [],
    }

    for variable in algorithm["signature"]:
        # Add variable defaults to run configuration
        run["data"].append(
            {
                "name": variable["name"],
                **variable["default"],
            }
        )

        # Initialise associated resources
        if variable["type"] == "resource":
            resource = {
                "name": variable["default"]["resource"],
                "title": variable["title"],
                "description": variable["description"],
                "profile": variable["profile"],
                "schema": variable.get("schema", {}),
                "data": [],
            }

            write_resource(
                run_name=run["name"],
                resource=resource,
                base_path=DATAPACKAGE_PATH,
            )

            print(f"[bold]=>[/bold] Generated resource: {resource['name']}")

    # Write generated configuration
    write_run_configuration(run, base_path=DATAPACKAGE_PATH)

    print(
        f"[bold]=>[/bold] Generated default run configuration: {run['name']}"
    )

    # Add default run to datapackage.json
    datapackage = load_datapackage_configuration(base_path=DATAPACKAGE_PATH)
    datapackage["runs"].append(run["name"])
    write_datapackage_configuration(datapackage, base_path=DATAPACKAGE_PATH)

    # Execute all relationships in order
    for relationship in algorithm["relationships"]:
        execute_relationship(
            run_name=run["name"],
            variable_name=relationship["source"],
        )
        print(
            f"[bold]=>[/bold] Executed relationship for variable [bold]"
            f'{relationship["source"]}[/bold]'
        )

    # TODO: Remove configurations from datapackage on reset
    # TODO: Create DatapackageClient for interacting with datapackages in
    # opendatapy - should do all the tasks the CLI does


@app.command()
def run(
    run_name: Annotated[
        Optional[str],
        typer.Argument(help="The name of the run to execute"),
    ] = None,
) -> None:
    """Run the specified configuration"""
    if run_name is None:
        run_name = get_default_run()

    # Execute algorithm container and print any logs
    print(f"[bold]=>[/bold] Executing [bold]{run_name}[/bold]")

    try:
        logs = execute_datapackage(
            client,
            run_name,
            base_path=DATAPACKAGE_PATH,
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
def view_table(
    variable_name: Annotated[
        str,
        typer.Argument(
            help="Name of variable to view",
            show_default=False,
        ),
    ],
    run_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target run",
            show_default=True,
        ),
    ] = None,
) -> None:
    """Print a tabular data variable"""
    if run_name is None:
        run_name = get_default_run()

    resource = load_resource_by_variable(
        run_name=run_name,
        variable_name=variable_name,
        base_path=DATAPACKAGE_PATH,
    )

    if "tabular-data-resource" in resource.profile:
        print(
            tabulate(
                resource.to_dict()["data"], headers="keys", tablefmt="github"
            )
        )
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
    run_name: Annotated[
        Optional[str],
        typer.Argument(help="The name of the run to view"),
    ] = None,
) -> None:
    """Render a view locally"""
    if run_name is None:
        run_name = get_default_run()

    print(f"[bold]=>[/bold] Generating [bold]{view_name}[/bold] view")

    try:
        logs = execute_view(
            docker_client=client,
            run_name=run_name,
            view_name=view_name,
            base_path=DATAPACKAGE_PATH,
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
        VIEW_ARTEFACTS_DIR.format(
            base_path=DATAPACKAGE_PATH, run_name=run_name
        )
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
    run_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target run",
            show_default=True,
        ),
    ] = None,
) -> None:
    """Load data into configuration variable"""
    if run_name is None:
        run_name = get_default_run()

    # Load resource into TabularDataResource object
    resource = load_resource_by_variable(
        run_name=run_name,
        variable_name=variable_name,
        base_path=DATAPACKAGE_PATH,
    )

    # Read CSV into resource
    print(f"[bold]=>[/bold] Reading {path}")
    resource.data = pd.read_csv(path)

    # Write to resource
    write_resource(
        run_name=run_name, resource=resource, base_path=DATAPACKAGE_PATH
    )

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
    run_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target run",
            show_default=True,
        ),
    ] = None,
) -> None:
    """Set a parameter value"""
    if run_name is None:
        run_name = get_default_run()

    # Parse value (workaround for Typer not supporting Union types :<)
    param_value = dumb_str_to_type(param_value)

    # Load param resource
    resource = load_resource_by_variable(
        run_name=run_name,
        variable_name=variable_name,
        base_path=DATAPACKAGE_PATH,
    )

    # Check it's a param resource
    if resource.profile != "parameter-tabular-data-resource":
        print(
            f"[red]Resource [bold]{resource.name}[/bold] is not of type "
            '"parameters"[/red]'
        )
        exit(1)

    # If data is not populated, something has gone wrong
    if not resource:
        print(
            f'[red]Parameter resource [bold]{resource.name}[/bold] "data" '
            'field is empty. Try running "opends reset"?[/red]'
        )
        exit(1)

    print(
        f"[bold]=>[/bold] Setting parameter [bold]{param_name}[/bold] to "
        f"value [bold]{param_value}[/bold]"
    )

    # Set parameter value (initial guess)
    try:
        # This will generate a key error if param_name doesn't exist
        # The assignment doesn't unfortunately
        resource.data.loc[param_name]  # Ensure param_name row exists
        resource.data.loc[param_name, "init"] = param_value
    except KeyError:
        print(
            f'[red]Could not find parameter "{param_name}" in resource '
            f"[bold]{resource.name}[/bold][/red]"
        )
        exit(1)

    # Write resource
    write_resource(
        run_name=run_name, resource=resource, base_path=DATAPACKAGE_PATH
    )

    print(
        f"[bold]=>[/bold] Successfully set parameter [bold]{param_name}"
        f"[/bold] value to [bold]{param_value}[/bold] in parameter resource "
        f"[bold]{resource.name}[/bold]"
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
    run_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of target run",
            show_default=True,
        ),
    ] = None,
) -> None:
    """Set a variable value"""
    if run_name is None:
        run_name = get_default_run()

    # Parse value (workaround for Typer not supporting Union types :<)
    variable_value = dumb_str_to_type(variable_value)

    # Load algorithum signature
    signature = find_by_name(
        load_algorithm(
            algorithm_name=run_name.split(".")[0],
            base_path=DATAPACKAGE_PATH,
        )["signature"],
        variable_name,
    )

    # Convenience dict mapping opends types to Python types
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

    # Load run configuration
    run = load_run_configuration(run_name, base_path=DATAPACKAGE_PATH)

    # Set variable value
    find_by_name(run["data"], variable_name)["value"] = variable_value

    # Write configuration
    write_run_configuration(run, base_path=DATAPACKAGE_PATH)

    # Execute any relationships applied to this variable value
    execute_relationship(
        run_name=run_name,
        variable_name=variable_name,
    )

    print(
        f"[bold]=>[/bold] Successfully set [bold]{variable_name}[/bold] "
        "variable"
    )


@app.command()
def reset():
    """Reset datapackage to clean state

    Removes all run outputs and resets configurations to default
    """
    # Remove all run directories
    for f in os.scandir(DATAPACKAGE_PATH):
        if f.is_dir() and f.path.endswith(".run"):
            print(f"[bold]=>[/bold] Deleting [bold]{f.name}[/bold]")
            shutil.rmtree(f.path)

    # Remove all run references from datapackage.json
    datapackage = load_datapackage_configuration(base_path=DATAPACKAGE_PATH)
    datapackage["runs"] = []
    write_datapackage_configuration(datapackage, base_path=DATAPACKAGE_PATH)


if __name__ == "__main__":
    app()
