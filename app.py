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
        # 1. 🌟 智能自适应路径加载 UI 文件（完美适配 RPM 全局部署与本地 Git 调试）
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
        # 3. 绑定时区与 GRUB 各组件
        # =====================================================================
        self.combo = self.window.findChild(QComboBox, "timezone_combo")
        self.btn = self.window.findChild(QPushButton, "apply_btn")
        self.current_lbl = self.window.findChild(QLabel, "current_zone_lbl")

        self.current_grub_lbl = self.window.findChild(QLabel, "current_grub_lbl")
        self.grub_path_edit = self.window.findChild(QLineEdit, "grub_path_edit")
        self.grub_browse_btn = self.window.findChild(QPushButton, "grub_browse_btn")
        self.grub_apply_btn = self.window.findChild(QPushButton, "grub_apply_btn")

        # =====================================================================
        # 4. 初始化数据状态与信号事件绑定
        # =====================================================================
        self.init_timezone_list()
        self.refresh_current_timezone()
        self.refresh_current_grub_theme()  
        
        if self.btn: self.btn.clicked.connect(self.apply_timezone)
        if self.grub_browse_btn: self.grub_browse_btn.clicked.connect(self.smart_browse_grub)
        if self.grub_apply_btn: self.grub_apply_btn.clicked.connect(self.apply_grub_theme)

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

    # ================= 🌟 智能核心：GRUB 逻辑区 =================
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
            
            if self.current_grub_lbl:
                self.current_grub_lbl.setText(status_text)
        except Exception as e:
            print(f"[DEBUG GRUB 错误] 解析失败: {e}")

    def smart_browse_grub(self):
        print("[DEBUG 浏览] 打开智能文件选择器...")
        file_filters = (
            "所有支持的格式 (*.txt *.zip *.tar.gz *.tar.xz *.tgz);;"
            "主题配置文件 (theme.txt);;"
            "压缩档案 (*.zip *.tar.gz *.tar.xz *.tgz);;"
            "所有文件 (*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self.window,
            "选择 GRUB 主题 (支持 theme.txt 或 压缩包)",
            os.path.expanduser("~/Downloads"),
            file_filters
        )
        if file_path:
            print(f"[DEBUG 浏览] 用户锁定了路径: {file_path}")
            self.grub_path_edit.setText(file_path)
        else:
            print("[DEBUG 浏览] 用户取消了选择。")

    def apply_grub_theme(self):
        user_input_path = self.grub_path_edit.text().strip()
        print(f"\n[DEBUG 引擎 🚀] ========== 启动最新全家桶检测流水线 ==========")
        print(f"[DEBUG 引擎 🚀] 用户提交的目标路径: '{user_input_path}'")

        if not user_input_path:
            QMessageBox.warning(self.window, "提示", "请先选择一个 theme.txt 文件或主题压缩包！")
            return

        if not os.path.exists(user_input_path):
            QMessageBox.critical(self.window, "错误", "指定的文件在本地系统中不存在，请重新选择！")
            return

        sandbox_dir = "/tmp/grub_theme_sandbox"
        if os.path.exists(sandbox_dir):
            shutil.rmtree(sandbox_dir)
        os.makedirs(sandbox_dir, exist_ok=True)

        final_theme_dir_name = ""  
        final_source_dir = ""      

        try:
            if user_input_path.endswith(('.zip', '.tar.gz', '.tar.xz', '.tgz')):
                print("[DEBUG 引擎 🚀] 检测到压缩包，解压分析中...")
                
                if user_input_path.endswith('.zip'):
                    with zipfile.ZipFile(user_input_path, 'r') as z: z.extractall(sandbox_dir)
                elif user_input_path.endswith(('.tar.xz', '.xz')):
                    with tarfile.open(user_input_path, 'r:xz') as t: t.extractall(sandbox_dir)
                else:
                    with tarfile.open(user_input_path, 'r:gz') as t: t.extractall(sandbox_dir)

                detected_themes = {} 
                for root, dirs, files in os.walk(sandbox_dir):
                    if "theme.txt" in files:
                        current_theme_txt_path = os.path.join(root, "theme.txt")
                        current_theme_dir = os.path.dirname(current_theme_txt_path)
                        
                        pure_theme_name = os.path.basename(current_theme_dir) 
                        parent_dir_name = os.path.basename(os.path.dirname(current_theme_dir)) 
                        
                        display_name = f"{parent_dir_name} - {pure_theme_name}"
                        detected_themes[display_name] = current_theme_dir

                if not detected_themes:
                    raise ValueError("无效的主题包：压缩包内部未检索到 theme.txt 核心配置文件！")
                
                elif len(detected_themes) == 1:
                    display_name = list(detected_themes.keys())[0]
                    final_source_dir = detected_themes[display_name]
                    final_theme_dir_name = os.path.basename(final_source_dir)
                    print(f"[DEBUG 引擎 🚀] 仅发现单主题，跳过弹窗直接锁定: '{final_theme_dir_name}'")
                
                else:
                    print(f"[DEBUG 引擎 🚀] 成功锁定变体全家桶！检测到存在 {len(detected_themes)} 个分辨率版本。")
                    theme_options = sorted(list(detected_themes.keys()))
                    
                    chosen_theme, ok = QInputDialog.getItem(
                        self.window,
                        "检测到多个主题版本",
                        "当前压缩包内包含多个分辨率版本，请选择适合您显示器的款式：",
                        theme_options,
                        current=0,
                        editable=False
                    )
                    
                    if not ok or not chosen_theme:
                        print("[DEBUG 引擎 🚀] 用户取消选择，安全退出。")
                        if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)
                        return
                    
                    final_source_dir = detected_themes[chosen_theme]
                    pure_name = os.path.basename(final_source_dir)
                    resolution_suffix = os.path.basename(os.path.dirname(final_source_dir))
                    final_theme_dir_name = f"{pure_name}-{resolution_suffix}"
                    print(f"[DEBUG 引擎 🚀] 用户最终锁定了版本: {chosen_theme}")

            elif user_input_path.endswith('theme.txt'):
                print("[DEBUG 引擎 🚀] TXT直装模式")
                origin_source_dir = os.path.dirname(user_input_path)
                final_theme_dir_name = os.path.basename(origin_source_dir)
                temp_copy_target = os.path.join(sandbox_dir, final_theme_dir_name)
                shutil.copytree(origin_source_dir, temp_copy_target)
                final_source_dir = temp_copy_target

            else:
                raise ValueError("不支持的文件格式！请提供 theme.txt 或者压缩包。")

        except Exception as e:
            print(f"[DEBUG 引擎 🚀 崩溃] 预处理失败: {e}")
            QMessageBox.critical(self.window, "解析失败", str(e))
            if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)  
            return

        system_themes_root = "/usr/share/grub/themes"
        target_system_path = os.path.join(system_themes_root, final_theme_dir_name)
        target_theme_txt_absolute = os.path.join(target_system_path, "theme.txt")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"/etc/default/grub.bak.{timestamp}"

        shell_script = f"""
        mkdir -p "{system_themes_root}"
        cp -r "{final_source_dir}" "{target_system_path}"
        cp /etc/default/grub "{backup_file}" || exit 1
        sed -i '/^GRUB_THEME=/d' /etc/default/grub
        echo 'GRUB_THEME="{target_theme_txt_absolute}"' >> /etc/default/grub
        grub2-mkconfig -o /boot/grub2/grub.cfg
        """

        print("[DEBUG 提权 🚀] 唤起 pkexec...")
        cmd = ["pkexec", "sh", "-c", shell_script]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(f"[DEBUG 终端日志] 返回码: {result.returncode}")
            if result.stdout: print(f"[DEBUG stdout]\n{result.stdout.strip()}")
            if result.stderr: print(f"[DEBUG stderr]\n{result.stderr.strip()}")
            
            if result.returncode == 0:
                QMessageBox.information(self.window, "成功", f"主题【{final_theme_dir_name}】应用成功！")
                self.refresh_current_grub_theme()  
            else:
                QMessageBox.critical(self.window, "失败", f"执行失败: {result.stderr}")
        except Exception as e:
            QMessageBox.critical(self.window, "异常", f"执行遇到非预期崩溃: {str(e)}")
        finally:
            if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tweak_app = FedoraTweakApp()
    tweak_app.window.show()
    sys.exit(app.exec())
