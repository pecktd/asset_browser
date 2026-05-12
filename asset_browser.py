import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from qtpy import QtWidgets, QtCore, QtGui

import maya.cmds as mc

from pkrig3_ui import run_workspace


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

        Args:
            file_path (Path): Path to the work file.

        Returns:
            Optional[WorkFile]: Parsed WorkFile instance, or None if format is invalid.
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


def get_maya_scene_path() -> Path:
    """
    Returns the current Maya scene file path as a Path object.

    Returns:
        Path: The resolved path to the current Maya scene file.
    """
    scene_path_str = mc.file(q=True, sn=True)
    if not scene_path_str:
        location_list = mc.file(q=True, l=True)
        if location_list:
            scene_path_str = location_list[0]

    return Path(scene_path_str)


def group_files(folder_path: Path) -> dict[str, dict[str, str] | list[str]]:
    """Groups work files in a folder by variant and task, then by version, subversion, and user.

    This function scans all files in the given folder and attempts to parse each filename into a
    structured `WorkFile`. Valid files are grouped into a nested dictionary using the following keys:

    - Outer key: `"variant:task"` (e.g., `"default:all"`)
    - Inner key: `"ver:sub_ver:user"` (e.g., `"001:01:peck"`)
    - Value: The file name

    Files that fail to parse are collected under the `"error"` key.

    Example output:
        {
            "default:all": {
                "001:01:peck": "mkg_fakeAdam_default_rig_peck_all.v001_01",
                "001:01:khim": "mkg_fakeAdam_default_rig_khim_all.v001_01"
            },
            "typeA:all": {
                "001:01:peck": "mkg_fakeAdam_typeA_rig_peck_all.v001_01"
            },
            "error": [
                "test",
                "temp"
            ]
        }

    Args:
        folder_path (Path): Path to the folder containing work files.

    Returns:
        dict[str, dict[str, str] | list[str]]: A dictionary of grouped file names and errors.
    """
    result: dict[str, dict[str, str] | list[str]] = {"error": []}
    files = [f for f in folder_path.iterdir() if f.is_file() and (f.suffix in (".ma", ".mb"))]

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


class LineEditWidget(QtWidgets.QWidget):
    def __init__(self, name):
        super(LineEditWidget, self).__init__(None)

        self.name = name

        self.main_hl = QtWidgets.QHBoxLayout()
        self.main_hl.setContentsMargins(0, 0, 0, 0)

        self.label = QtWidgets.QLabel()
        self.label.setText("{}:".format(self.name))

        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setAlignment(QtCore.Qt.AlignRight)

        self.end_line = QtWidgets.QFrame()
        self.end_line.setFrameShape(QtWidgets.QFrame.VLine)
        self.end_line.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.main_hl.addWidget(self.label, 0)
        self.main_hl.addWidget(self.line_edit, 1)
        self.main_hl.addWidget(self.end_line, 2)

        self.setLayout(self.main_hl)

    def text(self):
        return self.line_edit.text()


class SpinBoxWidget(QtWidgets.QWidget):
    def __init__(self, name):
        super(SpinBoxWidget, self).__init__(None)

        self.name = name

        self.main_hl = QtWidgets.QHBoxLayout()
        self.main_hl.setContentsMargins(0, 0, 0, 0)

        self.label = QtWidgets.QLabel()
        self.label.setText("{}:".format(self.name))

        self.val_sb = QtWidgets.QSpinBox()
        self.val_sb.setAlignment(QtCore.Qt.AlignRight)
        self.val_sb.setMinimumWidth(50)

        self.end_line = QtWidgets.QFrame()
        self.end_line.setFrameShape(QtWidgets.QFrame.VLine)
        self.end_line.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.main_hl.addWidget(self.label, 0)
        self.main_hl.addWidget(self.val_sb, 1)
        self.main_hl.addWidget(self.end_line, 2)

        self.setLayout(self.main_hl)

    def value(self):
        return self.val_sb.value()


class ListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, name: str, path: str):
        super(ListWidgetItem, self).__init__(None)

        self.name = name
        self.path = path
        self.setText(name)


class ListItemWidget(QtWidgets.QWidget):
    def __init__(self, name: str, path: Path):
        super(ListItemWidget, self).__init__(None)

        self.name = name
        self.path = path

        self.main_vl = QtWidgets.QVBoxLayout()
        self.main_vl.setContentsMargins(0, 0, 0, 0)

        self.label = QtWidgets.QLabel()
        self.label.setText(self.name)
        self.label.setAlignment(QtCore.Qt.AlignHCenter)

        self.list = QtWidgets.QListWidget()

        self.main_vl.addWidget(self.label)
        self.main_vl.addWidget(self.list)
        self.setLayout(self.main_vl)

    def add_item(self, name: str, path: str):
        self.list.addItem(ListWidgetItem(name, path))

    def add_items(self, names: list[str]):
        for name in names:
            self.add_item(name, self.path)

    def add_separator(self):
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        separator_item = QtWidgets.QListWidgetItem()
        separator_item.setSizeHint(separator.sizeHint())
        separator_item.setFlags(QtCore.Qt.NoItemFlags)
        self.list.addItem(separator_item)
        self.list.setItemWidget(separator_item, separator)

    def pop_folders(self):

        self.list.clear()
        folder_names = [
            f.stem for f in self.path.iterdir() if f.is_dir() and not f.name.startswith(".")
        ]
        if folder_names:
            self.add_items(sorted(folder_names))

    def pop_files(self):
        self.list.clear()
        files = group_files(self.path)

        if not files:
            return False

        for var_task in sorted(files):
            if var_task == "error":
                continue

            for ver_user in sorted(files[var_task]):
                self.add_item(files[var_task][ver_user], self.path)

            self.add_separator()

        if files["error"]:
            self.add_items(sorted(files["error"]))
            self.add_separator()

    def get_selected(self) -> str:
        if self.list.currentItem():
            return self.list.currentItem().name
        else:
            return None

    def select_by_name(self, name: str):
        for i in range(self.list.count()):
            current_item = self.list.item(i)

            if ListWidgetItem not in type(current_item).mro():
                continue

            current_item: ListWidgetItem
            if current_item.name == str(name):
                self.list.setCurrentRow(i)


class ListItemWithFilterWidget(ListItemWidget):

    def __init__(self, name: str, path: str):
        super().__init__(name, path)
        self.filter_le = QtWidgets.QLineEdit()
        self.filter_le.setAlignment(QtCore.Qt.AlignRight)
        self.filter_le.setPlaceholderText("Filter...")
        self.main_vl.addWidget(self.filter_le)

        self.filter_le.textChanged.connect(self._filter)

    def _filter(self):

        current_text = self.filter_le.text()

        for i in range(self.list.count()):

            current_item: ListWidgetItem = self.list.item(i)

            if not current_text:
                current_item.setHidden(False)
                continue

            if ListWidgetItem not in type(current_item).mro():
                current_item.setHidden(True)
            else:
                if current_text not in current_item.name:
                    current_item.setHidden(True)


class AssetBrowser(QtWidgets.QMainWindow):
    window = None

    def __init__(self, parent):
        super().__init__(parent)

        self.selected_path: Path

        self.setObjectName("AssetBrowser")
        self.setWindowTitle("AssetBrowser")
        self.resize(1100, 700)

        # Central Widgets
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.central_vl = QtWidgets.QVBoxLayout(self.central_widget)
        self.central_vl.setSpacing(0)
        self.central_vl.setContentsMargins(5, 5, 5, 5)

        # Main Layout
        self.main_vl = QtWidgets.QVBoxLayout()
        self.main_vl.setSpacing(0)
        self.central_vl.addLayout(self.main_vl)

        # Menu Bar
        self.menu_bar = QtWidgets.QMenuBar(self)
        self.menu_bar.setGeometry(QtCore.QRect(0, 0, 620, 21))
        self.setMenuBar(self.menu_bar)

        self.menu_line = QtWidgets.QFrame(self.central_widget)
        self.menu_line.setFrameShape(QtWidgets.QFrame.HLine)
        self.menu_line.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.main_vl.addWidget(self.menu_line)

        self.main_hl = QtWidgets.QHBoxLayout()
        self.main_hl.setSpacing(0)
        self.main_vl.addLayout(self.main_hl)

        self.tools_hl = QtWidgets.QHBoxLayout()
        self.tools_hl.setSpacing(0)
        self.main_vl.addLayout(self.tools_hl)

        # File System Widgets
        self.project_vl = QtWidgets.QVBoxLayout()
        self.project_vl.setSpacing(0)
        self.main_hl.addLayout(self.project_vl)

        self.project_widget = ListItemWithFilterWidget("Projects", Path(os.getenv("PROJ_ROOT")))
        self.project_vl.addWidget(self.project_widget)

        self.asset_vl = QtWidgets.QVBoxLayout()
        self.asset_vl.setSpacing(0)
        self.main_hl.addLayout(self.asset_vl)

        self.asset_widget = ListItemWithFilterWidget("Assets", "")
        self.asset_vl.addWidget(self.asset_widget)

        self.step_widget = ListItemWidget("Steps", "")
        self.asset_vl.addWidget(self.step_widget)

        self.asset_vl.setStretch(0, 3)
        self.asset_vl.setStretch(1, 1)

        self.file_vl = QtWidgets.QVBoxLayout()
        self.file_vl.setSpacing(0)
        self.main_hl.addLayout(self.file_vl)

        self.file_widget = ListItemWithFilterWidget("Files", "")
        self.file_vl.addWidget(self.file_widget)

        self.rigging_component_vl = QtWidgets.QVBoxLayout()
        self.rigging_component_vl.setSpacing(0)
        self.main_hl.addLayout(self.rigging_component_vl)

        self.variant_widget = ListItemWidget("Variants", "")
        self.rigging_component_vl.addWidget(self.variant_widget)

        self.workspace_widget = ListItemWidget("Workspaces", "")
        self.rigging_component_vl.addWidget(self.workspace_widget)

        self.launch_workspace_but = QtWidgets.QPushButton("Open Workspace")
        self.rigging_component_vl.addWidget(self.launch_workspace_but)

        self.rigging_compoenent_widget = ListItemWidget("Rigging Components", "")
        self.rigging_component_vl.addWidget(self.rigging_compoenent_widget)

        self.rigging_component_vl.setStretch(0, 1)
        self.rigging_component_vl.setStretch(1, 2)
        self.rigging_component_vl.setStretch(2, 1)
        self.rigging_component_vl.setStretch(3, 3)

        self.main_hl.setStretch(0, 1)
        self.main_hl.setStretch(1, 2)
        self.main_hl.setStretch(2, 5)
        self.main_hl.setStretch(3, 1)

        # File Save/Load Widgets
        self.variant_le = LineEditWidget("Variant")
        self.tools_hl.addWidget(self.variant_le)

        self.user_le = LineEditWidget("User")
        self.tools_hl.addWidget(self.user_le)

        self.task_le = LineEditWidget("Task")
        self.tools_hl.addWidget(self.task_le)

        self.main_ver_sb = SpinBoxWidget("Main Version")
        self.main_ver_sb.val_sb.setMinimum(1)
        self.main_ver_sb.val_sb.setMaximum(999)
        self.tools_hl.addWidget(self.main_ver_sb)

        self.sub_ver_sb = SpinBoxWidget("Sub Version")
        self.sub_ver_sb.val_sb.setMinimum(1)
        self.sub_ver_sb.val_sb.setMaximum(99)
        self.tools_hl.addWidget(self.sub_ver_sb)

        self.save_but = QtWidgets.QPushButton("Save")
        self.tools_hl.addWidget(self.save_but)

        for i in range(6):
            self.tools_hl.setStretch(i, 1)
        self.tools_hl.setStretch(6, 2)

        # Connections
        self.project_widget.list.itemClicked.connect(self._project_clicked)
        self.project_widget.list.itemSelectionChanged.connect(self._project_clicked)

        self.asset_widget.list.itemClicked.connect(self._asset_clicked)
        self.asset_widget.list.itemSelectionChanged.connect(self._asset_clicked)

        self.step_widget.list.itemClicked.connect(self._step_clicked)
        self.step_widget.list.itemSelectionChanged.connect(self._step_clicked)

        self.variant_widget.list.itemClicked.connect(self._variant_clicked)
        self.variant_widget.list.itemSelectionChanged.connect(self._variant_clicked)

        self.workspace_widget.list.itemClicked.connect(self._workspace_clicked)
        self.workspace_widget.list.itemSelectionChanged.connect(self._workspace_clicked)

        self.file_widget.list.itemClicked.connect(self._file_clicked)
        self.file_widget.list.itemSelectionChanged.connect(self._file_clicked)
        self.file_widget.list.itemDoubleClicked.connect(self._file_double_clicked)

        self.rigging_compoenent_widget.list.itemClicked.connect(
            self._rigging_component_file_clicked
        )
        self.rigging_compoenent_widget.list.itemSelectionChanged.connect(
            self._rigging_component_file_clicked
        )
        self.rigging_compoenent_widget.list.itemDoubleClicked.connect(self._file_double_clicked)
        self.launch_workspace_but.clicked.connect(self._open_workspace_triggered)

        self.save_but.clicked.connect(self._save_clicked)
        self.file_widget.list.itemDoubleClicked.connect(self._file_double_clicked)
        self.file_widget.list.itemClicked.connect(self._file_clicked)
        self.file_widget.list.itemSelectionChanged.connect(self._file_clicked)

        # Style Sheets
        style_sheet = "QStatusBar, QPushButton, QListWidget, QLabel, "
        style_sheet += "QComboBox, QMenuBar, QSpinBox, "
        style_sheet += "QLineEdit{font-size: 11pt;}"
        self.setStyleSheet(style_sheet)

        # Start up
        self._show_all_rigging_uis(False)
        self.project_widget.pop_folders()

        scene_parts = get_maya_scene_path().parts

        if len(scene_parts) >= 12:
            self.project_widget.select_by_name(scene_parts[-8])
            self.asset_widget.select_by_name(scene_parts[-6])
            self.step_widget.select_by_name(scene_parts[-4])
            self.file_widget.select_by_name(scene_parts[-3])

        self.user_le.line_edit.setText(os.getenv("USER"))

        self._rebuild_menu_bar()

    def _show_all_rigging_uis(self, show: bool):
        for i in range(self.rigging_component_vl.count()):
            item: QtWidgets.QLayoutItem = self.rigging_component_vl.itemAt(i)
            widget: QtWidgets.QWidget = item.widget()
            if widget is not None:
                if show:
                    widget.show()
                else:
                    widget.hide()

    def _rebuild_menu_bar(self):
        self.menu_bar.clear()
        self.file_menu = self.menu_bar.addMenu("&File")

        open_folder_act = QtWidgets.QAction("&Open Folder", self)
        self.file_menu.addAction(open_folder_act)
        open_folder_act.triggered.connect(self._open_folder_triggered)

        self.file_menu.addSeparator()

        copy_path_act = QtWidgets.QAction("Copy path to clipboard", self)
        self.file_menu.addAction(copy_path_act)
        copy_path_act.triggered.connect(self._copy_path_clicked)

        copy_stem_act = QtWidgets.QAction("Copy stem to clipboard", self)
        self.file_menu.addAction(copy_stem_act)
        copy_stem_act.triggered.connect(self._copy_stem_clicked)

        self.file_menu.addSeparator()

        save_act = QtWidgets.QAction("&Save", self)
        self.file_menu.addAction(save_act)
        save_act.triggered.connect(self._save_clicked)

        open_file_act = QtWidgets.QAction("&Open File", self)
        self.file_menu.addAction(open_file_act)
        open_file_act.triggered.connect(self._open_file_triggered)

        self.file_menu.addSeparator()

        import_act = QtWidgets.QAction("&Import", self)
        self.file_menu.addAction(import_act)
        import_act.setShortcut(QtGui.QKeySequence("Ctrl+I"))
        import_act.triggered.connect(self._import_triggered)

        ref_act = QtWidgets.QAction("&Create Reference...", self)
        self.file_menu.addAction(ref_act)
        ref_act.setShortcut(QtGui.QKeySequence("Ctrl+R"))
        ref_act.triggered.connect(self._ref_triggered)

        open_workspace_act = QtWidgets.QAction("Open &Workspace", self)
        self.file_menu.addAction(open_workspace_act)
        open_workspace_act.setShortcut(QtGui.QKeySequence("Ctrl+Shift+O"))
        open_workspace_act.triggered.connect(self._open_workspace_triggered)

    def _copy_path_clicked(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(str(self.selected_path))

    def _copy_stem_clicked(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(Path(self.selected_path).stem)

    def _open_file_triggered(self):
        self._open_scene(str(self.selected_path))

    def _open_folder_triggered(self):
        subprocess.Popen(["nautilus", str(self.selected_path)])

    def _import_triggered(self):
        result = mc.confirmDialog(
            title="Import:",
            message=self.selected_path,
            button=["Yes", "No"],
            defaultButton="No",
            cancelButton="No",
            dismissString="No",
        )
        if result == "Yes":
            mc.file(self.selected_path, i=True)
        else:
            return False

    def _ref_triggered(self):
        result = mc.confirmDialog(
            title="Create Reference:",
            message=self.selected_path,
            button=["Yes", "No"],
            defaultButton="No",
            cancelButton="No",
            dismissString="No",
        )
        if result == "Yes":
            mc.file(self.selected_path, r=True, ns=self.selected_path.stem)
        else:
            return False

    def _open_workspace_triggered(self):
        workspace = run_workspace.maya_run()
        workspace.folder_browser.line_edit.setText(str(self.workspace_widget.path))
        workspace.workspace_list.select_by_name(self.workspace_widget.get_selected())

    def _project_clicked(self):

        self.asset_widget.list.clear()
        self.step_widget.list.clear()
        self.file_widget.list.clear()

        selected = self.project_widget.get_selected()

        if not selected:
            return False

        selected_path = self.project_widget.path / selected / "assets"
        if not selected_path.exists():
            return False

        self.asset_widget.path = selected_path
        self.asset_widget.pop_folders()

        self.selected_path = selected_path

    def _asset_clicked(self):

        old_step = self.step_widget.get_selected()

        self.step_widget.list.clear()
        self.file_widget.list.clear()

        selected = self.asset_widget.get_selected()

        if not selected:
            return False

        selected_path = self.asset_widget.path / selected / "work"
        if not selected_path.exists():
            return False

        self.step_widget.path = selected_path
        self.step_widget.pop_folders()

        if old_step:
            self.step_widget.select_by_name(old_step)

        self.selected_path = selected_path

    def _step_clicked(self):
        self.file_widget.list.clear()
        self.variant_widget.list.clear()
        self.workspace_widget.list.clear()
        self.rigging_compoenent_widget.list.clear()

        selected = self.step_widget.get_selected()
        if not selected:
            return False

        selected_path = self.step_widget.path / selected
        if not selected_path.exists():
            return False

        self.file_widget.path = selected_path
        self.file_widget.pop_files()

        self.variant_widget.path = selected_path
        self.variant_widget.pop_folders()

        if selected == "rig":
            self._show_all_rigging_uis(True)
        else:
            self._show_all_rigging_uis(False)

        self.selected_path = selected_path

    def _variant_clicked(self):
        self.workspace_widget.list.clear()
        self.rigging_compoenent_widget.list.clear()

        selected = self.variant_widget.get_selected()

        if not selected:
            return False

        selected_path = self.variant_widget.path / selected
        if not selected_path.exists():
            return False

        self.workspace_widget.path = selected_path
        self.workspace_widget.pop_folders()

        self.selected_path = selected_path

    def _workspace_clicked(self):
        self.rigging_compoenent_widget.list.clear()

        selected = self.workspace_widget.get_selected()

        if not selected:
            return False

        selected_path = self.workspace_widget.path / selected
        if not selected_path.exists():
            return False

        self.rigging_compoenent_widget.path = selected_path
        self.rigging_compoenent_widget.pop_files()

        self.selected_path = selected_path

    def save_warning(self):
        if not mc.file(q=True, mf=True):
            return True

        result = mc.confirmDialog(
            title="Warning: Scene Not Saved",
            message="Save changes?",
            button=["Save", "Don't Save", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel",
            dismissString="Cancel",
        )

        if result == "Save":
            mc.file(s=True, f=True, type="mayaAscii")
            return True
        elif result == "Don't Save":
            return True
        else:
            return False

    def _save_clicked(self):
        cwd = self.file_widget.path
        file = "{p}_{a}_{v}_{s}_{u}_{pt}.v{mv:03d}_{sv:02d}.ma".format(
            p=self.project_widget.get_selected(),
            a=self.asset_widget.get_selected(),
            v=self.variant_le.text(),
            s=self.step_widget.get_selected(),
            u=self.user_le.text(),
            pt=self.task_le.text(),
            mv=int(self.main_ver_sb.value()),
            sv=int(self.sub_ver_sb.value()),
        )

        if self.save_warning():
            scene_path = cwd / file
            mc.file(rn=str(scene_path))
            mc.file(s=True, f=True, type="mayaAscii")
            self.file_widget.pop_files()

    def _open_scene(self, scene_path: str):
        if self.save_warning():
            mc.file(scene_path, o=True, f=True)

    def _file_double_clicked(self):
        self._open_scene(self.selected_path)

    def _file_clicked(self):
        selected_file = self.file_widget.get_selected()

        if selected_file:
            self.selected_path = self.file_widget.path / selected_file
        else:
            return False

        work_file = WorkFile.from_file_path(self.selected_path)

        self.variant_le.line_edit.setText(work_file.var)
        self.user_le.line_edit.setText(os.getenv("USER"))
        self.task_le.line_edit.setText(work_file.task)
        self.main_ver_sb.val_sb.setValue(work_file.ver)
        self.sub_ver_sb.val_sb.setValue(work_file.sub_ver)

    def _rigging_component_file_clicked(self):
        selected_file = self.rigging_compoenent_widget.get_selected()
        if selected_file:
            self.selected_path = self.rigging_compoenent_widget.path / selected_file
