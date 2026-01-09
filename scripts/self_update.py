import os
import sys
import time
import requests
import json
from datetime import datetime, date
from typing import Optional, List, Any
from scripts.utilities import *

def self_update(root_loc: str, this_version: str) -> None:
    """
    Checks for a newer version of the dev environment and prompts the user to update if available.
    """
    try:
        latest_version = retrieve_version()
        if latest_version and version_greater(latest_version[0], this_version):
            prompt_and_update(root_loc, latest_version)
        elif latest_version:
            print(colorize_green('This is the latest version.'))
    except Exception as e:
        print(e)
        print(colorize_yellow(
            "There was an error retrieving the current dev-env version. I'll just get on with starting the machine."
        ))
        print(colorize_yellow('Continuing in 5 seconds...'))
        time.sleep(5)

def prompt_and_update(root_loc: str, latest_version: List[str]) -> None:
    """
    Prompts the user to update if a new version is available.
    """
    print(colorize_yellow(f"A new version is available - v{latest_version[0]}"))
    print(colorize_yellow('Changes:'))
    print(colorize_yellow(latest_version[1]))
    print()
    ask_update = not refused_today(root_loc)
    if ask_update:
        confirm_and_update(root_loc)

def refused_today(root_loc: str) -> bool:
    """
    Checks if the user has already refused to update today.
    """
    update_check_file = os.path.join(root_loc, '.update-check-context')
    if not os.path.exists(update_check_file):
        return False
    with open(update_check_file) as f:
        parsed_date = datetime.strptime(f.read().strip(), '%Y-%m-%d').date()
    if date.today() == parsed_date:
        print(colorize_yellow(
            "You've already said you don't want to update today, so I won't ask again. To update manually, run git pull."
        ))
        print()
        return True
    else:
        os.remove(update_check_file)
        return False

def confirm_and_update(root_loc: str) -> None:
    """
    Asks the user to confirm the update and acts accordingly.
    """
    confirm = ''
    while not confirm.upper().startswith(('Y', 'N')):
        confirm = input(colorize_yellow('Would you like to update now? (y/n) '))
    if confirm.upper().startswith('Y'):
        run_update(root_loc)
    else:
        print()
        print(colorize_yellow(
            "Okay. I'll ask again tomorrow. If you want to update in the meantime, simply run git pull yourself."
        ))
        print(colorize_yellow('Continuing in 5 seconds...'))
        print()
        with open(os.path.join(root_loc, '.update-check-context'), 'w') as f:
            f.write(date.today().strftime('%Y-%m-%d'))
        time.sleep(5)

def run_update(root_loc: str) -> None:
    """
    Runs the update command and handles the result.
    """
    if run_command(f"git -C {root_loc} pull") != 0:
        print(colorize_yellow(
            "There was an error retrieving the new dev-env. Sorry. I'll just get on with starting the machine."
        ))
        print(colorize_yellow('Continuing in 5 seconds...'))
        time.sleep(5)
    else:
        print(colorize_yellow('Update successful.'))
        print(colorize_yellow('Please rerun your command (source run.sh up)'))
        sys.exit(1)

def retrieve_version() -> Optional[List[Any]]:
    """
    Retrieves the latest version information from GitHub releases.
    Returns a list [version, changelog] or None on error.
    """
    url = 'https://api.github.com/repos/LandRegistry/common-dev-env/releases/latest'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            tag = result['tag_name'].lstrip('v')
            body = result.get('body', '')
            return [tag, body]
        else:
            print(colorize_yellow(
                f"There was an error retrieving the current dev-env version (HTTP code {response.status_code}). I'll just get on with starting the machine."
            ))
            print(colorize_yellow('Continuing in 5 seconds...'))
            time.sleep(5)
            return None
    except Exception as e:
        print(colorize_yellow(f"Error retrieving version: {e}"))
        print(colorize_yellow('Continuing in 5 seconds...'))
        time.sleep(5)
        return None

def version_greater(v1: str, v2: str) -> bool:
    """
    Compares two version strings and returns True if v1 > v2.
    """
    from packaging.version import Version
    return Version(v1) > Version(v2)
