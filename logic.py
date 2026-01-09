# logic.py

import os
import sys
import time
import argparse
import subprocess
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any

# Import helpers scripts
from scripts.delete_env_files import delete_files
from scripts.utilities import *
from scripts.update_apps import update_apps
from scripts.self_update import self_update
from scripts.docker_compose import *
from scripts.commodities import *
from scripts.provision_custom import provision_custom

def run_command(cmd: str, output_list: Optional[List[str]] = None) -> int:
    """
    Runs a shell command and optionally appends output lines to output_list.
    Returns the command's exit code.
    """
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if output_list is not None:
        output_list.extend(result.stdout.splitlines())
    return result.returncode

def colorize_lightblue(msg: str) -> str:
    return msg

def colorize_yellow(msg: str) -> str:
    return msg

def colorize_green(msg: str) -> str:
    return msg

def colorize_red(msg: str) -> str:
    return msg

def colorize_pink(msg: str) -> str:
    return msg

# Paths and constants
root_loc: str = os.path.dirname(os.path.abspath(__file__))
DEV_ENV_CONTEXT_FILE: str = os.path.join(root_loc, '.dev-env-context')
DEV_ENV_CONFIG_DIR: str = os.path.join(root_loc, 'dev-env-config')
DOCKER_COMPOSE_FILE_LIST: str = os.path.join(root_loc, '.docker-compose-file-list')

# Argument parser setup
parser = argparse.ArgumentParser(description='Usage: logic.py [options]')
parser.add_argument('-u', '--check-for-update', action='store_true')
parser.add_argument('-s', '--start-apps', action='store_true')
parser.add_argument('-S', '--stop-apps', action='store_true')
parser.add_argument('-c', '--prepare-config', action='store_true')
parser.add_argument('-a', '--update-apps', action='store_true')
parser.add_argument('-b', '--build-images', action='store_true')
parser.add_argument('-p', '--provision-commodities', action='store_true')
parser.add_argument('-C', '--prepare-compose', action='store_true')
parser.add_argument('-r', '--reset', action='store_true')
parser.add_argument('-n', '--nopull', action='store_true')
args = parser.parse_args()

os.environ['PYTHONUNBUFFERED'] = '1'

def fail_and_exit(new_project: bool) -> None:
    """
    Prints a failure message and exits the script.
    """
    print(colorize_red("Failed to clone or update the configuration repository."))
    sys.exit(1)

def check_healthy_output(output_lines: List[str]) -> bool:
    """
    Checks if any line in output_lines contains 'healthy'.
    """
    return any('healthy' in line for line in output_lines)

# Check for update logic
if args.check_for_update:
    this_version: str = '3.1.0'
    print(colorize_lightblue(f"This is a universal dev env (version {this_version})"))
    current_branch: str = subprocess.getoutput(f"git -C {root_loc} rev-parse --abbrev-ref HEAD").strip()
    if current_branch == 'master':
        self_update(root_loc, this_version)
    else:
        print(colorize_yellow('*******************************************************'))
        print(colorize_yellow('**                     WARNING!                      **'))
        print(colorize_yellow('**         YOU ARE NOT ON THE MASTER BRANCH          **'))
        print(colorize_yellow('**            UPDATE CHECKING IS DISABLED            **'))
        print(colorize_yellow('**          THERE MAY BE UNSTABLE FEATURES           **'))
        print(colorize_yellow("**   IF YOU DON\'T KNOW WHY YOU ARE ON THIS BRANCH    **"))
        print(colorize_yellow("**          THEN YOU PROBABLY SHOULDN\'T BE!          **"))
        print(colorize_yellow('*******************************************************'))
        print('')
        print(colorize_yellow('Continuing in 5 seconds (CTRL+C to quit)...'))
        time.sleep(5)

# Stop running apps
if args.stop_apps and os.path.exists(DOCKER_COMPOSE_FILE_LIST) and os.path.getsize(DOCKER_COMPOSE_FILE_LIST) != 0:
    print(colorize_lightblue('Stopping apps:'))
    run_command(f"{os.environ.get('DC_CMD')} stop")

# Prepare configuration repository
if args.prepare_config:
    if os.path.exists(DEV_ENV_CONTEXT_FILE):
        print()
        with open(DEV_ENV_CONTEXT_FILE) as f:
            print(colorize_green(f"This dev env has been provisioned to run for the repo: {f.read()}"))
    else:
        config_repo: str = input(colorize_yellow('Please enter the (Git) url of your dev env configuration repository: '))
        with open(DEV_ENV_CONTEXT_FILE, 'w') as f:
            f.write(config_repo)
    with open(DEV_ENV_CONTEXT_FILE) as f:
        config_repo = f.read().strip()
    if os.path.isdir(DEV_ENV_CONFIG_DIR):
        new_project: bool = False
        if config_repo == 'local':
            command_successful: int = 0
        else:
            command_successful = run_command(f"git -C {DEV_ENV_CONFIG_DIR} pull")
    else:
        new_project = True
        if '#' in config_repo:
            parsed_repo, ref = config_repo.split('#', 1)
        else:
            parsed_repo, ref = config_repo, ''
        if config_repo == 'local':
            print(colorize_lightblue('Initializing local config repository.'))
            os.makedirs(DEV_ENV_CONFIG_DIR, exist_ok=True)
            with open(os.path.join(DEV_ENV_CONFIG_DIR, 'configuration.yml'), 'w') as f:
                f.write("---\napplications: {}\n")
            print(colorize_green(f"You can start adding apps to {DEV_ENV_CONFIG_DIR}/configuration.yml"))
            sys.exit(1)
        else:
            command_successful = run_command(f"git clone {parsed_repo} {DEV_ENV_CONFIG_DIR}")
            if command_successful == 0 and ref:
                command_successful = run_command(f"git -C {DEV_ENV_CONFIG_DIR} checkout {ref}")
    if command_successful != 0:
        fail_and_exit(new_project)

# Update apps logic
if args.update_apps:
    print(colorize_lightblue('Updating apps:'))
    update_apps(root_loc)

# Reset environment logic
if args.reset:
    confirm: str = ''
    while not confirm.upper().startswith(('Y', 'N')):
        confirm = input(colorize_yellow('Would you like to KEEP your dev-env configuration files? (y/n) '))
    if confirm.upper().startswith('N'):
        if os.path.exists(DEV_ENV_CONTEXT_FILE):
            os.remove(DEV_ENV_CONTEXT_FILE)
        if os.path.isdir(DEV_ENV_CONFIG_DIR):
            import shutil
            shutil.rmtree(DEV_ENV_CONFIG_DIR)
    delete_files(root_loc)
    run_command(f"{os.environ.get('DC_CMD')} down --rmi all --volumes --remove-orphans")
    print(colorize_green('Environment reset'))

# Prepare docker-compose files
if args.prepare_compose:
    create_commodities_list(root_loc)
    prepare_compose(root_loc, DOCKER_COMPOSE_FILE_LIST)

# Build docker images
if args.build_images:
    if os.path.getsize(DOCKER_COMPOSE_FILE_LIST) == 0:
        print(colorize_red('Nothing to start!'))
        sys.exit(1)
    print(colorize_lightblue('Building images (might take a while)... (logging to logfiles/imagebuild.log)'))
    if run_command(f"{os.environ.get('DC_CMD')} build {'--pull' if not args.nopull else ''} > logfiles/imagebuild.log 2>&1") != 0:
        print(colorize_red('Something went wrong when building the images, check the log file. Here are the last 10 lines:'))
        with open(os.path.join(root_loc, 'logfiles/imagebuild.log')) as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line, end='')
        sys.exit(1)

# Provision commodities (containers)
if args.provision_commodities:
    existing_containers: List[str] = []
    run_command(f"{os.environ.get('DC_CMD')} ps --services", existing_containers)
    print(colorize_lightblue('Recreating containers... (logging to logfiles/containercreate.log)'))
    if run_command(f"{os.environ.get('DC_CMD')} up --remove-orphans --force-recreate --no-start > logfiles/containercreate.log 2>&1") != 0:
        print(colorize_red('Something went wrong when creating the containers, check the log file. Here are the last 10 lines:'))
        with open(os.path.join(root_loc, 'logfiles/containercreate.log')) as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line, end='')
        sys.exit(1)
    existing_containers2: List[str] = []
    run_command(f"{os.environ.get('DC_CMD')} ps --services", existing_containers2)
    new_containers: List[str] = list(set(existing_containers2) - set(existing_containers))
    provision_commodities(root_loc, new_containers)

# Start applications logic
if args.start_apps:
    if os.path.getsize(DOCKER_COMPOSE_FILE_LIST) == 0:
        print(colorize_red('Nothing to start!'))
        sys.exit(1)
    with open(os.path.join(root_loc, 'dev-env-config', 'configuration.yml')) as f:
        config: Dict[str, Any] = yaml.safe_load(f)
    services_to_start: List[str] = []
    run_command(f"{os.environ.get('DC_CMD')} config --services", services_to_start)
    expensive_todo: List[Dict[str, Any]] = []
    expensive_inprogress: List[Dict[str, Any]] = []
    print(colorize_lightblue('Checking application configurations...'))
    for appname, appconfig in config.get('applications', {}).items():
        config_options = appconfig.get('options', [])
        for option in config_options:
            service_name: str = option['compose-service-name']
            auto_start: bool = option.get('auto-start', True)
            if not auto_start:
                print(colorize_pink(f"Dev-env-config option found - service {service_name} autostart is FALSE"))
                if service_name in services_to_start:
                    services_to_start.remove(service_name)
        app_config_path: str = os.path.join(root_loc, 'apps', appname, 'configuration.yml')
        if not os.path.exists(app_config_path):
            continue
        with open(app_config_path) as depf:
            dependencies: Dict[str, Any] = yaml.safe_load(depf)
        if not dependencies or 'expensive_startup' not in dependencies:
            continue
        for service in dependencies['expensive_startup']:
            service_name = service['compose_service']
            if service_name not in services_to_start:
                continue
            print(colorize_pink(f"Found expensive to start service {service_name}"))
            expensive_todo.append(service)
            services_to_start.remove(service_name)
    up: int = run_command(f"{os.environ.get('DC_CMD')} up --no-deps --remove-orphans -d logstash", [])
    time.sleep(3)
    if up != 0:
        print(colorize_red('Something went wrong when initialising live container logging. Check the output above.'))
        sys.exit(1)
    if services_to_start:
        print(colorize_lightblue('Starting inexpensive services... (logging to logfiles/containerstart.log)'))
        up = run_command(f"{os.environ.get('DC_CMD')} up --no-deps --remove-orphans -d {' '.join(services_to_start)}")
        if up != 0:
            print(colorize_red('Something went wrong when starting the containers, check the log file. Here are the last 10 lines:'))
            with open(os.path.join(root_loc, 'logfiles/containerstart.log')) as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(line, end='')
            sys.exit(1)
    if len(expensive_todo) > 0:
        print(colorize_lightblue('Starting expensive services... (logging to logfiles/containerstart.log)'))
    expensive_failed: List[Dict[str, Any]] = []
    while len(expensive_todo) > 0 or len(expensive_inprogress) > 0:
        if len(expensive_inprogress) > 0:
            print()
            time.sleep(5)
        def healthy(service: Dict[str, Any]) -> bool:
            """
            Checks if a service is healthy using either Docker healthcheck or a custom command.
            """
            service['check_count'] = service.get('check_count', 0) + 1
            if service.get('healthcheck_cmd') == 'docker':
                print(colorize_lightblue(f"Checking if {service['compose_service']} is healthy (using Docker healthcheck) - Attempt {service['check_count']}"))
                output_lines: List[str] = []
                outcode: int = run_command(f"docker inspect --format=\"{{{{json .State.Health.Status}}}}\" {service['compose_service']}", output_lines)
                return outcode == 0 and check_healthy_output(output_lines)
            else:
                print(colorize_lightblue(f"Checking if {service['compose_service']} is healthy (using configuration.yml CMD) - Attempt {service['check_count']}"))
                return run_command(f"docker exec {service['compose_service']} {service['healthcheck_cmd']}") == 0
        # Remove healthy services from in-progress list
        expensive_inprogress[:] = [s for s in expensive_inprogress if not healthy(s)]
        for service in expensive_inprogress:
            output_lines: List[str] = []
            run_command(f"docker logs --tail 1 {service['compose_service']}", output_lines)
            print(colorize_yellow(f"Not yet (Last log line: {output_lines[0] if output_lines else ''})"))
            restart_count: int = 0
            output_lines = []
            run_command(f"docker inspect --format=\"{{{{json .RestartCount}}}}\" {service['compose_service']}", output_lines)
            for ln in output_lines:
                if ln.isdigit() and int(ln) > 0:
                    restart_count = int(ln)
            if restart_count > 0:
                print(colorize_pink(f"The container has exited (crashed?) and been restarted {restart_count} times (max 10 allowed)"))
            if restart_count > 9:
                print(colorize_red('The failure threshold has been reached. Skipping this container'))
                expensive_failed.append(service)
                run_command(f"{os.environ.get('DC_CMD')} stop {service['compose_service']}")
        while len(expensive_inprogress) < 3 and expensive_todo:
            service = expensive_todo.pop(0)
            dependency_healthy: bool = True
            wait_until_healthy_list = service.get('wait_until_healthy', [])
            if wait_until_healthy_list:
                print(colorize_lightblue(f"{service['compose_service']} has dependencies it would like to be healthy before starting:"))
            for dep in wait_until_healthy_list:
                if dep.get('healthcheck_cmd') == 'docker':
                    print(colorize_lightblue(f"Checking if {dep['compose_service']} is healthy (using Docker healthcheck)"))
                    output_lines: List[str] = []
                    outcode: int = run_command(f"docker inspect --format=\"{{{{json .State.Health.Status}}}}\" {dep['compose_service']}", output_lines)
                    dependency_healthy = outcode == 0 and check_healthy_output(output_lines)
                else:
                    print(colorize_lightblue(f"Checking if {dep['compose_service']} is healthy (using cmd in configuration.yml)"))
                    dependency_healthy = run_command(f"docker exec {dep['compose_service']} {dep['healthcheck_cmd']}") == 0
                if dependency_healthy:
                    print(colorize_green('It is!'))
                else:
                    print(colorize_yellow(f"{dep['compose_service']} is not healthy, so {service['compose_service']} will not be started yet"))
                    time.sleep(3)
                    break
            if dependency_healthy:
                run_command(f"{os.environ.get('DC_CMD')} up --no-deps --remove-orphans -d {service['compose_service']}")
                service['check_count'] = 0
                expensive_inprogress.append(service)
    provision_custom(root_loc)
    if expensive_failed:
        print(colorize_yellow('All done, but the following containers failed to start - check logs/log.txt for any useful error messages:'))
        for service in expensive_failed:
            print(colorize_yellow(f"  {service['compose_service']}"))
    else:
        print(colorize_green('Environment is ready for use'))
    post_up_message = config.get('post-up-message')
    if post_up_message:
        print()
        print(colorize_yellow('Special message from your dev-env-config:'))
        print(colorize_pink(post_up_message))
