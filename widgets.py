from qtpy import QtCore, QtWidgets

from asset_browser.utils import group_files


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


class ListItemWithFilterWidget(ListItemWidget):
    def __init__(self, name: str, path):
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
