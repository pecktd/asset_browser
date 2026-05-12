from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WorkFile:
    proj: str
    name: str
    var: str
    step: str
    user: str
    task: str
    ver: int
    sub_ver: int

    @classmethod
    def from_file_path(cls, file_path: Path) -> Optional["WorkFile"]:
        """Parses a structured filename into a WorkFile instance.

        Expected format: proj_name_var_step_user_task.v###_subver
        Example: PRJ_seq01_char_anim_john_track.v012_01.ma
        """
        stem = file_path.stem
        if ".v" not in stem:
            return None

        parts = stem.split("_")
        if len(parts) != 7:
            return None

        proj, name, var, step, user, task_ver, sub_ver = parts

        try:
            task, ver_str = task_ver.split(".v")
            ver = int(ver_str)
            sub_ver = int(sub_ver)
        except ValueError:
            return None

        return cls(proj, name, var, step, user, task, ver, sub_ver)
