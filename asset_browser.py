import os
from pathlib import Path

from qtpy import QtCore, QtGui, QtWidgets

import maya.cmds as mc

from pkrig3_ui import run_workspace

from asset_browser.models import WorkFile
from asset_browser.utils import (
    current_user,
    get_maya_scene_path,
    load_session_state,
    open_folder,
    save_session_state,
)
from asset_browser.widgets import (
    LineEditWidget,
    ListItemWidget,
    SpinBoxWidget,
    TypeToFilterListWidget,
)


class AssetBrowser(QtWidgets.QMainWindow):
    window = None

    def __init__(self, parent):
        super().__init__(parent)

        self.selected_path: Path

        self.setObjectName("AssetBrowser")
        self.setWindowTitle("AssetBrowser")
        self.resize(1100, 700)

        self._setup_ui()
        self._connect_signals()
        self._apply_style()
        self._load_initial_state()

    # ------- UI construction -------

    def _setup_ui(self):
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.central_vl = QtWidgets.QVBoxLayout(self.central_widget)
        self.central_vl.setSpacing(0)
        self.central_vl.setContentsMargins(5, 5, 5, 5)

        self.main_vl = QtWidgets.QVBoxLayout()
        self.main_vl.setSpacing(0)
        self.central_vl.addLayout(self.main_vl)

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

        self._setup_browser_columns()
        self._setup_tool_bar()
        self._rebuild_menu_bar()

    def _setup_browser_columns(self):
        # Project column
        self.project_vl = QtWidgets.QVBoxLayout()
        self.project_vl.setSpacing(0)
        self.main_hl.addLayout(self.project_vl)

        self.project_widget = TypeToFilterListWidget(
            "Projects", Path(os.getenv("PROJ_ROOT")), with_create_button=True
        )
        self.project_vl.addWidget(self.project_widget)

        # Asset / step column
        self.asset_vl = QtWidgets.QVBoxLayout()
        self.asset_vl.setSpacing(0)
        self.main_hl.addLayout(self.asset_vl)

        self.asset_widget = TypeToFilterListWidget("Assets", "", with_create_button=True)
        self.asset_vl.addWidget(self.asset_widget)

        self.asset_step_line = QtWidgets.QFrame(self.central_widget)
        self.asset_step_line.setFrameShape(QtWidgets.QFrame.HLine)
        self.asset_step_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.asset_vl.addWidget(self.asset_step_line)

        self.step_widget = ListItemWidget("Steps", "")
        self.asset_vl.addWidget(self.step_widget)

        self.asset_vl.setStretch(0, 3)
        self.asset_vl.setStretch(2, 1)

        # File column
        self.file_vl = QtWidgets.QVBoxLayout()
        self.file_vl.setSpacing(0)
        self.main_hl.addLayout(self.file_vl)

        self.file_widget = TypeToFilterListWidget("Files", "")
        self.file_vl.addWidget(self.file_widget)

        # Rigging column
        self.rigging_component_vl = QtWidgets.QVBoxLayout()
        self.rigging_component_vl.setSpacing(0)
        self.main_hl.addLayout(self.rigging_component_vl)

        self.variant_widget = ListItemWidget("Variants", "")
        self.rigging_component_vl.addWidget(self.variant_widget)

        self.workspace_widget = ListItemWidget("Workspaces", "")
        self.rigging_component_vl.addWidget(self.workspace_widget)

        self.launch_workspace_but = QtWidgets.QPushButton("Open Workspace")
        self.rigging_component_vl.addWidget(self.launch_workspace_but)

        self.rigging_component_widget = ListItemWidget("Rigging Components", "")
        self.rigging_component_vl.addWidget(self.rigging_component_widget)

        self.rigging_component_vl.setStretch(0, 1)
        self.rigging_component_vl.setStretch(1, 2)
        self.rigging_component_vl.setStretch(2, 1)
        self.rigging_component_vl.setStretch(3, 3)

        self.main_hl.setStretch(0, 1)
        self.main_hl.setStretch(1, 2)
        self.main_hl.setStretch(2, 5)
        self.main_hl.setStretch(3, 1)

    def _setup_tool_bar(self):
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

    def _rebuild_menu_bar(self):
        self.menu_bar.clear()
        self.file_menu = self.menu_bar.addMenu("&File")

        def add_action(label, handler, shortcut=None):
            act = QtWidgets.QAction(label, self)
            if shortcut:
                act.setShortcut(QtGui.QKeySequence(shortcut))
            act.triggered.connect(handler)
            self.file_menu.addAction(act)

        add_action("&Open Folder", self._open_folder_triggered)
        self.file_menu.addSeparator()
        add_action("Copy path to clipboard", self._copy_path_clicked)
        add_action("Copy stem to clipboard", self._copy_stem_clicked)
        self.file_menu.addSeparator()
        add_action("&Save", self._save_clicked)
        add_action("&Open File", self._open_file_triggered)
        self.file_menu.addSeparator()
        add_action("&Import", self._import_triggered, "Ctrl+I")
        add_action("&Create Reference...", self._ref_triggered, "Ctrl+R")
        add_action("Open &Workspace", self._open_workspace_triggered, "Ctrl+Shift+O")

    def _connect_signals(self):
        def on_click_or_select(list_widget, handler):
            list_widget.itemClicked.connect(handler)
            list_widget.itemSelectionChanged.connect(handler)

        on_click_or_select(self.project_widget.list, self._project_clicked)
        on_click_or_select(self.asset_widget.list, self._asset_clicked)
        on_click_or_select(self.step_widget.list, self._step_clicked)
        on_click_or_select(self.variant_widget.list, self._variant_clicked)
        on_click_or_select(self.workspace_widget.list, self._workspace_clicked)
        on_click_or_select(self.file_widget.list, self._file_clicked)
        on_click_or_select(self.rigging_component_widget.list, self._rigging_component_file_clicked)

        self.file_widget.list.itemDoubleClicked.connect(self._file_double_clicked)
        self.rigging_component_widget.list.itemDoubleClicked.connect(self._file_double_clicked)
        self.launch_workspace_but.clicked.connect(self._open_workspace_triggered)
        self.save_but.clicked.connect(self._save_clicked)
        self.project_widget.create_but.clicked.connect(self._create_project_clicked)
        self.asset_widget.create_but.clicked.connect(self._create_asset_clicked)

    def _apply_style(self):
        self.setStyleSheet(
            "QStatusBar, QPushButton, QListWidget, QLabel, "
            "QComboBox, QMenuBar, QSpinBox, QLineEdit{font-size: 11pt;}"
        )

    def _load_initial_state(self):
        self._show_all_rigging_uis(False)
        self.project_widget.pop_folders()

        # Prefer the open scene's location; fall back to the last session on exit.
        if not self._restore_selection_from_scene(get_maya_scene_path()):
            self._restore_session_state()

        self.user_le.line_edit.setText(current_user())

    def _restore_selection_from_scene(self, scene_path: Path) -> bool:
        """Mirror the open Maya scene's location in the browser columns.

        Regular scene layout:    <project>/assets/<asset>/work/<step>/<file>
        Workspace scene layout:  <project>/assets/<asset>/work/<step>/<variant>/<workspace>/<file>

        Returns True if the scene matched the pipeline layout and columns were selected.
        """
        parts = scene_path.parts
        work_idx = next(
            (i for i, p in enumerate(parts) if p == "work" and i >= 3 and parts[i - 2] == "assets"),
            None,
        )
        if work_idx is None or len(parts) < work_idx + 3:
            return False

        self.project_widget.select_by_name(parts[work_idx - 3])
        self.asset_widget.select_by_name(parts[work_idx - 1])
        self.step_widget.select_by_name(parts[work_idx + 1])

        in_workspace = len(parts) >= work_idx + 5
        if in_workspace:
            self.variant_widget.select_by_name(parts[work_idx + 2])
            self.workspace_widget.select_by_name(parts[work_idx + 3])
            self.rigging_component_widget.select_by_name(scene_path.name)
        else:
            self.file_widget.select_by_name(scene_path.name)

        return True

    # ------- Session persistence (restore last location when no scene is open) -------

    _SESSION_WIDGETS = (
        ("project", "project_widget"),
        ("asset", "asset_widget"),
        ("step", "step_widget"),
        ("variant", "variant_widget"),
        ("workspace", "workspace_widget"),
        ("file", "file_widget"),
        ("rigging_component", "rigging_component_widget"),
    )

    def _save_session_state(self):
        state = {key: getattr(self, attr).get_selected() for key, attr in self._SESSION_WIDGETS}
        save_session_state(state)

    def _restore_session_state(self):
        state = load_session_state()
        if not state:
            return

        # Select column-by-column; each selection cascades and populates the next.
        for key, attr in self._SESSION_WIDGETS:
            name = state.get(key)
            if name:
                getattr(self, attr).select_by_name(name)

    def closeEvent(self, event):
        self._save_session_state()
        super().closeEvent(event)

    def _show_all_rigging_uis(self, show: bool):
        for i in range(self.rigging_component_vl.count()):
            item: QtWidgets.QLayoutItem = self.rigging_component_vl.itemAt(i)
            widget: QtWidgets.QWidget = item.widget()
            if widget is not None:
                widget.setVisible(show)

    # ------- Cascade helper -------

    def _cascade(self, source_widget, downstream_widgets, subfolder: str = "") -> Path | None:
        """Clears downstream lists, validates the source selection, returns the resulting path.

        Returns None if there is no selection or the resulting path doesn't exist.
        """
        for w in downstream_widgets:
            w.list.clear()

        selected = source_widget.get_selected()
        if not selected:
            return None

        path = source_widget.path / selected
        if subfolder:
            path = path / subfolder

        if not path.exists():
            return None

        self.selected_path = path
        return path

    # ------- Column cascade handlers -------

    def _project_clicked(self):
        path = self._cascade(
            self.project_widget,
            [self.asset_widget, self.step_widget, self.file_widget],
            subfolder="assets",
        )
        if path is None:
            return
        self.asset_widget.path = path
        self.asset_widget.pop_folders()

    def _create_project_clicked(self):
        self._create_folder(self.project_widget, "Create Project", "Project name:")

    def _create_asset_clicked(self):
        self._create_folder(
            self.asset_widget, "Create Asset", "Asset name:", subfolders=("work", "rig")
        )

    def _create_folder(self, widget, title: str, message: str, subfolders: tuple = ()):
        """Prompt for a name and create ``<widget.path>/<name>/<*subfolders>``."""
        base = widget.path
        if not isinstance(base, Path) or not base.exists():
            mc.confirmDialog(title=title, message="Select a parent item first.", button=["OK"])
            return

        result = mc.promptDialog(
            title=title,
            message=message,
            button=["Create", "Cancel"],
            defaultButton="Create",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if result != "Create":
            return

        name = mc.promptDialog(q=True, text=True).strip()
        if not name:
            return

        new_path = base / name
        if new_path.exists():
            mc.confirmDialog(
                title=title,
                message=f"'{name}' already exists.",
                button=["OK"],
            )
            return

        new_path.joinpath(*subfolders).mkdir(parents=True)
        widget.pop_folders()
        widget.select_by_name(name)

    def _asset_clicked(self):
        old_step = self.step_widget.get_selected()
        path = self._cascade(
            self.asset_widget,
            [self.step_widget, self.file_widget],
            subfolder="work",
        )
        if path is None:
            return
        self.step_widget.path = path
        self.step_widget.pop_folders()
        if old_step:
            self.step_widget.select_by_name(old_step)

    def _step_clicked(self):
        selected = self.step_widget.get_selected()
        path = self._cascade(
            self.step_widget,
            [
                self.file_widget,
                self.variant_widget,
                self.workspace_widget,
                self.rigging_component_widget,
            ],
        )
        if path is None:
            return
        self.file_widget.path = path
        self.file_widget.pop_files()
        self.variant_widget.path = path
        self.variant_widget.pop_folders()
        self._show_all_rigging_uis(selected == "rig")

    def _variant_clicked(self):
        path = self._cascade(
            self.variant_widget,
            [self.workspace_widget, self.rigging_component_widget],
        )
        if path is None:
            return
        self.workspace_widget.path = path
        self.workspace_widget.pop_folders()

    def _workspace_clicked(self):
        path = self._cascade(
            self.workspace_widget,
            [self.rigging_component_widget],
        )
        if path is None:
            return
        self.rigging_component_widget.path = path
        self.rigging_component_widget.pop_files()

    def _file_clicked(self):
        selected_file = self.file_widget.get_selected()
        if not selected_file:
            return

        self.selected_path = self.file_widget.path / selected_file
        work_file = WorkFile.from_file_path(self.selected_path)

        self.variant_le.line_edit.setText(work_file.var)
        self.user_le.line_edit.setText(current_user())
        self.task_le.line_edit.setText(work_file.task)
        self.main_ver_sb.val_sb.setValue(work_file.ver)
        self.sub_ver_sb.val_sb.setValue(work_file.sub_ver)

    def _rigging_component_file_clicked(self):
        selected_file = self.rigging_component_widget.get_selected()
        if selected_file:
            self.selected_path = self.rigging_component_widget.path / selected_file

    def _file_double_clicked(self):
        self._open_scene(self.selected_path)

    # ------- Menu actions -------

    def _copy_path_clicked(self):
        QtWidgets.QApplication.clipboard().setText(str(self.selected_path))

    def _copy_stem_clicked(self):
        QtWidgets.QApplication.clipboard().setText(Path(self.selected_path).stem)

    def _open_file_triggered(self):
        self._open_scene(str(self.selected_path))

    def _open_folder_triggered(self):
        open_folder(self.selected_path)

    def _import_triggered(self):
        if self._confirm("Import:", self.selected_path):
            mc.file(self.selected_path, i=True)

    def _ref_triggered(self):
        if self._confirm("Create Reference:", self.selected_path):
            mc.file(self.selected_path, r=True, ns=self.selected_path.stem)

    def _open_workspace_triggered(self):
        workspace = run_workspace.maya_run()
        workspace.folder_browser.line_edit.setText(str(self.workspace_widget.path))
        workspace.workspace_list.select_by_name(self.workspace_widget.get_selected())

    @staticmethod
    def _confirm(title: str, message) -> bool:
        result = mc.confirmDialog(
            title=title,
            message=message,
            button=["Yes", "No"],
            defaultButton="No",
            cancelButton="No",
            dismissString="No",
        )
        return result == "Yes"

    # ------- Save / open -------

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
        if result == "Don't Save":
            return True
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

    def _open_scene(self, scene_path):
        if self.save_warning():
            mc.file(str(scene_path), o=True, f=True)
