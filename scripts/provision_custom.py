import os
import yaml
from scripts.utilities import colorize_green, colorize_pink, colorize_yellow, run_command

def create_custom_provision(root_loc: str) -> None:
    """
    Creates the .custom_provision.yml file if it does not exist.
    """
    custom_path = os.path.join(root_loc, '.custom_provision.yml')
    if os.path.exists(custom_path):
        return
    print(colorize_green("Did not find a .custom_provision file. I'll create a new one."))
    custom_file = {
        'version': '1',
        'applications': []
    }
    with open(custom_path, 'w') as f:
        yaml.dump(custom_file, f)

def custom_provisioned(root_loc: str, app_name: str) -> bool:
    """
    Returns True if the app has already been custom provisioned.
    """
    custom_path = os.path.join(root_loc, '.custom_provision.yml')
    if not os.path.exists(custom_path):
        return False
    with open(custom_path) as f:
        custom_file = yaml.safe_load(f)
    return app_name in custom_file.get('applications', [])

def set_custom_provisioned(root_loc: str, app_name: str) -> None:
    """
    Marks the app as custom provisioned in .custom_provision.yml.
    """
    create_custom_provision(root_loc)
    custom_path = os.path.join(root_loc, '.custom_provision.yml')
    with open(custom_path) as f:
        custom_file = yaml.safe_load(f)
    custom_file['applications'].append(app_name)
    with open(custom_path, 'w') as f:
        yaml.dump(custom_file, f)

def provision_custom(root_loc: str) -> None:
    """
    Runs custom provision scripts for all apps as defined in configuration.yml.
    """
    config_path = os.path.join(root_loc, 'dev-env-config', 'configuration.yml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not config or 'applications' not in config:
        return
    for appname in config['applications']:
        run_onetime_custom_provision(root_loc, appname)
        run_always_custom_provision(root_loc, appname)

def run_onetime_custom_provision(root_loc: str, appname: str) -> None:
    """
    Runs the once-only custom provision script for an app if it exists and hasn't been run.
    """
    script_path = os.path.join(root_loc, 'apps', appname, 'fragments', 'custom-provision.sh')
    if not os.path.exists(script_path):
        return
    print(colorize_pink(f"Found a custom provision script (once-only) in {appname}"))
    if custom_provisioned(root_loc, appname):
        print(colorize_yellow(f"Custom provision script has already been run for {appname}, skipping"))
    else:
        run_command(f"sh {script_path}")
        set_custom_provisioned(root_loc, appname)

def run_always_custom_provision(root_loc: str, appname: str) -> None:
    """
    Runs the always-run custom provision script for an app if it exists.
    """
    script_path = os.path.join(root_loc, 'apps', appname, 'fragments', 'custom-provision-always.sh')
    if not os.path.exists(script_path):
        return
    print(colorize_pink(f"Found a custom provision script (always) in {appname}"))
    run_command(f"sh {script_path}")
