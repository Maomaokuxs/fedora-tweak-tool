import sys
import subprocess
import os
import re
import zipfile
import tarfile
import shutil
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMessageBox, QComboBox, 
                               QPushButton, QLabel, QListWidget, QStackedWidget,
                               QLineEdit, QFileDialog, QInputDialog)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

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
        # 2. 绑定大框架联动
        # =====================================================================
        self.nav_list = self.window.findChild(QListWidget, "nav_list")
        self.content_stack = self.window.findChild(QStackedWidget, "content_stack")
        if self.nav_list and self.content_stack:
            self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
            self.nav_list.setCurrentRow(0) 

        # =====================================================================
        # 3. 绑定各组件（时区、GRUB）
        # =====================================================================
        self.combo = self.window.findChild(QComboBox, "timezone_combo")
        self.btn = self.window.findChild(QPushButton, "apply_btn")
        self.current_lbl = self.window.findChild(QLabel, "current_zone_lbl")

        self.current_grub_lbl = self.window.findChild(QLabel, "current_grub_lbl")
        self.grub_path_edit = self.window.findChild(QLineEdit, "grub_path_edit")
        self.grub_browse_btn = self.window.findChild(QPushButton, "grub_browse_btn")
        self.grub_apply_btn = self.window.findChild(QPushButton, "grub_apply_btn")
        self.grub_theme_combo = self.window.findChild(QComboBox, "grub_theme_combo")
        self.grub_refresh_btn = self.window.findChild(QPushButton, "grub_refresh_btn")

        # 显卡检测与驱动管理组件
        self.gpu_info_lbl = self.window.findChild(QLabel, "gpu_info_lbl")
        self.driver_status_lbl = self.window.findChild(QLabel, "driver_status_lbl")
        self.gpu_action_btn = self.window.findChild(QPushButton, "gpu_action_btn")

        # =====================================================================
        # 4. 初始化数据状态与信号事件绑定
        # =====================================================================
        self.system_themes_root = "/usr/share/grub/themes" 
        
        # 🌟 重新设计的硬件状态机标志位
        self.detected_vendor = "Unknown"  # "NVIDIA", "AMD", "Intel", "Unknown"
        self.nvidia_driver_installed = False
        self.vaapi_perfect = False       # 标记硬件加速是否已经处于完美状态
        
        self.init_timezone_list()
        self.refresh_current_timezone()
        self.refresh_current_grub_theme()  
        self.refresh_local_themes_combo() 
        
        # 启动时全自动主动探知本地显卡硬件与编解码状态
        self.detect_gpu_and_drivers()
        
        if self.btn: self.btn.clicked.connect(self.apply_timezone)
        if self.grub_browse_btn: self.grub_browse_btn.clicked.connect(self.smart_browse_grub)
        if self.grub_refresh_btn: self.grub_refresh_btn.clicked.connect(self.refresh_local_themes_combo)
        if self.grub_apply_btn: self.grub_apply_btn.clicked.connect(self.dispatch_grub_apply)
        if self.gpu_action_btn: self.gpu_action_btn.clicked.connect(self.apply_gpu_codec_fix)

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

    # ================= 🌟 智能核心：显卡与编解码全家桶检测 =================
    def detect_gpu_and_drivers(self):
        print("[DEBUG 硬件] 开始清点 PCI 巴士上的显卡硬件及硬件加速生态...")
        gpu_info_text = "未侦测到主流显卡"
        driver_status_text = "系统正处于基础渲染状态。"
        
        try:
            # 1. 探知 GPU 硬件（支持多显卡并存判定）
            result = subprocess.run(["lspci"], capture_output=True, text=True, check=True)
            lspci_out = result.stdout
            
            gpus = [line for line in lspci_out.splitlines() if "VGA compatible" in line or "3D controller" in line]
            
            if gpus:
                display_gpus = []
                # 设定主显卡优先级：NVIDIA -> AMD -> Intel
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

            # 2. 根据不同的显卡阵营，深度盘点多媒体多媒体格式支持状态
            if self.detected_vendor == "NVIDIA":
                if os.path.exists("/proc/driver/nvidia/version"):
                    self.nvidia_driver_installed = True
                    driver_status_text = "NVIDIA 官方闭源驱动：【 已正确加载 】\n"
                    
                    # 检查硬解桥接包
                    vaapi_check = subprocess.run(["rpm", "-q", "libva-nvidia-driver"], capture_output=True, text=True)
                    if vaapi_check.returncode == 0:
                        self.vaapi_perfect = True
                        driver_status_text += "多媒体编解码格式：【 H.264/H.265/NVENC 全格式硬解打通 】"
                    else:
                        driver_status_text += "⚠️ 编解码格式受限：缺少 VA-API 桥接包，高码率录屏可能导致 CPU 飙升！"
                else:
                    driver_status_text = "⚠️ 运行受限：检测到 NVIDIA 显卡，但正运行于开源驱动下。3D 性能极差且无硬件加速！"

            elif self.detected_vendor in ["AMD", "Intel"]:
                # 开源栈检查：看 freeworld 版的高级编解码驱动是否把官方阉割版给顶替掉了
                freeworld_check = subprocess.run(["rpm", "-q", "mesa-va-drivers-freeworld"], capture_output=True, text=True)
                if freeworld_check.returncode == 0:
                    self.vaapi_perfect = True
                    driver_status_text = f"{self.detected_vendor} 原生图形驱动：【 运行状态完美 】\n多媒体编解码格式：【 H.264 / H.265 专利全格式硬解已全激活 】"
                else:
                    driver_status_text = f"{self.detected_vendor} 原生图形驱动：【 运行状态良好 】\n⚠️ 编解码格式受限：Fedora 默认禁用了商业视频硬解，OBS 录屏及本地高码率播放体验较差！"

            # 3. 动态配置唯一的控制按钮
            if self.gpu_action_btn:
                if self.vaapi_perfect:
                    self.gpu_action_btn.setText("🎉 当前多媒体硬解加速已处于完美状态")
                    self.gpu_action_btn.setEnabled(False)
                else:
                    self.gpu_action_btn.setEnabled(True)
                    if self.detected_vendor == "NVIDIA":
                        if not self.nvidia_driver_installed:
                            self.gpu_action_btn.setText("一键安装 NVIDIA 闭源驱动 + 打通全格式硬解")
                        else:
                            self.gpu_action_btn.setText("一键打通 NVENC / OBS 录屏硬件加速通道")
                    elif self.detected_vendor in ["AMD", "Intel"]:
                        self.gpu_action_btn.setText(f"一键激活 {self.detected_vendor} 全格式多媒体视频硬解")
                    else:
                        self.gpu_action_btn.setText("未知硬件，无法配置加速")
                        self.gpu_action_btn.setEnabled(False)

        except Exception as e:
            gpu_info_text = "主动探知失败，系统 PCI 读取受阻。"
            print(f"[DEBUG 硬件 异常] {e}")

        if self.gpu_info_lbl: self.gpu_info_lbl.setText(gpu_info_text)
        if self.driver_status_lbl: self.driver_status_lbl.setText(driver_status_text)

    def apply_gpu_codec_fix(self):
        """
        核心分流多事务触发：一键交付 Polkit 与 DNF5，彻底解禁商业多媒体编码格式
        """
        if self.vaapi_perfect or self.detected_vendor == "Unknown": return

        # 🌟 事务流 1：NVIDIA 闭源全家桶一键整备
        if self.detected_vendor == "NVIDIA":
            if not self.nvidia_driver_installed:
                shell_script = """
                dnf5 config-manager --set-enabled fedora-cisco-openh264 || true
                dnf5 install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm || true
                dnf5 install -y https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-44.noarch.rpm || true
                dnf5 update -y --refresh
                dnf5 install -y akmod-nvidia xorg-x11-drv-nvidia-cuda libva-nvidia-driver nvidia-vaapi-driver
                """
                success_msg = "NVIDIA 闭源驱动与全格式硬解部署成功！请务必【重新启动电脑】以加载满血显卡模块！"
            else:
                shell_script = "dnf5 install -y libva-nvidia-driver nvidia-vaapi-driver gstreamer1-vaapi"
                success_msg = "NVIDIA VA-API 高速硬解通道打通成功！现在可以重启 OBS 享受丝滑录屏了！"

        # 🌟 事务流 2：AMD / Intel 开源多媒体全格式一键解禁
        elif self.detected_vendor in ["AMD", "Intel"]:
            print(f"[DEBUG 驱动] 正在为 {self.detected_vendor} 替换官方闭源硬解全家桶包...")
            
            # 引入 RPM Fusion 自由源 ➡️ 执行 DNF5 标志性的 swap 事务，用满血 freeworld 顶替官方阉割版
            shell_script = """
            dnf5 install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm || true
            dnf5 update -y --refresh
            dnf5 swap -y mesa-va-drivers mesa-va-drivers-freeworld
            dnf5 swap -y mesa-vdr-drivers mesa-vdr-drivers-freeworld
            dnf5 install -y gstreamer1-plugins-bad-freeworld gstreamer1-plugins-ugly-freeworld ffmpeg-free-devel
            """
            success_msg = f"🎉 恭喜！{self.detected_vendor} 开源全格式多媒体硬解加速已彻底激活！OBS 录屏与 4K 播放全面解锁底层硬件加速。"

        # 调起官方认证弹窗
        QMessageBox.information(self.window, "准备整备环境", "工具即将拉起官方 Polkit 授权。由于需要同步云端镜像站下载多媒体组件，请在输入密码后安心等候几分钟。")
        
        cmd = ["pkexec", "sh", "-c", shell_script]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"[DEBUG 终端返回码]: {result.returncode}")
            if result.returncode == 0:
                QMessageBox.information(self.window, "大获全胜", success_msg)
                self.detect_gpu_and_drivers() # 重新过检，将按钮当场灰掉
            else:
                QMessageBox.critical(self.window, "部署失败", f"DNF5 事务被系统拦截或由于网络原因中断:\n{result.stderr}")
        except Exception as e:
            QMessageBox.critical(self.window, "异常崩溃", f"执行显卡事务时遭遇未知挂起: {str(e)}")

    # ================= GRUB 逻辑区 =================
    def refresh_current_grub_theme(self):
        print("[DEBUG GRUB] 正在读取 /etc/default/grub 以分析当前生效主题...")
        if not os.path.exists("/etc/default/grub"):
            if self.current_grub_lbl: self.current_grub_lbl.setText("当前状态：未找到 GRUB 配置文件")
            return
        try:
            with open("/etc/default/grub", "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r'^\s*GRUB_THEME=["\' ]?([^"\'\n]+)["\' ]?', content, re.MULTILINE)
            if match:
                raw_path = match.group(1).strip()
                theme_name = os.path.basename(os.path.dirname(raw_path))
                status_text = f"当前正在使用的主题：【 {theme_name} 】"
                print(f"[DEBUG GRUB] 分析成功。当前主题: {theme_name} 完整路径: {raw_path}")
            else:
                status_text = "当前正在使用的主题：系统默认文字菜单 (未启用主题)"
                print("[DEBUG GRUB] 分析完毕：文件中未发现活动的 GRUB_THEME 变量。")
            if self.current_grub_lbl: self.current_grub_lbl.setText(status_text)
        except Exception as e:
            print(f"[DEBUG GRUB 错误] 解析失败: {e}")

    def refresh_local_themes_combo(self):
        if not self.grub_theme_combo: return
        self.grub_theme_combo.clear()
        if not os.path.exists(self.system_themes_root): return
        valid_themes = []
        try:
            for name in os.listdir(self.system_themes_root):
                full_path = os.path.join(self.system_themes_root, name)
                if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "theme.txt")):
                    valid_themes.append(name)
            valid_themes.sort()
            self.grub_theme_combo.addItems(valid_themes)
        except Exception as e: print(e)

    def dispatch_grub_apply(self):
        user_input_path = self.grub_path_edit.text().strip()
        if user_input_path: self.apply_grub_theme_archive(user_input_path)
        else: self.apply_local_grub_theme_switch()

    def apply_local_grub_theme_switch(self):
        if not self.grub_theme_combo or self.grub_theme_combo.currentIndex() == -1:
            QMessageBox.warning(self.window, "提示", "当前本地主题选单为空！")
            return
        selected_name = self.grub_theme_combo.currentText()
        target_theme_txt = os.path.join(self.system_themes_root, selected_name, "theme.txt")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/etc/default/grub.bak.{timestamp}"
        shell_script = f"""
        cp /etc/default/grub "{backup_file}" || exit 1
        sed -i '/^GRUB_THEME=/d' /etc/default/grub
        echo 'GRUB_THEME="{target_theme_txt}"' >> /etc/default/grub
        grub2-mkconfig -o /boot/grub2/grub.cfg
        """
        cmd = ["pkexec", "sh", "-c", shell_script]
        try:
            if subprocess.run(cmd, capture_output=True, text=True).returncode == 0:
                QMessageBox.information(self.window, "成功", f"成功切换本地已有主题：【{selected_name}】")
                self.refresh_current_grub_theme()
        except Exception as e: print(e)

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
            elif user_input_path.endswith(('.tar.xz', '.xz')):
                with tarfile.open(user_input_path, 'r:xz') as t: t.extractall(sandbox_dir)
            else:
                with tarfile.open(user_input_path, 'r:gz') as t: t.extractall(sandbox_dir)
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
        shell_script = f"""
        mkdir -p "{self.system_themes_root}"
        cp -r "{final_source_dir}" "{target_system_path}"
        sed -i '/^GRUB_THEME=/d' /etc/default/grub
        echo 'GRUB_THEME="{os.path.join(target_system_path, "theme.txt")}"' >> /etc/default/grub
        grub2-mkconfig -o /boot/grub2/grub.cfg
        """
        if subprocess.run(["pkexec", "sh", "-c", shell_script]).returncode == 0:
            QMessageBox.information(self.window, "成功", "外部主题安装应用成功！")
            self.refresh_current_grub_theme(); self.refresh_local_themes_combo(); self.grub_path_edit.clear()
        if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 🌟 专门针对 Wayland 环境的破壁代码：强行绑定任务栏图标！
    # 名字必须和我们在 /usr/share/applications/ 里创建的 .desktop 文件名一模一样
    app.setDesktopFileName("fedora-tweak-tool.desktop")
    
    tweak_app = FedoraTweakApp()
    tweak_app.window.show()
    sys.exit(app.exec())