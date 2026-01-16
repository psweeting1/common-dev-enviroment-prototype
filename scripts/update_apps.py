import os
import time
import threading
import queue
import yaml
from typing import Dict, Any, List
from scripts.utilities import (
    colorize_lightblue,
    colorize_red,
    colorize_yellow,
    colorize_green,
    run_command)

THREAD_COUNT = 3

def update_apps(root_loc: str) -> None:
    """
    Updates or clones all applications defined in configuration.yml using threads.
    """
    config_path = os.path.join(root_loc, 'dev-env-config', 'configuration.yml')
    with open(config_path) as f:
        config: Dict[str, Any] = yaml.safe_load(f)
    if not config or 'applications' not in config:
        return

    output_mutex = threading.Lock()
    q = queue.Queue()
    threads = []

    def worker():
        while True:
            queue_item = q.get()
            if queue_item is None:
                break
            appname, appconfig = queue_item
            output_lines = [colorize_green(f"================== {appname} ==================")]
            output_lines += update_or_clone(appconfig, root_loc, appname)
            with output_mutex:
                for line in output_lines:
                    print(line)
            q.task_done()

    for _ in range(THREAD_COUNT):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    populate_queue(config, q)
    q.join()
    for _ in range(THREAD_COUNT):
        q.put(None)
    for t in threads:
        t.join()

def populate_queue(config: Dict[str, Any], q: queue.Queue) -> None:
    for appname, appconfig in config['applications'].items():
        q.put((appname, appconfig))

def required_ref(appconfig: Dict[str, Any]) -> str:
    return appconfig.get('ref', appconfig.get('branch'))

def update_or_clone(appconfig: Dict[str, Any], root_loc: str, appname: str) -> List[str]:
    if appconfig.get('repo') == 'none':
        return [colorize_lightblue('This app is local-only; skipping')]
    app_path = os.path.join(root_loc, 'apps', appname)
    if os.path.isdir(app_path):
        return update_app(appconfig, root_loc, appname)
    else:
        return clone_app(appconfig, root_loc, appname)

def current_branch(root_loc: str, appname: str) -> str:
    app_path = os.path.join(root_loc, 'apps', appname)
    result = os.popen(f"git -C {app_path} rev-parse --abbrev-ref HEAD").read().strip()
    if result == 'HEAD':
        return 'detached'
    return result

def merge(root_loc: str, appname: str) -> List[str]:
    if current_branch(root_loc, appname) == 'detached':
        return []
    output_lines: List[str] = []
    app_path = os.path.join(root_loc, 'apps', appname)
    if run_command(f"git -C {app_path} merge --ff-only", output_lines) != 0:
        output_lines.append(colorize_yellow(
            "The local branch couldn't be fast forwarded (a merge is probably required); skipping update"
        ))
    return output_lines

def update_app(appconfig: Dict[str, Any], root_loc: str, appname: str) -> List[str]:
    output_lines: List[str] = []
    branch = current_branch(root_loc, appname)
    if branch == 'detached':
        output_lines.append(colorize_yellow('Detached head detected; skipping update'))
        return output_lines
    required_reference = required_ref(appconfig)
    if branch != required_reference:
        output_lines.append(colorize_yellow(
            f"The current branch ({branch}) differs from the devenv configuration ({required_reference}); skipping update"
        ))
        return output_lines
    app_path = os.path.join(root_loc, 'apps', appname)
    if run_command(f"git -C {app_path} fetch origin", output_lines) == 0:
        output_lines += merge(root_loc, appname)
        return output_lines
    output_lines.append(colorize_red(f"Error while updating {appname}"))
    output_lines.append(colorize_yellow('Continuing in 3 seconds...'))
    time.sleep(3)
    return output_lines

def clone_app(appconfig: Dict[str, Any], root_loc: str, appname: str) -> List[str]:
    output_lines: List[str] = []
    output_lines.append(colorize_lightblue(f"{appname} does not yet exist; cloning"))
    repo = appconfig['repo']
    app_path = os.path.join(root_loc, 'apps', appname)
    if run_command(f"git clone {repo} {app_path}", output_lines) != 0:
        output_lines.append(colorize_red(f"Error while cloning {appname}"))
        output_lines.append(colorize_yellow('Continuing in 3 seconds...'))
        time.sleep(3)
    branch = current_branch(root_loc, appname)
    required_reference = required_ref(appconfig)
    if branch != required_reference:
        run_command(f"git -C {app_path} checkout {required_reference}", output_lines)
    return output_lines

if __name__ == "__main__":
    update_apps(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
