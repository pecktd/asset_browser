import getpass
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import maya.cmds as mc

from asset_browser.models import WorkFile

_SESSION_OPTION_VAR = "assetBrowserLastSession"
_PREFS_OPTION_VAR = "assetBrowserPrefs"


def get_maya_scene_path() -> Path:
    """Returns the current Maya scene file path as a Path object."""
    scene_path_str = mc.file(q=True, sn=True)
    if not scene_path_str:
        location_list = mc.file(q=True, l=True)
        if location_list:
            scene_path_str = location_list[0]

    return Path(scene_path_str)


def group_files(folder_path: Path) -> dict[str, dict[str, str] | list[str]]:
    """Groups work files in a folder by `variant:task`, then by `ver:sub_ver:user`.

    Files that fail to parse are collected under the "error" key.
    """
    result: dict[str, dict[str, str] | list[str]] = {"error": []}
    files = [f for f in folder_path.iterdir() if f.is_file() and f.suffix in (".ma", ".mb")]

    for file in files:
        work_file = WorkFile.from_file_path(file)

        if not work_file:
            result["error"].append(file.name)
            continue

        var_task = f"{work_file.var}:{work_file.task}"
        ver_user = f"{work_file.ver:03d}:{work_file.sub_ver:02d}:{work_file.user}"

        if var_task not in result:
            result[var_task] = {}

        result[var_task][ver_user] = file.name

    return result


def current_user() -> str:
    """Returns the current OS user, cross-platform."""
    return getpass.getuser()


def save_session_state(state: dict) -> None:
    """Persist the browser's last column selection across Maya sessions."""
    mc.optionVar(sv=(_SESSION_OPTION_VAR, json.dumps(state)))


def load_session_state() -> dict:
    """Return the browser's last persisted column selection, or an empty dict."""
    if not mc.optionVar(exists=_SESSION_OPTION_VAR):
        return {}
    try:
        return json.loads(mc.optionVar(q=_SESSION_OPTION_VAR))
    except (ValueError, TypeError):
        return {}


def save_prefs(prefs: dict) -> None:
    """Persist the browser's user preferences across Maya sessions."""
    mc.optionVar(sv=(_PREFS_OPTION_VAR, json.dumps(prefs)))


def load_prefs() -> dict:
    """Return the browser's persisted user preferences, or an empty dict."""
    if not mc.optionVar(exists=_PREFS_OPTION_VAR):
        return {}
    try:
        return json.loads(mc.optionVar(q=_PREFS_OPTION_VAR))
    except (ValueError, TypeError):
        return {}


def copy_folder(src: Path, dst: Path) -> None:
    """Recursively copy the folder ``src`` to a new folder ``dst`` (which must not yet exist)."""
    shutil.copytree(str(src), str(dst))


def open_folder(path: Path) -> None:
    """Open a folder in the OS file manager, cross-platform."""
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
