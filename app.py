#!/usr/bin/python3
import sys
import os

# 🌟 强行将系统级打包路径和本地开发路径并网注入 Python 搜寻链路（防止模块 ImportError）
sys.path.insert(0, "/usr/share/fedora-tweak-tool")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QPushButton, QLabel, 
                               QListWidget, QStackedWidget, QLineEdit)

# 🌟 挂载所有的模块化引擎
from modules.timezone import TimezoneManager
from modules.gpu import GpuManager
from modules.grub import GrubManager
from modules.cursor import CursorManager
from modules.repo import RepoManager

class FedoraTweakApp:
    def __init__(self):
        # 1. 🌟 智能自适应路径加载 UI 文件
        loader = QUiLoader()
        ui_possible_paths = [
            "/usr/share/fedora-tweak-tool/main.ui",  
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.ui"), 
            "main.ui" 
        ]
        
        ui_path = next((path for path in ui_possible_paths if os.path.exists(path)), None)
        if not ui_path:
            print("[CRITICAL] 无法找到 main.ui 核心资源文件！")
            sys.exit(-1)

        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.window = loader.load(ui_file)
        ui_file.close()

        # 全局状态防死锁锁定位
        self._is_loading_repos = False

        # 2. 🎛️ 捞出 UI 物理组件
        self.nav_list = self.window.findChild(QListWidget, "nav_list")
        self.content_stack = self.window.findChild(QStackedWidget, "content_stack")
        
        self.combo = self.window.findChild(QComboBox, "timezone_combo")
        self.btn = self.window.findChild(QPushButton, "apply_btn")
        self.current_lbl = self.window.findChild(QLabel, "current_zone_lbl")

        self.current_grub_lbl = self.window.findChild(QLabel, "current_grub_lbl")
        self.grub_path_edit = self.window.findChild(QLineEdit, "grub_path_edit")
        self.grub_browse_btn = self.window.findChild(QPushButton, "grub_browse_btn")
        self.grub_apply_btn = self.window.findChild(QPushButton, "grub_apply_btn")
        self.grub_theme_combo = self.window.findChild(QComboBox, "grub_theme_combo")
        self.grub_refresh_btn = self.window.findChild(QPushButton, "grub_refresh_btn")

        self.gpu_info_lbl = self.window.findChild(QLabel, "gpu_info_lbl")
        self.driver_status_lbl = self.window.findChild(QLabel, "driver_status_lbl")
        self.gpu_action_btn = self.window.findChild(QPushButton, "gpu_action_btn")

        self.cursor_theme_combo = self.window.findChild(QComboBox, "cursor_theme_combo")
        self.cursor_path_edit = self.window.findChild(QLineEdit, "cursor_path_edit")
        self.cursor_browse_btn = self.window.findChild(QPushButton, "cursor_browse_btn")
        self.cursor_apply_btn = self.window.findChild(QPushButton, "cursor_apply_btn")
        self.cursor_preview_lbl = self.window.findChild(QLabel, "cursor_preview_lbl")
        
        self.repo_list_widget = self.window.findChild(QListWidget, "repo_list_widget")
        self.recommended_repo_list = self.window.findChild(QListWidget, "recommended_repo_list")
        self.repo_refresh_btn = self.window.findChild(QPushButton, "repo_refresh_btn")

        if self.cursor_preview_lbl:
            canvas = QPixmap(128, 128)
            canvas.fill(Qt.transparent)     
            self.cursor_preview_lbl.setPixmap(canvas)

        # 3. 🧩 实例化子模块，将大管家 (self) 的权限移交
        self.tz_mgr = TimezoneManager(self)
        self.gpu_mgr = GpuManager(self)
        self.grub_mgr = GrubManager(self)
        self.cursor_mgr = CursorManager(self)
        self.repo_mgr = RepoManager(self)

        # 4. 🎚️ 焊接中央路由与事件通信流
        if self.nav_list and self.content_stack:
            def safe_page_switcher(row_index):
                if row_index < 0 or row_index >= self.content_stack.count(): return
                self.content_stack.setCurrentIndex(row_index)
                if self.repo_list_widget and self.repo_list_widget.isVisible():
                    self.repo_mgr.scan_and_render_system_repos()
            self.nav_list.currentRowChanged.connect(safe_page_switcher)

        if self.btn: self.btn.clicked.connect(self.tz_mgr.apply_timezone)
        if self.grub_browse_btn: self.grub_browse_btn.clicked.connect(self.grub_mgr.smart_browse_grub)
        if self.grub_refresh_btn: self.grub_refresh_btn.clicked.connect(self.grub_mgr.refresh_local_themes_combo)
        if self.grub_apply_btn: self.grub_apply_btn.clicked.connect(self.grub_mgr.dispatch_grub_apply)
        if self.gpu_action_btn: self.gpu_action_btn.clicked.connect(self.gpu_mgr.apply_gpu_codec_fix)
        if self.cursor_browse_btn: self.cursor_browse_btn.clicked.connect(self.cursor_mgr.smart_browse_cursor)
        if self.cursor_apply_btn: self.cursor_apply_btn.clicked.connect(self.cursor_mgr.dispatch_cursor_apply)
        if self.cursor_theme_combo: self.cursor_theme_combo.currentIndexChanged.connect(self.cursor_mgr.update_cursor_preview)
        
        if self.repo_list_widget: self.repo_list_widget.itemClicked.connect(self.repo_mgr.dispatch_repo_toggle_on_click)
        if self.recommended_repo_list:
            self.recommended_repo_list.itemClicked.connect(self.repo_mgr.dispatch_recommended_toggle_on_click)
        if self.repo_refresh_btn: self.repo_refresh_btn.clicked.connect(self.repo_mgr.scan_and_render_system_repos)

        # 5. 🚀 全面拉起冷启动渲染盘点
        self.tz_mgr.init_timezone_list()
        self.tz_mgr.refresh_current_timezone()
        self.grub_mgr.refresh_current_grub_theme()  
        self.grub_mgr.refresh_local_themes_combo() 
        self.gpu_mgr.detect_gpu_and_drivers()
        self.cursor_mgr.refresh_cursor_themes_combo() 
        
        if self.nav_list: self.nav_list.setCurrentRow(0)
        self.cursor_mgr.update_cursor_preview()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("fedora-tweak-tool.desktop")
    tweak_app = FedoraTweakApp()
    tweak_app.window.show()
    sys.exit(app.exec())