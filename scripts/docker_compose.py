import os
import sys
import time
import yaml
import glob
from typing import Dict, List, Optional, Any
from scripts.utilities import colorize_yellow, colorize_red, colorize_lightblue

def prepare_compose(root_loc: str, file_list_loc: str) -> None:
    """
    Prepares the list of Docker Compose fragments for the environment and writes them to a file.
    Handles app fragments and commodity fragments, and writes the list using the correct separator for the OS.
    """
    commodity_list: List[str] = []
    compose_variants = find_active_variants(root_loc)

    # Ensure the first fragment is always the root fragment for consistent path resolution
    commodity_list.append(os.path.join(root_loc, 'apps', 'root-compose-fragment.yml'))

    # Add app compose fragments
    get_apps(root_loc, commodity_list, compose_variants)

    # Add commodity fragments if present
    commodities_path = os.path.join(root_loc, '.commodities.yml')
    if os.path.exists(commodities_path):
        with open(commodities_path) as f:
            commodities = yaml.safe_load(f)
        if commodities and 'commodities' in commodities:
            for commodity_info in commodities['commodities']:
                commodity_list.append(
                    os.path.join(root_loc, 'scripts', 'docker', commodity_info, 'compose-fragment.yml')
                )

    # Write the compose file list to disk, using the correct separator for the platform
    sep = ';' if sys.platform.startswith('win') else ':'
    with open(file_list_loc, 'w') as f:
        f.write(sep.join(commodity_list))

def get_apps(root_loc: str, commodity_list: List[str], compose_variants: Dict[str, str]) -> None:
    """
    Adds app-specific compose fragments to the commodity_list based on the configuration and active variants.
    """
    config_path = os.path.join(root_loc, 'dev-env-config', 'configuration.yml')
    if not os.path.exists(config_path):
        print(colorize_yellow('No dev-env-config found. Maybe this is a fresh box... '
                              'if so, you need to do "source run.sh up"'))
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not config or 'applications' not in config:
        return

    for appname in config['applications']:
        app_fragments_dir = os.path.join(root_loc, 'apps', appname, 'fragments')
        if appname in compose_variants:
            variant_fragment_filename = fragment_filename(compose_variants[appname])
            variant_path = os.path.join(app_fragments_dir, variant_fragment_filename)
            if os.path.exists(variant_path):
                commodity_list.append(variant_path)
        else:
            default_fragment = os.path.join(app_fragments_dir, 'compose-fragment.yml')
            if os.path.exists(default_fragment):
                commodity_list.append(default_fragment)

def find_active_variants(root_loc: str) -> Dict[str, str]:
    """
    Determines which compose variant fragment to use for each app, based on configuration and available files.
    Returns a dictionary mapping app names to their selected variant fragment name.
    """
    config_path = os.path.join(root_loc, 'dev-env-config', 'configuration.yml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if not config or 'applications' not in config:
        return {}

    compose_variants: Dict[str, str] = {}

    for appname in config['applications']:
        found_valid_fragment = False
        fragments_glob = os.path.join(root_loc, 'apps', appname, 'fragments', '*compose-fragment*.yml')
        compose_fragments = glob.glob(fragments_glob)

        for fragment in compose_fragments:
            basename = os.path.basename(fragment)
            if basename == 'compose-fragment.yml':
                found_valid_fragment = True
            elif basename.startswith('compose-fragment.') and basename.endswith('.yml'):
                variant_fragment_filename = validate_variant_fragment_filename(config, appname, basename)
                if variant_fragment_filename is not None:
                    compose_variants[appname] = variant_fragment_filename
                    print(colorize_lightblue(f'{appname}: Selected compose variant "{compose_variants[appname]}"'))
                    found_valid_fragment = True
            else:
                print(colorize_yellow(f"Unsupported fragment in {appname}: {basename}"))

        if not found_valid_fragment:
            print(colorize_red(f"Cannot find a valid compose fragment file in {appname}; no container will be created"))
            print(colorize_yellow('Continuing in 10 seconds...'))
            time.sleep(10)

    return compose_variants

def validate_variant_fragment_filename(config: Dict[str, Any], appname: str, basename: str) -> Optional[str]:
    """
    Validates if the given variant fragment filename matches the app's configured variant.
    Returns the variant name if valid, otherwise None.
    """
    import re
    match = re.match(r'compose-fragment\.(.*?)\.yml', basename)
    if match:
        variant_fragment_filename = match.group(1)
        app_config = config['applications'].get(appname, {})
        if app_config.get('variant') == variant_fragment_filename:
            return variant_fragment_filename
    return None

def highest_version(version_a: str, version_b: str) -> Optional[str]:
    """
    Returns the highest docker-compose version among the two provided.
    """
    if version_a == 'unversioned' or version_b == 'unversioned':
        return 'unversioned'
    if version_a == '3.7' or version_b == '3.7':
        return '3.7'
    if version_a == '2' or version_b == '2':
        return '2'
    return None

def fragment_filename(compose_variant_name: Optional[str]) -> str:
    """
    Returns the filename for a compose fragment, given a variant name (or default if None).
    """
    if compose_variant_name is None:
        return 'compose-fragment.yml'
    return f'compose-fragment.{compose_variant_name}.yml'
