import os
import yaml
from scripts.utilities import colorize_yellow, colorize_pink, colorize_lightblue
from scripts.provision_script.provision_postgres import provision_postgres
# from scripts.provision_hosts import provision_hosts
# from scripts.provision_nginx import provision_nginx
# from scripts.provision_elasticsearch5 import provision_elasticsearch5
# from scripts.provision_elasticsearch7 import provision_elasticsearch7
# from scripts.provision_wiremock import provision_wiremock
# from scripts.provision_localstack import provision_localstack

def create_commodities_list(root_loc: str) -> None:
    """
    Builds a list of all commodities required by all apps and writes it to .commodities.yml.
    """
    config_path = os.path.join(root_loc, 'dev-env-config', 'configuration.yml')
    if not os.path.exists(config_path):
        print(colorize_yellow('No dev-env-config found. Maybe this is a fresh box... '
                              'if so, you need to do "source run.sh up"'))
        exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    commodity_list, app_to_commodity_map = which_app_needs_what(root_loc, config)
    if 'logging' not in commodity_list:
        commodity_list.append('logging')
    commodity_file = get_commodity_file(root_loc)

    # Update the master list and add missing pairings
    commodity_file['commodities'] = commodity_list
    add_missing_pairings(app_to_commodity_map, commodity_file)

    # Write the commodity information to a file
    with open(os.path.join(root_loc, '.commodities.yml'), 'w') as f:
        yaml.dump(commodity_file, f)

def add_missing_pairings(app_to_commodity_map: dict, commodity_file: dict) -> None:
    """
    Ensures all app/commodity pairings are present in the commodity file.
    """
    cf_app_list = commodity_file['applications']
    for app_name, app_commodity_list in app_to_commodity_map.items():
        if app_name not in cf_app_list:
            cf_app_list[app_name] = {}
        for current_commodity in app_commodity_list:
            if current_commodity not in cf_app_list[app_name]:
                cf_app_list[app_name][current_commodity] = False
                print(colorize_pink(f"Found a new commodity dependency from {app_name} to {current_commodity}"))

def which_app_needs_what(root_loc: str, config: dict) -> tuple[list, dict]:
    """
    Returns a tuple: (list of all commodities, mapping of app to its commodities).
    """
    app_to_commodity_map = {}
    commodity_list = []
    if config.get('applications'):
        for appname in config['applications']:
            app_config_path = os.path.join(root_loc, 'apps', appname, 'configuration.yml')
            if not os.path.exists(app_config_path):
                continue
            with open(app_config_path) as f:
                dependencies = yaml.safe_load(f)
            if not dependencies or 'commodities' not in dependencies:
                continue
            for appcommodity in dependencies['commodities']:
                commodity_list.append(appcommodity)
                app_to_commodity_map.setdefault(appname, []).append(appcommodity)
    return list(set(commodity_list)), app_to_commodity_map

def get_commodity_file(root_loc: str) -> dict:
    """
    Loads or creates the .commodities.yml file structure.
    """
    path = os.path.join(root_loc, '.commodities.yml')
    if os.path.exists(path):
        with open(path) as f:
            commodity_file = yaml.safe_load(f)
    else:
        print(colorize_lightblue('Did not find any .commodities file. Creating a new one.'))
        commodity_file = {
            'version': '2',
            'commodities': [],
            'applications': {}
        }
    return commodity_file

def commodity_provisioned(root_loc: str, app_name: str, commodity: str) -> bool:
    """
    Returns True if the commodity is provisioned for the app.
    """
    with open(os.path.join(root_loc, '.commodities.yml')) as f:
        commodity_file = yaml.safe_load(f)
    return commodity_file['applications'][app_name][commodity]

def set_commodity_provision_status(root_loc: str, app_name: str, commodity: str, status: bool) -> None:
    """
    Sets the provision status for a commodity for a given app.
    """
    path = os.path.join(root_loc, '.commodities.yml')
    with open(path) as f:
        commodity_file = yaml.safe_load(f)
    commodity_file['applications'][app_name][commodity] = status
    with open(path, 'w') as f:
        yaml.dump(commodity_file, f)

def commodity_required(root_loc: str, appname: str, commodity: str) -> bool:
    """
    Returns True if the app requires the commodity.
    """
    app_config_path = os.path.join(root_loc, 'apps', appname, 'configuration.yml')
    if not os.path.exists(app_config_path):
        return False
    with open(app_config_path) as f:
        dependencies = yaml.safe_load(f)
    if not dependencies:
        return False
    return 'commodities' in dependencies and commodity in dependencies['commodities']

def commodity(root_loc: str, commodity_name: str) -> bool:
    """
    Returns True if the given name is a commodity in the environment.
    """
    path = os.path.join(root_loc, '.commodities.yml')
    if not os.path.exists(path):
        return False
    with open(path) as f:
        commodities = yaml.safe_load(f)
    return commodity_name in commodities.get('commodities', [])

def provision_commodities(root_loc: str, new_containers: list) -> None:
    """
    Provisions all required commodities for the environment.
    """
    print(colorize_lightblue('Provisioning commodities...'))
    for postgres_version in ['13', '17']:
        provision_postgres(root_loc, new_containers, postgres_version)
    # provision_nginx(root_loc, new_containers)
    # provision_elasticsearch5(root_loc)
    # provision_elasticsearch7(root_loc)
    # provision_wiremock(root_loc, new_containers)
    # provision_hosts(root_loc)
    # provision_localstack(root_loc, new_containers)

def container_to_commodity(container_name: str) -> str:
    """
    Maps a container name to its commodity name.
    """
    return 'auth' if container_name == 'openldap' else container_name

# def show_commodity_messages(root_loc):
#     show_postgres_warnings(root_loc)
