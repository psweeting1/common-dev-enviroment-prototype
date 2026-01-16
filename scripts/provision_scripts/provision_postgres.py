import os
import time
import yaml

from scripts.commodities import (
    commodity_required,
    container_to_commodity,
    commodity_provisioned,
    set_commodity_provision_status,
)

from scripts.utilities import (
    colorize_red,
    colorize_yellow,
    colorize_pink,
    colorize_lightblue,
    colorize_green,
    run_command,
    run_command_noshell,
)


def postgres_container(postgres_version: str) -> str:
    if postgres_version == '13':
        return 'postgres-13'
    elif postgres_version == '17':
        return 'postgres-17'
    else:
        print(colorize_red(f"Unknown PostgreSQL version ({postgres_version}) specified."))
        return ''


def provision_postgres(root_loc: str, new_containers: list, postgres_version: str) -> None:
    container = postgres_container(postgres_version)
    if not container:
        return

    config_path = os.path.join(root_loc, 'dev-env-config', 'configuration.yml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not config or 'applications' not in config:
        return

    new_db_container = container in new_containers
    if new_db_container:
        print(colorize_yellow(
            f"The Postgres {postgres_version} container has been newly created - "
            "provision status in .commodities will be ignored"
        ))

    started = False
    for appname in config['applications']:
        if not postgres_required(root_loc, appname, container):
            continue
        sql_path = os.path.join(root_loc, 'apps', appname, 'fragments', 'postgres-init-fragment.sql')
        if os.path.exists(sql_path):
            started = start_postgres_maybe(
                root_loc, appname, started, new_db_container, postgres_version
            )


def postgres_required(root_loc: str, appname: str, container: str) -> bool:
    config_path = os.path.join(root_loc, 'apps', appname, 'configuration.yml')
    return (
            os.path.exists(config_path) and
            commodity_required(root_loc, appname, container_to_commodity(container))
    )


def start_postgres_maybe(
        root_loc: str,
        appname: str,
        started: bool,
        new_db_container: bool,
        postgres_version: str,
) -> bool:
    container = postgres_container(postgres_version)
    if not container:
        return started

    print(colorize_pink(f"Found Postgres init fragment SQL in {appname}"))
    if commodity_provisioned(root_loc, appname, container_to_commodity(container)) and not new_db_container:
        print(colorize_yellow(
            f"Postgres {postgres_version} has previously been provisioned for {appname}, skipping"
        ))
    else:
        started = start_postgres(root_loc, appname, started, postgres_version)
    return started


def start_postgres(
        root_loc: str,
        appname: str,
        started: bool,
        postgres_version: str,
) -> bool:
    container = postgres_container(postgres_version)
    if not container:
        return started

    if not started:
        run_command_noshell(os.environ['DC_CMD'].split() + ['up', '-d', container])
        print(colorize_lightblue(f"Waiting for Postgres {postgres_version} to finish initialising"))

        command_output = []
        command_outcode = 1
        while command_outcode != 0 or not check_healthy_output(command_output):
            command_output.clear()
            command_outcode = run_command(
                f'docker inspect --format="{{{{json .State.Health.Status}}}}" {container}',
                command_output
            )
            print(colorize_yellow(f"Postgres {postgres_version} is unavailable - sleeping"))
            time.sleep(3)
        time.sleep(3)
        print(colorize_green(f"Postgres {postgres_version} is ready"))
        started = True

    run_initialisation(root_loc, appname, container)
    set_commodity_provision_status(root_loc, appname, container_to_commodity(container), True)
    return started


def run_initialisation(root_loc: str, appname: str, container: str) -> None:
    sql_fragment = 'postgres-init-fragment.sql'
    app_fragments = os.path.join(root_loc, 'apps', appname, 'fragments')
    run_command(
        f'tar -c -C {app_fragments} {sql_fragment} | docker cp - {container}:/'
    )
    print(colorize_pink(f"Executing SQL fragment for {appname}..."))
    run_command_noshell(['docker', 'exec', container, 'psql', '-q', '-f', sql_fragment])
    print(colorize_pink('...done.'))


def check_healthy_output(command_output: list) -> bool:
    return any('healthy' in line for line in command_output)
