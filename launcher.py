from qtpy import QtWidgets

from maya import OpenMayaUI
import maya.cmds as mc

from asset_browser import asset_browser

if int(mc.about(v=True)) >= 2025:
    from shiboken6 import wrapInstance
else:
    from shiboken2 import wrapInstance


def launch_ui():

    if QtWidgets.QApplication.instance():
        window: QtWidgets.QMainWindow
        for window in QtWidgets.QApplication.allWindows():
            if "AssetBrowser" in window.objectName():
                window.destroy()

    main_window_ptr = OpenMayaUI.MQtUtil.mainWindow()
    main_window = wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    example_tool_ui_class = asset_browser.AssetBrowser(parent=main_window)
    example_tool_ui_class.show()
