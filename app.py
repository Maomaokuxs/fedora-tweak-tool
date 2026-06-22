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
                               QListWidget, QStackedWidget, QLineEdit, QMainWindow, QCheckBox)

# 🌟 挂载所有的模块化引擎
from modules.timezone import TimezoneManager
from modules.gpu import GpuManager
from modules.grub import GrubManager
from modules.cursor import CursorManager
from modules.repo import RepoManager
from modules.fcitx import FcitxManager

class FedoraTweakApp:
    def __init__(self):
        # =====================================================================
        # 1. 🌟 智能自适应路径加载 UI 文件（本地开发版绝对优先！）
        # =====================================================================
        loader = QUiLoader()
        ui_possible_paths = [
            # 🥇 第一优先级：当前代码所在目录下的 main.ui (保证开发修改立刻生效)
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.ui"), 
            # 🥈 第二优先级：当前终端工作目录下的 main.ui
            "main.ui",
            # 🥉 第三优先级（兜底）：系统级打包安装后的只读路径
            "/usr/share/fedora-tweak-tool/main.ui"  
        ]
        
        ui_path = next((path for path in ui_possible_paths if os.path.exists(path)), None)
        if not ui_path:
            print("[CRITICAL] 无法找到 main.ui 核心资源文件！")
            sys.exit(-1)
            
        print(f"[DEBUG 核心加载] 成功命中 UI 资源路径: {ui_path}")

        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.window = loader.load(ui_file)
        ui_file.close()

        # 全局状态防死锁锁定位
        self._is_loading_repos = False

        # =====================================================================
        # 2. 🎛️ 捞出 UI 物理组件 (硬核探针检测)
        # =====================================================================
        # --- 中央路由组件 ---
        self.nav_list = self.window.findChild(QListWidget, "nav_list")
        self.content_stack = self.window.findChild(QStackedWidget, "content_stack")
        
        print(f"[DEBUG 路由探测] nav_list (左侧边栏): {'✅ 成功挂载' if self.nav_list else '❌ 丢失'}")
        print(f"[DEBUG 路由探测] content_stack (右侧页面): {'✅ 成功挂载' if self.content_stack else '❌ 丢失'}")
        if self.content_stack:
            print(f"[DEBUG 路由探测] content_stack 内部目前共侦测到 {self.content_stack.count()} 个物理页面。")

        # --- 时区组件 ---
        self.combo = self.window.findChild(QComboBox, "timezone_combo")
        self.btn = self.window.findChild(QPushButton, "apply_btn")
        self.current_lbl = self.window.findChild(QLabel, "current_zone_lbl")

        # --- GRUB 引导组件 ---
        self.current_grub_lbl = self.window.findChild(QLabel, "current_grub_lbl")
        self.grub_path_edit = self.window.findChild(QLineEdit, "grub_path_edit")
        self.grub_browse_btn = self.window.findChild(QPushButton, "grub_browse_btn")
        self.grub_apply_btn = self.window.findChild(QPushButton, "grub_apply_btn")
        self.grub_theme_combo = self.window.findChild(QComboBox, "grub_theme_combo")
        self.grub_refresh_btn = self.window.findChild(QPushButton, "grub_refresh_btn")

        # --- GPU 硬件组件 ---
        self.gpu_info_lbl = self.window.findChild(QLabel, "gpu_info_lbl")
        self.driver_status_lbl = self.window.findChild(QLabel, "driver_status_lbl")
        self.gpu_action_btn = self.window.findChild(QPushButton, "gpu_action_btn")

        # --- 🐭 鼠标与输入法协同核心组件 ---
        self.cursor_theme_combo = self.window.findChild(QComboBox, "cursor_theme_combo")
        self.cursor_path_edit = self.window.findChild(QLineEdit, "cursor_path_edit")
        self.cursor_browse_btn = self.window.findChild(QPushButton, "btn_browse_cursor")  # 注意这里对应你的 UI name
        if not self.cursor_browse_btn: # 兼容旧名
            self.cursor_browse_btn = self.window.findChild(QPushButton, "cursor_browse_btn")
            
        self.cursor_apply_btn = self.window.findChild(QPushButton, "btn_apply_cursor")    # 注意这里对应你的 UI name
        if not self.cursor_apply_btn:  # 兼容旧名
            self.cursor_apply_btn = self.window.findChild(QPushButton, "cursor_apply_btn")
            
        self.cursor_preview_lbl = self.window.findChild(QLabel, "cursor_preview_lbl")
        
        if self.cursor_preview_lbl:
            canvas = QPixmap(128, 128)
            canvas.fill(Qt.transparent)     
            self.cursor_preview_lbl.setPixmap(canvas)

        # --- 软件源大管家组件 ---
        self.repo_list_widget = self.window.findChild(QListWidget, "repo_list_widget")
        self.recommended_repo_list = self.window.findChild(QListWidget, "recommended_repo_list")
        self.repo_refresh_btn = self.window.findChild(QPushButton, "repo_refresh_btn")

        # --- Fcitx 输入法主题组件 ---
        self.fcitx_current_theme_lbl = self.window.findChild(QLabel, "fcitx_current_theme_lbl")
        self.fcitx_theme_combo = self.window.findChild(QComboBox, "fcitx_theme_combo")
        self.fcitx_dark_theme_combo = self.window.findChild(QComboBox, "fcitx_dark_theme_combo")
        self.fcitx_auto_switch_check = self.window.findChild(QCheckBox, "fcitx_auto_switch_check")
        self.fcitx_path_edit = self.window.findChild(QLineEdit, "fcitx_path_edit")
        self.fcitx_browse_btn = self.window.findChild(QPushButton, "fcitx_browse_btn")
        self.fcitx_apply_btn = self.window.findChild(QPushButton, "fcitx_apply_btn")
        self.fcitx_refresh_btn = self.window.findChild(QPushButton, "fcitx_refresh_btn")
        self.fcitx_preview_lbl = self.window.findChild(QLabel, "fcitx_preview_lbl")


        # =====================================================================
        # 3. 🧩 实例化子模块，将大管家 (self) 的权限移交
        # =====================================================================
        self.tz_mgr = TimezoneManager(self)
        self.gpu_mgr = GpuManager(self)
        self.grub_mgr = GrubManager(self)
        self.cursor_mgr = CursorManager(self)
        self.repo_mgr = RepoManager(self)
        self.fcitx_mgr = FcitxManager(self)

        # =====================================================================
        # 4. 🎚️ 焊接中央路由与事件通信流
        # =====================================================================
        if self.nav_list and self.content_stack:
            def safe_page_switcher(row_index):
                print(f"\n[DEBUG 路由切页] ⚡ 接收到点击信号，试图切换至索引: {row_index}")
                if row_index < 0:
                    return
                
                total_pages = self.content_stack.count()
                if row_index >= total_pages:
                    print(f"[DEBUG 路由切页 致命] 越界拦截！右侧仅 {total_pages} 页，但请求了第 {row_index} 页。")
                    return
                
                self.content_stack.setCurrentIndex(row_index)
                print(f"[DEBUG 路由切页 成功] 右侧页面已无缝切换至: 页面 {row_index}")

                if hasattr(self, 'repo_list_widget') and self.repo_list_widget and self.repo_list_widget.isVisible():
                    self.repo_mgr.scan_and_render_system_repos()

            self.nav_list.currentRowChanged.connect(safe_page_switcher)
            print("[DEBUG 路由通信] 🔗 中央路由切页信号已成功焊接！")
        else:
            print("[DEBUG 路由通信 崩溃] ❌ 缺失左侧或右侧组件，切页信号无法焊接！")

        # --- 绑定业务模块动作 ---
        if self.btn: self.btn.clicked.connect(self.tz_mgr.apply_timezone)
        
        if self.grub_browse_btn: self.grub_browse_btn.clicked.connect(self.grub_mgr.smart_browse_grub)
        if self.grub_refresh_btn: self.grub_refresh_btn.clicked.connect(self.grub_mgr.refresh_local_themes_combo)
        if self.grub_apply_btn: self.grub_apply_btn.clicked.connect(self.grub_mgr.dispatch_grub_apply)
        
        if self.gpu_action_btn: self.gpu_action_btn.clicked.connect(self.gpu_mgr.apply_gpu_codec_fix)
        
        if self.cursor_browse_btn: self.cursor_browse_btn.clicked.connect(self.cursor_mgr.smart_browse_cursor)
        if self.cursor_apply_btn: self.cursor_apply_btn.clicked.connect(self.cursor_mgr.dispatch_cursor_apply)
        if self.cursor_theme_combo: self.cursor_theme_combo.currentIndexChanged.connect(self.cursor_mgr.update_cursor_preview)

        if self.fcitx_browse_btn: self.fcitx_browse_btn.clicked.connect(self.fcitx_mgr.smart_browse_theme)
        if self.fcitx_apply_btn: self.fcitx_apply_btn.clicked.connect(self.fcitx_mgr.dispatch_apply)
        if self.fcitx_refresh_btn: self.fcitx_refresh_btn.clicked.connect(self.fcitx_mgr.refresh_theme_combos)
        
        if self.repo_list_widget: self.repo_list_widget.itemClicked.connect(self.repo_mgr.dispatch_repo_toggle_on_click)
        if self.recommended_repo_list: self.recommended_repo_list.itemClicked.connect(self.repo_mgr.dispatch_recommended_toggle_on_click)
        if self.repo_refresh_btn: self.repo_refresh_btn.clicked.connect(self.repo_mgr.scan_and_render_system_repos)

        # =====================================================================
        # 5. 🚀 全面拉起冷启动渲染盘点
        # =====================================================================
        self.tz_mgr.init_timezone_list()
        self.tz_mgr.refresh_current_timezone()
        self.grub_mgr.refresh_current_grub_theme()  
        self.grub_mgr.refresh_local_themes_combo() 
        self.gpu_mgr.detect_gpu_and_drivers()
        self.cursor_mgr.refresh_cursor_themes_combo()
        self.fcitx_mgr.refresh_current_theme()
        self.fcitx_mgr.refresh_theme_combos()

        if self.nav_list: self.nav_list.setCurrentRow(0)
        self.cursor_mgr.update_cursor_preview()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("fedora-tweak-tool.desktop")
    tweak_app = FedoraTweakApp()
    tweak_app.window.show()
    sys.exit(app.exec())