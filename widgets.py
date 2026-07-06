from qtpy import QtCore, QtWidgets

from asset_browser.utils import group_files


class SettingsDialog(QtWidgets.QDialog):
    """Modal preferences dialog, opened from ``File > Settings...``.

    Edits the browser's persisted user preferences: which rigging workspace UI the
    ``Open Workspace`` action launches, and the folder ``Create Workspace`` copies its
    template workspaces from. Call :meth:`get_prefs` after ``exec_()`` returns truthy.
    """

    WORKSPACE_UIS = ("pkrig3", "megarig")

    def __init__(self, parent, prefs: dict):
        super().__init__(parent)

        self.setWindowTitle("Asset Browser Settings")
        self.setMinimumWidth(440)

        form = QtWidgets.QFormLayout()

        self.workspace_ui_cb = QtWidgets.QComboBox()
        self.workspace_ui_cb.addItems(self.WORKSPACE_UIS)
        current_ui = prefs.get("workspace_ui", self.WORKSPACE_UIS[0])
        if current_ui in self.WORKSPACE_UIS:
            self.workspace_ui_cb.setCurrentText(current_ui)
        form.addRow("Open workspace with:", self.workspace_ui_cb)

        self.template_le = QtWidgets.QLineEdit(prefs.get("workspace_template_root", ""))
        browse_but = QtWidgets.QPushButton("...")
        browse_but.setFixedWidth(30)
        browse_but.clicked.connect(self._browse_template_root)
        template_hl = QtWidgets.QHBoxLayout()
        template_hl.setContentsMargins(0, 0, 0, 0)
        template_hl.addWidget(self.template_le)
        template_hl.addWidget(browse_but)
        form.addRow("Workspace template root:", template_hl)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_vl = QtWidgets.QVBoxLayout(self)
        main_vl.addLayout(form)
        main_vl.addWidget(buttons)

    def _browse_template_root(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Workspace Template Root", self.template_le.text()
        )
        if folder:
            self.template_le.setText(folder)

    def get_prefs(self) -> dict:
        return {
            "workspace_ui": self.workspace_ui_cb.currentText(),
            "workspace_template_root": self.template_le.text().strip(),
        }


class LineEditWidget(QtWidgets.QWidget):
    def __init__(self, name):
        super().__init__(None)

        self.name = name

        self.main_hl = QtWidgets.QHBoxLayout()
        self.main_hl.setContentsMargins(0, 0, 0, 0)

        self.label = QtWidgets.QLabel()
        self.label.setText(f"{self.name}:")

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
        super().__init__(None)

        self.name = name

        self.main_hl = QtWidgets.QHBoxLayout()
        self.main_hl.setContentsMargins(0, 0, 0, 0)

        self.label = QtWidgets.QLabel()
        self.label.setText(f"{self.name}:")

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
        super().__init__(None)

        self.name = name
        self.path = path
        self.setText(name)


class ListItemWidget(QtWidgets.QWidget):
    def __init__(self, name: str, path):
        super().__init__(None)

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
        return None

    def select_by_name(self, name: str):
        for i in range(self.list.count()):
            current_item = self.list.item(i)

            if ListWidgetItem not in type(current_item).mro():
                continue

            current_item: ListWidgetItem
            if current_item.name == str(name):
                self.list.setCurrentRow(i)


class TypeToFilterListWidget(ListItemWidget):
    """A list you filter by simply typing while it has focus.

    There is no persistent filter field. As soon as the user types, a small
    transient query strip appears above the list showing the active query;
    Backspace edits it and Escape clears it (and hides the strip again).
    """

    def __init__(self, name: str, path, with_create_button: bool = False):
        super().__init__(name, path)

        self._filter_text = ""

        # Transient query strip, sits between the header label and the list.
        self.query_label = QtWidgets.QLabel()
        self.query_label.setStyleSheet("color: #8ab4f8; padding: 2px;")
        self.query_label.setVisible(False)
        self.main_vl.insertWidget(1, self.query_label)

        self.create_but = None
        if with_create_button:
            self.create_but = QtWidgets.QPushButton("Create")
            self.main_vl.addWidget(self.create_but)

        self.list.installEventFilter(self)

    # ------- type-to-filter behavior -------

    def eventFilter(self, obj, event):
        if obj is self.list and event.type() == QtCore.QEvent.KeyPress:
            if self._handle_key(event):
                return True
        return super().eventFilter(obj, event)

    def _handle_key(self, event) -> bool:
        key = event.key()

        if key == QtCore.Qt.Key_Escape:
            if self._filter_text:
                self._set_filter("")
                return True
            return False

        if key == QtCore.Qt.Key_Backspace:
            if self._filter_text:
                self._set_filter(self._filter_text[:-1])
                return True
            return False

        # Let shortcuts (Ctrl/Alt/Meta) and navigation keys fall through to the list.
        if event.modifiers() & (
            QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier | QtCore.Qt.MetaModifier
        ):
            return False

        text = event.text()
        if text and text.isprintable():
            self._set_filter(self._filter_text + text)
            return True

        return False

    def _set_filter(self, text: str):
        self._filter_text = text
        self._apply_filter()
        self._update_query_label()

    def _apply_filter(self):
        needle = self._filter_text.lower()
        for i in range(self.list.count()):
            current_item = self.list.item(i)
            if ListWidgetItem not in type(current_item).mro():
                current_item.setHidden(bool(needle))
                continue
            current_item.setHidden(needle not in current_item.name.lower())

    def _update_query_label(self):
        if self._filter_text:
            self.query_label.setText(f"\U0001F50D  {self._filter_text}")
            self.query_label.setVisible(True)
        else:
            self.query_label.clear()
            self.query_label.setVisible(False)
