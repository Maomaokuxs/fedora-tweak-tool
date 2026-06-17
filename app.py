#!/usr/bin/python3
import sys
import subprocess
import os
import re
import zipfile
import tarfile
import shutil
import struct  # 🌟 核心保留：用于解剖 Xcursor 二进制的 TOC 结构

# 🌟 将所有 PySide6 依赖归装整齐，合并为一个干净的导入管线，杜绝重复与未定义报错
from PySide6.QtCore import QFile, Qt  
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtWidgets import (QApplication, QMessageBox, QComboBox, 
                               QPushButton, QLabel, QListWidget, QStackedWidget,
                               QLineEdit, QFileDialog, QInputDialog, QCheckBox) 

class FedoraTweakApp:
    def __init__(self):
        # =====================================================================
        # 1. 🌟 智能自适应路径加载 UI 文件
        # =====================================================================
        loader = QUiLoader()
        
        ui_possible_paths = [
            "/usr/share/fedora-tweak-tool/main.ui",  # RPM 安装后的系统级静态资源规范路径
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.ui"), # 本地 Git 开发目录相对路径
            "main.ui"  # 备用路径
        ]
        
        ui_path = None
        for path in ui_possible_paths:
            if os.path.exists(path):
                ui_path = path
                break

        if not ui_path:
            print("[CRITICAL] 无法在任何预设路径下找到 main.ui 核心资源文件！")
            sys.exit(-1)

        print(f"[DEBUG 启动 🚀] 成功锁定 UI 资源路径: '{ui_path}'")
        
        ui_file = QFile(ui_path)
        if not ui_file.open(QFile.ReadOnly):
            print(f"[CRITICAL] 无法以只读模式打开 UI 文件: {ui_path}")
            sys.exit(-1)
        self.window = loader.load(ui_file)
        ui_file.close()

        # =====================================================================
        # 2. 🔒 保留原生标签页物理联动逻辑（金刚不坏：自适应多页流控中心）
        # =====================================================================
        self.nav_list = self.window.findChild(QListWidget, "nav_list")
        self.content_stack = self.window.findChild(QStackedWidget, "content_stack")
        
        # 🌟 增加极其暴力的自检报警，瞬间定位是否是改名导致的丢失！
        if not self.nav_list:
            print("[CRITICAL 致命错误] 找不到名为 'nav_list' 的左侧边栏！请去 Qt Designer 检查 objectName！")
        if not self.content_stack:
            print("[CRITICAL 致命错误] 找不到名为 'content_stack' 的右侧堆栈页面！请去 Qt Designer 检查 objectName！")

        if self.nav_list and self.content_stack:
            def safe_page_switcher(row_index):
                if row_index < 0 or row_index >= self.content_stack.count():
                    print(f"[DEBUG 导航 警告] 触发了无效行号 {row_index}，右侧 Page 数量仅为 {self.content_stack.count()}")
                    return
                
                # 1. 强行拨动右侧堆栈页面
                self.content_stack.setCurrentIndex(row_index)
                page_name = self.content_stack.currentWidget().objectName()
                print(f"[DEBUG 导航 🚀] 边栏拨动 -> 强行切入第 {row_index} 页 ({page_name})")
                
                # 2. 🌟 真正的精准懒加载：只有当包含软件源列表的那个页面“被翻出来可见”时，才去疯狂读取硬盘配置！
                if hasattr(self, "repo_list_widget") and self.repo_list_widget and self.repo_list_widget.isVisible():
                    self.scan_and_render_system_repos()

            self.nav_list.currentRowChanged.connect(safe_page_switcher)

        # =====================================================================
        # 3. 🔒 核心状态机物理底板初始化
        # =====================================================================
        self.system_themes_root = "/usr/share/grub/themes" 
        self.detected_vendor = "Unknown"  
        self.nvidia_driver_installed = False
        self.vaapi_perfect = False       

        # =====================================================================
        # 4. 🎛️ 绑定各面板 UI 物理组件
        # =====================================================================
        # 时区组件
        self.combo = self.window.findChild(QComboBox, "timezone_combo")
        self.btn = self.window.findChild(QPushButton, "apply_btn")
        self.current_lbl = self.window.findChild(QLabel, "current_zone_lbl")

        # GRUB 组件
        self.current_grub_lbl = self.window.findChild(QLabel, "current_grub_lbl")
        self.grub_path_edit = self.window.findChild(QLineEdit, "grub_path_edit")
        self.grub_browse_btn = self.window.findChild(QPushButton, "grub_browse_btn")
        self.grub_apply_btn = self.window.findChild(QPushButton, "grub_apply_btn")
        self.grub_theme_combo = self.window.findChild(QComboBox, "grub_theme_combo")
        self.grub_refresh_btn = self.window.findChild(QPushButton, "grub_refresh_btn")

        # 显卡编解码组件
        self.gpu_info_lbl = self.window.findChild(QLabel, "gpu_info_lbl")
        self.driver_status_lbl = self.window.findChild(QLabel, "driver_status_lbl")
        self.gpu_action_btn = self.window.findChild(QPushButton, "gpu_action_btn")

        # 鼠标光标主题组件
        self.cursor_theme_combo = self.window.findChild(QComboBox, "cursor_theme_combo")
        self.cursor_path_edit = self.window.findChild(QLineEdit, "cursor_path_edit")
        self.cursor_browse_btn = self.window.findChild(QPushButton, "cursor_browse_btn")
        self.cursor_apply_btn = self.window.findChild(QPushButton, "cursor_apply_btn")
        self.cursor_preview_lbl = self.window.findChild(QLabel, "cursor_preview_lbl")
        
        # 动态软件源管理器组件
        self.repo_list_widget = self.window.findChild(QListWidget, "repo_list_widget")

        # 动态软件源管理器组件
        self.repo_list_widget = self.window.findChild(QListWidget, "repo_list_widget")
        # 👇 添加这一行来接管刷新按钮
        self.repo_refresh_btn = self.window.findChild(QPushButton, "repo_refresh_btn")

        # 🌟 鼠标预览图层安全防黑初始化
        if self.cursor_preview_lbl:
            canvas = QPixmap(128, 128)
            canvas.fill(Qt.transparent)     
            self.cursor_preview_lbl.setPixmap(canvas)

        # =====================================================================
        # 5. 🎚️ 焊接信号与槽映射通道
        # =====================================================================
        if self.btn: self.btn.clicked.connect(self.apply_timezone)
        if self.grub_browse_btn: self.grub_browse_btn.clicked.connect(self.smart_browse_grub)
        if self.grub_refresh_btn: self.grub_refresh_btn.clicked.connect(self.refresh_local_themes_combo)
        if self.grub_apply_btn: self.grub_apply_btn.clicked.connect(self.dispatch_grub_apply)
        if self.gpu_action_btn: self.gpu_action_btn.clicked.connect(self.apply_gpu_codec_fix)
        if self.cursor_browse_btn: self.cursor_browse_btn.clicked.connect(self.smart_browse_cursor)
        if self.cursor_apply_btn: self.cursor_apply_btn.clicked.connect(self.dispatch_cursor_apply)
        if self.repo_list_widget:
            self.repo_list_widget.itemClicked.connect(self.dispatch_repo_toggle_on_click)
               
        # 🌟 动态断线重连接口：这里不需要强行给 repo_list_widget 挂在 init 中连接 itemChanged 信号
        # 因为我们的 scan_and_render_system_repos 会在每次刷新完毕时自动把监听钩子精准挂上！
        if self.cursor_theme_combo:
            self.cursor_theme_combo.currentIndexChanged.connect(self.update_cursor_preview)
        
        # 🌟 软件源列表刷新按钮连线：点击就直接呼叫底层的全盘扫描函数！
        if self.repo_refresh_btn:
            self.repo_refresh_btn.clicked.connect(self.scan_and_render_system_repos)

        # =====================================================================
        # 6. 🚀 全面拉起数据流冷盘点
        # =====================================================================
        self.init_timezone_list()
        self.refresh_current_timezone()
        self.refresh_current_grub_theme()  
        self.refresh_local_themes_combo() 
        self.detect_gpu_and_drivers()
        self.refresh_cursor_themes_combo() 
        
        # 强行拨动至第 0 页，触发初始画面渲染
        if self.nav_list:
            self.nav_list.setCurrentRow(0)
        self.update_cursor_preview()

    # ================= 时区逻辑区 =================
    def init_timezone_list(self):
        if not self.combo: return
        try:
            result = subprocess.run(["timedatectl", "list-timezones"], capture_output=True, text=True, check=True)
            all_zones = [zone.strip() for zone in result.stdout.split("\n") if zone.strip()]
            self.combo.addItems(all_zones)
        except Exception as e:
            self.combo.addItems(["Asia/Shanghai", "UTC"])

    def refresh_current_timezone(self):
        try:
            result = subprocess.run(["timedatectl", "show", "--property=Timezone", "--value"], capture_output=True, text=True, check=True)
            if self.current_lbl: self.current_lbl.setText(result.stdout.strip())
        except Exception as e:
            print(f"[DEBUG 时区 错误] 获取当前时区失败: {e}")

    def apply_timezone(self):
        if not self.combo: return
        cmd = ["pkexec", "timedatectl", "set-timezone", self.combo.currentText()]
        try:
            if subprocess.run(cmd).returncode == 0:
                QMessageBox.information(self.window, "成功", "时区修改成功！")
                self.refresh_current_timezone()
        except Exception as e: print(e)

    # ================= 显卡与编解码全家桶检测 =================
    def detect_gpu_and_drivers(self):
        print("[DEBUG 硬件] 开始清点 PCI 巴士上的显卡硬件及硬件加速生态...")
        gpu_info_text = "未侦测到主流显卡"
        driver_status_text = "系统正处于基础渲染状态。"
        try:
            result = subprocess.run(["lspci"], capture_output=True, text=True, check=True)
            lspci_out = result.stdout
            gpus = [line for line in lspci_out.splitlines() if "VGA compatible" in line or "3D controller" in line]
            if gpus:
                display_gpus = []
                for gpu in gpus:
                    if "NVIDIA" in gpu:
                        self.detected_vendor = "NVIDIA"
                        match = re.search(r'\[([^\]]+)\]', gpu)
                        display_gpus.append(f"🟢 NVIDIA [{match.group(1) if match else 'GeForce'}]")
                    elif "Advanced Micro Devices" in gpu or "AMD" in gpu:
                        if self.detected_vendor != "NVIDIA": self.detected_vendor = "AMD"
                        display_gpus.append("🔴 AMD Radeon Graphics (已原生免驱)")
                    elif "Intel" in gpu:
                        if self.detected_vendor == "Unknown": self.detected_vendor = "Intel"
                        display_gpus.append("🔵 Intel HD / Arc Graphics (已原生免驱)")
                gpu_info_text = "\n".join(display_gpus)

            if self.detected_vendor == "NVIDIA":
                if os.path.exists("/proc/driver/nvidia/version"):
                    self.nvidia_driver_installed = True
                    driver_status_text = "NVIDIA 官方闭源驱动：【 已正确加载 】\n"
                    vaapi_check = subprocess.run(["rpm", "-q", "libva-nvidia-driver"], capture_output=True, text=True)
                    if vaapi_check.returncode == 0:
                        self.vaapi_perfect = True
                        driver_status_text += "多媒体编解码格式：【 H.264/H.265/NVENC 全格式硬解打通 】"
                    else:
                        driver_status_text += "⚠️ 编解码格式受限：缺少 VA-API 桥接包，高码率录屏可能导致 CPU 飙升！"
                else:
                    driver_status_text = "⚠️ 运行受限：检测到 NVIDIA 显卡，但正运行于开源驱动下。"
            elif self.detected_vendor in ["AMD", "Intel"]:
                freeworld_check = subprocess.run(["rpm", "-q", "mesa-va-drivers-freeworld"], capture_output=True, text=True)
                if freeworld_check.returncode == 0:
                    self.vaapi_perfect = True
                    driver_status_text = f"{self.detected_vendor} 原生图形驱动：【 运行状态完美 】\n多媒体编解码格式：【 H.264 / H.265 专利全格式硬解已全激活 】"
                else:
                    driver_status_text = f"{self.detected_vendor} 原生图形驱动：【 运行状态良好 】\n⚠️ 编解码格式受限：Fedora 默认禁用了商业视频硬解！"

            if self.gpu_action_btn:
                if self.vaapi_perfect:
                    self.gpu_action_btn.setText("🎉 当前多媒体硬解加速已处于完美状态")
                    self.gpu_action_btn.setEnabled(False)
                else:
                    self.gpu_action_btn.setEnabled(True)
                    if self.detected_vendor == "NVIDIA":
                        if not self.nvidia_driver_installed: self.gpu_action_btn.setText("一键安装 NVIDIA 闭源驱动 + 打通全格式硬解")
                        else: self.gpu_action_btn.setText("一键打通 NVENC / OBS 录屏硬件加速通道")
                    elif self.detected_vendor in ["AMD", "Intel"]: self.gpu_action_btn.setText(f"一键激活 {self.detected_vendor} 全格式多媒体视频硬解")
                    else: self.gpu_action_btn.setEnabled(False)
        except Exception as e: print(e)

        if self.gpu_info_lbl: self.gpu_info_lbl.setText(gpu_info_text)
        if self.driver_status_lbl: self.driver_status_lbl.setText(driver_status_text)

    def apply_gpu_codec_fix(self):
        if self.vaapi_perfect or self.detected_vendor == "Unknown": return
        if self.detected_vendor == "NVIDIA":
            if not self.nvidia_driver_installed:
                shell_script = """
                dnf5 config-manager --set-enabled fedora-cisco-openh264 || true
                dnf5 install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm || true
                dnf5 install -y https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-44.noarch.rpm || true
                dnf5 update -y --refresh
                dnf5 install -y akmod-nvidia xorg-x11-drv-nvidia-cuda libva-nvidia-driver nvidia-vaapi-driver
                """
                success_msg = "NVIDIA 闭源驱动与全格式硬解部署成功！请务必【重新启动电脑】！"
            else:
                shell_script = "dnf5 install -y libva-nvidia-driver nvidia-vaapi-driver gstreamer1-vaapi"
                success_msg = "NVIDIA VA-API 高速硬解通道打通成功！"
        elif self.detected_vendor in ["AMD", "Intel"]:
            shell_script = """
            dnf5 install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm || true
            dnf5 update -y --refresh
            dnf5 swap -y mesa-va-drivers mesa-va-drivers-freeworld
            dnf5 swap -y mesa-vdr-drivers mesa-vdr-drivers-freeworld
            dnf5 install -y gstreamer1-plugins-bad-freeworld gstreamer1-plugins-ugly-freeworld ffmpeg-free-devel
            """
            success_msg = f"🎉 恭喜！{self.detected_vendor} 开源全格式多媒体硬解加速已彻底激活！"

        QMessageBox.information(self.window, "准备整备环境", "工具即将拉起官方 Polkit 授权，请安心等候。")
        cmd = ["pkexec", "sh", "-c", shell_script]
        try:
            if subprocess.run(cmd, capture_output=True, text=True).returncode == 0:
                QMessageBox.information(self.window, "大获全胜", success_msg)
                self.detect_gpu_and_drivers()
        except Exception as e: print(e)

    # ================= GRUB 逻辑区 =================
    def refresh_current_grub_theme(self):
        if not os.path.exists("/etc/default/grub"): return
        try:
            with open("/etc/default/grub", "r", encoding="utf-8") as f: content = f.read()
            match = re.search(r'^\s*GRUB_THEME=["\' ]?([^"\'\n]+)["\' ]?', content, re.MULTILINE)
            if match:
                raw_path = match.group(1).strip()
                theme_name = os.path.basename(os.path.dirname(raw_path))
                status_text = f"当前正在使用的主题：【 {theme_name} 】"
            else: status_text = "当前正在使用的主题：系统默认文字菜单 (未启用主题)"
            if self.current_grub_lbl: self.current_grub_lbl.setText(status_text)
        except Exception as e: print(e)

    def refresh_local_themes_combo(self):
        if not self.grub_theme_combo or not os.path.exists(self.system_themes_root): return
        valid_themes = []
        try:
            for name in os.listdir(self.system_themes_root):
                full_path = os.path.join(self.system_themes_root, name)
                if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "theme.txt")): valid_themes.append(name)
            valid_themes.sort()
            self.grub_theme_combo.clear(); self.grub_theme_combo.addItems(valid_themes)
        except Exception as e: print(e)

    def dispatch_grub_apply(self):
        user_input_path = self.grub_path_edit.text().strip()
        if user_input_path: self.apply_grub_theme_archive(user_input_path)
        else: self.apply_local_grub_theme_switch()

    def apply_local_grub_theme_switch(self):
        if not self.grub_theme_combo or self.grub_theme_combo.currentIndex() == -1: return
        selected_name = self.grub_theme_combo.currentText()
        target_theme_txt = os.path.join(self.system_themes_root, selected_name, "theme.txt")
        shell_script = f"sed -i '/^GRUB_THEME=/d' /etc/default/grub && echo 'GRUB_THEME=\"{target_theme_txt}\"' >> /etc/default/grub && grub2-mkconfig -o /boot/grub2/grub.cfg"
        if subprocess.run(["pkexec", "sh", "-c", shell_script]).returncode == 0:
            QMessageBox.information(self.window, "成功", f"成功切换本地已有主题：【{selected_name}】")
            self.refresh_current_grub_theme()

    def smart_browse_grub(self):
        file_path, _ = QFileDialog.getOpenFileName(self.window, "选择 GRUB 主题", os.path.expanduser("~/Downloads"), "所有文件 (*)")
        if file_path: self.grub_path_edit.setText(file_path)

    def apply_grub_theme_archive(self, user_input_path):
        sandbox_dir = "/tmp/grub_theme_sandbox"
        if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)
        os.makedirs(sandbox_dir, exist_ok=True)
        try:
            if user_input_path.endswith('.zip'):
                with zipfile.ZipFile(user_input_path, 'r') as z: z.extractall(sandbox_dir)
            else:
                with tarfile.open(user_input_path, 'r:*') as t: t.extractall(sandbox_dir)
            detected_themes = {}
            for root, dirs, files in os.walk(sandbox_dir):
                if "theme.txt" in files:
                    current_dir = os.path.dirname(os.path.join(root, "theme.txt"))
                    detected_themes[f"{os.path.basename(os.path.dirname(current_dir))} - {os.path.basename(current_dir)}"] = current_dir
            if not detected_themes: raise ValueError("配置丢失！")
            elif len(detected_themes) == 1: final_source_dir = list(detected_themes.values())[0]
            else:
                chosen, ok = QInputDialog.getItem(self.window, "选择版本", "分辨率款式选择：", sorted(list(detected_themes.keys())), current=0, editable=False)
                if not ok: return
                final_source_dir = detected_themes[chosen]
            final_theme_dir_name = os.path.basename(final_source_dir)
        except Exception as e: QMessageBox.critical(self.window, "解析失败", str(e)); return

        target_system_path = os.path.join(self.system_themes_root, final_theme_dir_name)
        shell_script = f"mkdir -p \"{self.system_themes_root}\" && cp -r \"{final_source_dir}\" \"{target_system_path}\" && sed -i '/^GRUB_THEME=/d' /etc/default/grub && echo 'GRUB_THEME=\"{os.path.join(target_system_path, 'theme.txt')}\"' >> /etc/default/grub && grub2-mkconfig -o /boot/grub2/grub.cfg"
        if subprocess.run(["pkexec", "sh", "-c", shell_script]).returncode == 0:
            QMessageBox.information(self.window, "成功", "外部主题安装应用成功！")
            self.refresh_current_grub_theme(); self.refresh_local_themes_combo(); self.grub_path_edit.clear()
        if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)

    # ================= 🌟 鼠标主题样式管理区（完美对齐标准 XDG 路径版） =================
    def refresh_cursor_themes_combo(self):
        """
        全自动盘点系统与现代用户目录下的所有合法鼠标主题，并填充至下拉框
        """
        if not self.cursor_theme_combo: return
        self.cursor_theme_combo.clear()
        
        # 🌟 三维度无死角扫描：同时包容历史遗留路径、现代用户路径与系统全局路径
        search_paths = [
            os.path.expanduser("~/.icons"),              # 历史遗留老路径（你的 Future-cursors 在这里！）
            os.path.expanduser("~/.local/share/icons"),  # 现代 XDG 标准用户路径
            "/usr/share/icons"                            # 系统全局级路径
        ]
        
        valid_themes = []
        for path in search_paths:
            if not os.path.exists(path): continue
            try:
                for name in os.listdir(path):
                    if name == "default": continue  # 剔除软链接配置存根
                    full_path = os.path.join(path, name)
                    if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "cursors")):
                        if name not in valid_themes: valid_themes.append(name)
            except Exception as e: print(e)
                
        valid_themes.sort()
        self.cursor_theme_combo.addItems(valid_themes)
        print(f"[DEBUG 鼠标] 成功装载 {len(valid_themes)} 个可用的光标主题。")
        
        # 通过 KDE 6 官方原生工具精准截获唯一当前有效值
        try:
            result = subprocess.run(
                ["kreadconfig6", "--file", "kcminputrc", "--group", "Mouse", "--key", "cursorTheme"], 
                capture_output=True, text=True, check=True
            )
            true_theme = result.stdout.strip()
            print(f"[DEBUG 鼠标联动 🚀] KDE 6 核心层返回的当前真实鼠标主题为: '{true_theme}'")
            
            if true_theme:
                # 1. 第一步：尝试严格的完全匹配
                index = self.cursor_theme_combo.findText(true_theme)
                
                # 2. 第二步：如果严格匹配失败，启动不区分大小写的模糊包容性扫描
                if index == -1:
                    print(f"[DEBUG 鼠标联动 提示] 严格匹配失败，启动大小写模糊兼容扫描...")
                    for i in range(self.cursor_theme_combo.count()):
                        if self.cursor_theme_combo.itemText(i).lower() == true_theme.lower():
                            index = i
                            break
                
                # 3. 拨动指针
                if index != -1:
                    self.cursor_theme_combo.setCurrentIndex(index)
                    print(f"[DEBUG 鼠标联动 🚀] 下拉选单已完美锁定当前启用项: '{self.cursor_theme_combo.itemText(index)}'")
                else:
                    print(f"[DEBUG 鼠标联动 警告] 抓到了配置 '{true_theme}'，但三个 icons 扫描列表里确实缺少该文件夹。")
        except Exception as e:
            print(f"[DEBUG 鼠标抓取 失败] 无法通过 kreadconfig6 捕获状态: {e}")

    def smart_browse_cursor(self):
        """
        鼠标光标包本地智能文件选择器
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.window, "选择鼠标主题压缩包", os.path.expanduser("~/Downloads"), "鼠标包 (*.tar.gz *.tar.xz *.zip *.tgz)"
        )
        if file_path: self.cursor_path_edit.setText(file_path)

    def dispatch_cursor_apply(self):
        """
        中央双模调度。输入框有路径则【解压导入并应用】，为空则【本地就地切换】。
        """
        import os
        import shutil
        import tarfile
        import zipfile
        from PySide6.QtWidgets import QMessageBox

        user_input_path = self.cursor_path_edit.text().strip() if self.cursor_path_edit else ""

        # =====================================================================
        # 模式 A：外部压缩包解压导入
        # =====================================================================
        if user_input_path:
            if not os.path.exists(user_input_path):
                QMessageBox.critical(self.window, "错误", "指定的压缩包路径不存在！")
                return

            sandbox_dir = "/tmp/cursor_theme_sandbox"
            if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)
            os.makedirs(sandbox_dir, exist_ok=True)

            try:
                if user_input_path.endswith('.zip'):
                    with zipfile.ZipFile(user_input_path, 'r') as z: z.extractall(sandbox_dir)
                elif user_input_path.endswith(('.tar.xz', '.xz')):
                    with tarfile.open(user_input_path, 'r:xz') as t: t.extractall(sandbox_dir)
                else:
                    with tarfile.open(user_input_path, 'r:gz') as t: t.extractall(sandbox_dir)

                # 深入搜索防套娃
                target_theme_source_dir = None
                for root, dirs, files in os.walk(sandbox_dir):
                    if "cursors" in dirs:
                        target_theme_source_dir = root
                        break

                if not target_theme_source_dir:
                    raise ValueError("未在包内找到包含 'cursors' 的合规鼠标主题文件夹！")

                theme_dir_name = os.path.basename(target_theme_source_dir)
                
                # 强行落地到用户的现代 XDG 目录
                user_icons_root = os.path.expanduser("~/.local/share/icons")
                target_deploy_path = os.path.join(user_icons_root, theme_dir_name)

                os.makedirs(user_icons_root, exist_ok=True)
                if os.path.exists(target_deploy_path): shutil.rmtree(target_deploy_path)
                
                # 顺滑平铺部署
                shutil.copytree(target_theme_source_dir, target_deploy_path)
                
                # 核心配置应用与 KDE/Wayland 实时热刷新
                self.execute_cursor_apply_core(theme_dir_name)
                
                # 刷新下拉框列表，并强制让下拉框高亮选中这个刚导入的新主题
                self.refresh_cursor_themes_combo()
                if self.cursor_theme_combo:
                    idx = self.cursor_theme_combo.findText(theme_dir_name)
                    if idx != -1: self.cursor_theme_combo.setCurrentIndex(idx)

                if self.cursor_path_edit: self.cursor_path_edit.clear()
                
                # 🌟 联动刷新预览：让刚导入的高清 2x2 阵列立刻呈现在画布上
                self.update_cursor_preview()
                
                QMessageBox.information(self.window, "成功", f"外部鼠标主题 【{theme_dir_name}】 导入并应用成功！")

            except Exception as e:
                QMessageBox.critical(self.window, "导入失败", str(e))
            finally:
                if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)

        # =====================================================================
        # 模式 B：本地已有主题一键切换
        # =====================================================================
        else:
            if not self.cursor_theme_combo or self.cursor_theme_combo.currentIndex() == -1:
                QMessageBox.warning(self.window, "提示", "请选择本地鼠标主题，或导入外部压缩包！")
                return
            target_theme = self.cursor_theme_combo.currentText()
            try:
                # 1. 刷写底层配置并让 KWin 热重载
                self.execute_cursor_apply_core(target_theme)
                
                # 2. 🌟 核心联动微调：切换成功后，立刻强刷新右侧 2x2 矩阵预览，保证视觉绝对同步
                self.update_cursor_preview()
                
                QMessageBox.information(self.window, "切换成功", f"鼠标主题已成功切换为 【{target_theme}】！")
            except Exception as e:
                QMessageBox.critical(self.window, "失败", str(e))
    
    def execute_cursor_apply_core(self, theme_name):
        """
        三维一体配置刷写核心（现代 XDG 路径规范 + KDE 6 原生级热刷新适配）
        """
        import os
        import re
        import shutil
        import subprocess

        user_icons_dir = os.path.expanduser("~/.local/share/icons")
        default_theme_dir = os.path.join(user_icons_dir, "default")
        os.makedirs(default_theme_dir, exist_ok=True)
        
        # 1. XWayland 兼容层存根刷写
        with open(os.path.join(default_theme_dir, "index.theme"), "w", encoding="utf-8") as f:
            f.write(f"[Icon Theme]\nName=Default\nComment=Default Cursor Theme\nInherits={theme_name}\n")

        # 2. GTK 3 & GTK 4 原生应用硬编码修改
        for gtk_ver in ["gtk-3.0", "gtk-4.0"]:
            gtk_dir = os.path.expanduser(f"~/.config/{gtk_ver}")
            os.makedirs(gtk_dir, exist_ok=True)
            ini_path = os.path.join(gtk_dir, "settings.ini")
            
            content = ""
            if os.path.exists(ini_path):
                with open(ini_path, "r", encoding="utf-8") as f: content = f.read()
                    
            if "gtk-cursor-theme-name=" in content:
                content = re.sub(r"gtk-cursor-theme-name=.*$", f"gtk-cursor-theme-name={theme_name}", content, flags=re.MULTILINE)
            else:
                if "[Settings]" not in content: content = "[Settings]\n" + content
                content = content.replace("[Settings]\n", f"[Settings]\ngtk-cursor-theme-name={theme_name}\n")
                
            with open(ini_path, "w", encoding="utf-8") as f: f.write(content)

        # 3. GNOME / 影子接口全局配置刷新
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "cursor-theme", theme_name], capture_output=True)

        # 4. 🌟 KDE 6 Plasma 原生级指针热重载
        if shutil.which("plasma-apply-cursortheme"):
            print(f"[DEBUG 鼠标 🚀] 检测到 KDE Plasma 环境，向 KWin 注入原生级热重载命令...")
            subprocess.run(["plasma-apply-cursortheme", theme_name], capture_output=True)

    def update_cursor_preview(self):
        """
        🌟 终极高清矩阵预览引擎：跨路径盲盒清盘，TOC高清狙击导航，全自动拼合成 2x2 黄金阵列画板
        """
        import os
        import struct
        from PySide6.QtGui import QPixmap, QImage, QPainter
        from PySide6.QtCore import Qt
        
        if not self.cursor_theme_combo or not self.cursor_preview_lbl: return
        
        selected_theme = self.cursor_theme_combo.currentText()
        if not selected_theme: 
            self.cursor_preview_lbl.setText("暂无预览")
            return
            
        # 1. 三维度无死角锁定物理阵地
        possible_roots = [
            os.path.expanduser("~/.icons"),
            os.path.expanduser("~/.local/share/icons"),
            "/usr/share/icons"
        ]
        
        theme_path = None
        for root in possible_roots:
            test_path = os.path.join(root, selected_theme)
            if os.path.exists(test_path):
                theme_path = test_path
                break
        
        canvas_width = 128
        canvas_height = 128
        canvas = QPixmap(canvas_width, canvas_height)
        canvas.fill(Qt.transparent)
        
        preview_success = False

        if theme_path:
            cursors_dir = os.path.join(theme_path, "cursors")
            if os.path.exists(cursors_dir) and os.path.isdir(cursors_dir):
                
                # 2. 2x2 四宫格布局特征词：正常选择、链接选择、文本输入、系统忙碌
                grid_slots = [
                    ["left_ptr", "default", "arrow"],          
                    ["pointer", "pointing_hand", "hand2"],     
                    ["xterm", "ibeam", "text"],                
                    ["wait", "watch", "progress", "half-busy"] 
                ]
                
                painter = QPainter(canvas)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                
                images_drawn = 0
                
                for i, fallbacks in enumerate(grid_slots):
                    target_file = None
                    for name in fallbacks:
                        b_path = os.path.join(cursors_dir, name)
                        if os.path.lexists(b_path): 
                            target_file = b_path
                            break
                            
                    if target_file:
                        try:
                            real_path = os.path.realpath(target_file)
                            if not os.path.exists(real_path) or os.path.isdir(real_path): continue
                                
                            with open(real_path, "rb") as f:
                                data = f.read()
                                
                            if data[:4] == b"Xcur":
                                ntoc = struct.unpack("<I", data[8:12])[0]
                                img_offset = None
                                pos = 16
                                
                                # 🎯 TOC高清狙击算法
                                max_size_found = 0
                                for _ in range(ntoc):
                                    if pos + 12 > len(data): break
                                    ctype, csub, cpos = struct.unpack("<III", data[pos:pos+12])
                                    
                                    if ctype == 0xfffd0002 and 16 <= csub <= 128:
                                        if csub > max_size_found:
                                            max_size_found = csub
                                            img_offset = cpos
                                    pos += 12
                                    
                                if img_offset and img_offset + 36 <= len(data):
                                    w, h = struct.unpack("<II", data[img_offset+16:img_offset+24])
                                    
                                    if 16 <= w <= 128 and 16 <= h <= 128:
                                        pixel_start = img_offset + 36
                                        pixel_len = w * h * 4
                                        if pixel_start + pixel_len <= len(data):
                                            pixels = data[pixel_start:pixel_start+pixel_len]
                                            qimg = QImage(pixels, w, h, QImage.Format_ARGB32)
                                            
                                            pix = QPixmap.fromImage(qimg)
                                            scaled_pix = pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                            
                                            quadrant_x = (i % 2) * 64
                                            quadrant_y = (i // 2) * 64
                                            
                                            render_x = quadrant_x + (64 - scaled_pix.width()) // 2
                                            render_y = quadrant_y + (64 - scaled_pix.height()) // 2
                                            
                                            painter.drawPixmap(render_x, render_y, scaled_pix)
                                            images_drawn += 1
                        except Exception as parse_err:
                            print(f"[DEBUG 阵列加载] '{target_file}' 解析异常: {parse_err}")
                            
                painter.end()
                
                if images_drawn > 0:
                    preview_success = True
                    print(f"[DEBUG 预览 🚀] 视网膜高清阵列拼合成功！成功装载 {images_drawn} 个高级状态。")
                    
                    self.cursor_preview_lbl.setStyleSheet("""
                        QLabel {
                            background-color: rgba(255, 255, 255, 0.04);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 8px;
                        }
                    """)
                    self.cursor_preview_lbl.setPixmap(canvas)

        if not preview_success:
            self.cursor_preview_lbl.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px dashed rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    color: #777777;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
            self.cursor_preview_lbl.setText(f"🎨\n{selected_theme}\n[无标准素材]")


   # ================= 动态软件源核心管理区（超级 Debug 增强版） =================
    def scan_and_render_system_repos(self):
        """
        🔍 全动态清盘系统源：剥离一切状态锁，纯净平铺渲染
        """
        import os
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt

        if not self.repo_list_widget: return
        
        # 因为改成了 itemClicked 监听，这里清空和装载数据时绝对不会引发任何事件自扰
        self.repo_list_widget.clear()
        
        # 1. 强行置顶注入【虚拟源节点】：RPM Fusion 总闸
        has_fusion = os.path.exists("/etc/yum.repos.d/rpmfusion-free.repo")
        fusion_item = QListWidgetItem("📦 RPM Fusion 自由与非自由官方源合集\n[rpmfusion-all-bundle]")
        fusion_item.setData(Qt.UserRole, "SPECIAL_VIRTUAL_RPM_FUSION")
        fusion_item.setCheckState(Qt.Checked if has_fusion else Qt.Unchecked)
        self.repo_list_widget.addItem(fusion_item)

        # 2. 扫描底层真实的常规物理源
        repo_dir = "/etc/yum.repos.d"
        if os.path.exists(repo_dir): 
            for file_name in sorted(os.listdir(repo_dir)):
                if not file_name.endswith(".repo"): continue
                if file_name.startswith("rpmfusion-"): continue
                
                full_path = os.path.join(repo_dir, file_name)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    sections = re.split(r'^\[', content, flags=re.MULTILINE)
                    for section in sections:
                        if not section.strip(): continue
                        
                        id_match = re.match(r'^([^\]\n]+)\]', section)
                        if not id_match: continue
                        repo_id = id_match.group(1).strip()
                        
                        name_match = re.search(r'^\s*name\s*=\s*(.+)$', section, re.MULTILINE)
                        enabled_match = re.search(r'^\s*enabled\s*=\s*(.+)$', section, re.MULTILINE)
                        
                        repo_name = name_match.group(1).strip() if name_match else repo_id
                        is_enabled = False if (enabled_match and enabled_match.group(1).strip() in ["0", "false", "False"]) else True
                        
                        item = QListWidgetItem()
                        item.setText(f"{repo_name}\n[{repo_id}]")
                        item.setData(Qt.UserRole, repo_id)
                        item.setCheckState(Qt.Checked if is_enabled else Qt.Unchecked)
                        
                        self.repo_list_widget.addItem(item)
                except Exception as e:
                    print(f"[DEBUG 软件源 警告] 解析 {file_name} 发生轻微断层: {e}")

    def dispatch_repo_toggle_on_click(self, item):
        """
        ⚡ 物理级文本改写控制中心（彻底治愈冒号歧义、Polkit 连环命令拒绝与命令无效）
        """
        import os
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QMessageBox
        
        repo_id = item.data(Qt.UserRole)
        is_now_checked = (item.checkState() == Qt.Checked)
        action_word = "enable" if is_now_checked else "disable"
        target_val = "1" if is_now_checked else "0"
        
        print(f"\n==================== [🚀 HARDWARE LEVEL REPO WRITE] ====================")
        print(f"[⚙️ 目标] RepoID: {repo_id} | 动作: {action_word}")
        
        # 1. 🌟 虚拟源处理：多命令严格包装，完美治愈 127 授权错误
        if repo_id == "SPECIAL_VIRTUAL_RPM_FUSION":
            if is_now_checked:
                shell_script = "sh -c 'dnf5 install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-44.noarch.rpm && dnf5 update -y --refresh'"
            else:
                shell_script = "sh -c 'dnf5 remove -y rpmfusion-free-release rpmfusion-nonfree-release && rm -f /etc/yum.repos.d/rpmfusion-*.repo'"
            cmd = ["pkexec", "sh", "-c", shell_script]
            
        # 2. 🌟 常规源处理：物理级 sed 精准改写，彻底秒杀 dnf5 冒号 RepoID 无法识别卡死的顽疾
        else:
            # 暴力搜寻究竟是哪个 .repo 文件里装着这个 RepoID
            repo_dir = "/etc/yum.repos.d"
            target_repo_file = None
            
            if os.path.exists(repo_dir):
                for file_name in os.listdir(repo_dir):
                    if not file_name.endswith(".repo"): continue
                    file_path = os.path.join(repo_dir, file_name)
                    try:
                        with open(file_path, "r", errors="ignore") as f:
                            if f"[{repo_id}]" in f.read():
                                target_repo_file = file_path
                                break
                    except Exception: pass
            
            if not target_repo_file:
                QMessageBox.critical(self.window, "错误", f"在系统目录中找不到对应的源配置文件！")
                return
                
            print(f"[⚙️ 命中物理路径]: {target_repo_file}")
            
            # 现代化极其硬核的 sed 语法：匹配到 [repo_id] 后，在其下方范围内将 enabled=X 替换为最新状态
            # 如果该源原本没有显式写出 enabled=，则利用命令自动在块末尾补齐
            shell_script = f"""
            sed -i '/\\[{repo_id}\\]/,/^\\[/{{ /^[[:space:]]*enabled[[:space:]]*=/d }}' "{target_repo_file}"
            sed -i '/\\[{repo_id}\\]/a enabled={target_val}' "{target_repo_file}"
            """
            cmd = ["pkexec", "sh", "-c", shell_script]
            print(f"[⚙️ 执行物理改写指令]")

        try:
            self.repo_list_widget.setEnabled(False)
            QApplication.processEvents()
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_info = result.stderr.strip() or result.stdout.strip() or "授权被取消"
                raise RuntimeError(error_info)
            else:
                QMessageBox.information(self.window, "操作成功", f"软件源状态已同步写入系统底座！")
        except Exception as e:
            QMessageBox.critical(self.window, "改写失败", f"底层改写未完成:\n{e}")
        finally:
            self.repo_list_widget.setEnabled(True)
            # 满血刷盘自检
            self.scan_and_render_system_repos()
            print(f"========================================================================\n")

    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 🌟 破壁钢印：强行消除 Wayland 任务栏图标分离与快捷方式空转的鬼影问题
    app.setDesktopFileName("fedora-tweak-tool.desktop")
    
    tweak_app = FedoraTweakApp()
    tweak_app.window.show()
    sys.exit(app.exec())