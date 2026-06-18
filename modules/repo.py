import os
import re
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QApplication, QInputDialog, QLineEdit

class RepoManager:
    def __init__(self, app_ctx):
        self.ctx = app_ctx
        self.sudo_password = None
        print("[DEBUG 软件源] RepoManager 模块已挂载，大管家权限交接完毕。")

    def scan_and_render_system_repos(self):
        """🔍 全动态清盘系统源：双列表独立精细化渲染（注入动态宏滤网，消灭 $releasever）"""
        if not self.ctx.repo_list_widget: return
        self.ctx._is_loading_repos = True
        
        print("\n==================== [🔍 SYSTEM REPOS SCAN START] ====================")
        
        # 🌟 核心突破：前置嗅探当前系统的真实版本与架构，准备宏替换存根
        current_releasever = "44"  # 默认兜底版本
        current_basearch = "x86_64" # 默认兜底架构
        
        try:
            # 1. 嗅探真实的 releasever (Fedora 大版本号)
            ver_cmd = subprocess.run(["rpm", "-E", "%fedora"], capture_output=True, text=True)
            if ver_cmd.returncode == 0 and ver_cmd.stdout.strip():
                current_releasever = ver_cmd.stdout.strip()
            
            # 2. 嗅探真实的 basearch (CPU 基础架构)
            arch_cmd = subprocess.run(["rpm", "-E", "%_arch"], capture_output=True, text=True)
            if arch_cmd.returncode == 0 and arch_cmd.stdout.strip():
                current_basearch = arch_cmd.stdout.strip()
                
            print(f"[DEBUG 软件源] 成功捕获系统宏环境 -> $releasever={current_releasever} | $basearch={current_basearch}")
        except Exception as env_err:
            print(f"[DEBUG 软件源 警告] 嗅探系统宏环境失败，启用静态硬核兜底: {env_err}")

        # 🌟 1. 清空并纯净物理渲染【当前系统源列表】
        self.ctx.repo_list_widget.clear()
        repo_dir = "/etc/yum.repos.d"
        local_repo_count = 0
        
        if os.path.exists(repo_dir): 
            print(f"[DEBUG 软件源] 开始扫描本地物理路径: {repo_dir}")
            for file_name in sorted(os.listdir(repo_dir)):
                if not file_name.endswith(".repo"): continue
                
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
                        
                        # 🌟 核心拦截清洗：将原生文本里的恶心变量名，原地强行烫平为高清真实版本号
                        repo_name = repo_name.replace("$releasever", current_releasever)
                        repo_name = repo_name.replace("$basearch", current_basearch)
                        # 顺手把可能存在的复杂大括号变体也顺便洗掉
                        repo_name = repo_name.replace("${releasever}", current_releasever)
                        repo_name = repo_name.replace("${basearch}", current_basearch)
                        
                        is_enabled = False if (enabled_match and enabled_match.group(1).strip() in ["0", "false", "False"]) else True
                        
                        item = QListWidgetItem(f"{repo_name}\n[{repo_id}]")
                        item.setData(Qt.UserRole, repo_id)
                        item.setCheckState(Qt.Checked if is_enabled else Qt.Unchecked)
                        self.ctx.repo_list_widget.addItem(item)
                        local_repo_count += 1
                except Exception as e:
                    print(f"[DEBUG 软件源 警告] 解析 {file_name} 发生轻微断层: {e}")
        
        print(f"[DEBUG 软件源] 本地源扫描完毕，共挂载 {local_repo_count} 个物理仓库节点。")

        # 🌟 2. 清空并动态装填【推荐软件源列表】
        if self.ctx.recommended_repo_list:
            self.ctx.recommended_repo_list.clear()
            
            recommend_manifest = [
                ("📦 RPM Fusion 官方上游合集 (自由与非自由源)", "REC_RPM_FUSION", "/etc/yum.repos.d/rpmfusion-free.repo"),
                ("🌐 Google Chrome 官方Linux生产源", "REC_GOOGLE_CHROME", "/etc/yum.repos.d/google-chrome.repo"),
                ("💻 VSCode / Codium 微软官方开发源", "REC_VSCODE", "/etc/yum.repos.d/vscode.repo")
            ]
            
            print("[DEBUG 软件源] 开始盘点推荐生态源部署状态...")
            for label, rec_id, check_path in recommend_manifest:
                is_installed = os.path.exists(check_path)
                status_text = "已部署" if is_installed else "未部署"
                print(f"[DEBUG 软件源] 推荐源 [{rec_id}] 状态核查: {status_text}")
                
                rec_item = QListWidgetItem(label)
                rec_item.setData(Qt.UserRole, rec_id)
                rec_item.setCheckState(Qt.Checked if is_installed else Qt.Unchecked)
                self.ctx.recommended_repo_list.addItem(rec_item)

        self.ctx._is_loading_repos = False
        print("==================== [🔍 SYSTEM REPOS SCAN END] ====================\n")

    def verify_and_run_sudo(self, shell_script):
        """🔒 中央提权安全通道：利用 sudo -S 实现后台静默高能运转"""
        print(f"[DEBUG 提权通道] 准备静默下发提权指令...")
        
        if not self.sudo_password:
            print("[DEBUG 提权通道] 缓存令牌为空，拉起原生密码索要窗口。")
            passwd, ok = QInputDialog.getText(
                self.ctx.window, 
                "管理中心提权验证", 
                "🔐 正在尝试修改系统软件源，请输入 Root/Sudo 密码：", 
                QLineEdit.Password
            )
            if not ok or not passwd:
                print("[DEBUG 提权通道] 用户拒绝或取消了输入。")
                raise RuntimeError("用户取消了授权输入")
            self.sudo_password = passwd

        print(f"[DEBUG 提权通道] 令牌组装完毕，执行系统级 Shell: \n{shell_script}")
        full_cmd = f"echo '{self.sudo_password}' | sudo -S sh -c \"{shell_script}\""
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 and ("incorrect password" in result.stderr.lower() or "sorry" in result.stderr.lower()):
            print("[DEBUG 提权通道 致命] 密码校验失败，已销毁当前缓存令牌！")
            self.sudo_password = None
            raise RuntimeError("输入的密码错误，验证失败！")
            
        if result.returncode != 0:
            print(f"[DEBUG 提权通道 异常] 底层崩溃。回显 STDERR:\n{result.stderr.strip()}")
            raise RuntimeError(result.stderr.strip() or "底层 Shell 异常中断")
            
        print(f"[DEBUG 提权通道] 指令执行圆满成功！ReturnCode: 0")
        return result

    def dispatch_recommended_toggle_on_click(self, item):
        """⚡ 推荐软件源专属控制管线"""
        if getattr(self.ctx, "_is_loading_repos", False): return
        
        rec_id = item.data(Qt.UserRole)
        is_now_checked = (item.checkState() == Qt.Checked)
        action_word = "enable" if is_now_checked else "disable"
        
        print(f"\n==================== [🚀 RECOMMENDED REPO DEPLOY] ====================")
        print(f"[⚙️ 目标推荐源] 标识ID: {rec_id} | 动作指令: {action_word}")
        
        if rec_id == "REC_RPM_FUSION":
            if is_now_checked:
                shell_script = "dnf5 install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-44.noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-44.noarch.rpm && dnf5 update -y --refresh"
            else:
                shell_script = "dnf5 remove -y rpmfusion-free-release rpmfusion-nonfree-release && rm -f /etc/yum.repos.d/rpmfusion-*.repo"
        elif rec_id == "REC_GOOGLE_CHROME":
            if is_now_checked:
                shell_script = "dnf5 config-manager --set-enabled google-chrome || (echo -e '[google-chrome]\\nname=google-chrome\\nbaseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64\\nenabled=1\\ngpgcheck=1\\ngpgkey=https://dl.google.com/linux/linux_signing_key.pub' > /etc/yum.repos.d/google-chrome.repo)"
            else:
                shell_script = "rm -f /etc/yum.repos.d/google-chrome.repo"
        elif rec_id == "REC_VSCODE":
            if is_now_checked:
                # 🌟 核心修复：去掉了冗余的 sh -c 嵌套，并把 echo 内部的引号改为单引号，完美融入提权通道的双引号包围圈
                shell_script = "echo -e '[code]\\nname=Visual Studio Code\\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\\nenabled=1\\ngpgcheck=1\\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc' > /etc/yum.repos.d/vscode.repo"
            else:
                shell_script = "rm -f /etc/yum.repos.d/vscode.repo"
        else:
            print(f"[DEBUG 推荐源] 未知的推荐 ID: {rec_id}，中断放行。")
            return

        try:
            self.ctx.recommended_repo_list.setEnabled(False)
            QApplication.processEvents()
            self.verify_and_run_sudo(shell_script)
            QMessageBox.information(self.ctx.window, "提示", "配置成功")
        except Exception as e:
            item.setCheckState(Qt.Unchecked if is_now_checked else Qt.Checked)
            QMessageBox.critical(self.ctx.window, "改写失败", f"推荐源配置失败:\n{e}")
        finally:
            if self.ctx.recommended_repo_list: self.ctx.recommended_repo_list.setEnabled(True)
            self.scan_and_render_system_repos()
            print("========================================================================\n")

    def dispatch_repo_toggle_on_click(self, item):
        """⚡ 本地物理源专属控制管线（纯 Python 物理注入）"""
        if getattr(self.ctx, "_is_loading_repos", False): return
        
        repo_id = item.data(Qt.UserRole)
        is_now_checked = (item.checkState() == Qt.Checked)
        action_word = "enable" if is_now_checked else "disable"
        
        print(f"\n==================== [🚀 LOCAL HARDWARE REPO WRITE] ====================")
        print(f"[⚙️ 目标物理源] RepoID: {repo_id} | 动作: {action_word}")
        
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
            print(f"[DEBUG 物理源 错误] 遍历了 {repo_dir}，但找不到包含 [{repo_id}] 的配置文件！")
            QMessageBox.critical(self.ctx.window, "错误", f"在系统目录中找不到对应的源配置文件！")
            return
            
        print(f"[⚙️ 命中物理阵地]: {target_repo_file}")

        try:
            self.ctx.repo_list_widget.setEnabled(False)
            QApplication.processEvents()

            print(f"[DEBUG 物理源] 正在将目标文件读入内存沙盒...")
            with open(target_repo_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            new_lines = []
            inside_target_section = False
            enabled_line_written = False

            for line in lines:
                striped = line.strip()
                if striped.startswith("[") and striped.endswith("]"):
                    if inside_target_section and not enabled_line_written:
                        new_lines.append(f"enabled={'1' if is_now_checked else '0'}\n")
                        enabled_line_written = True
                    
                    if striped == f"[{repo_id}]":
                        inside_target_section = True
                        enabled_line_written = False
                    else:
                        inside_target_section = False

                if inside_target_section and striped.startswith("enabled"):
                    new_lines.append(f"enabled={'1' if is_now_checked else '0'}\n")
                    enabled_line_written = True
                    continue

                new_lines.append(line)

            if inside_target_section and not enabled_line_written:
                new_lines.append(f"enabled={'1' if is_now_checked else '0'}\n")

            sandbox_tmp = f"/tmp/tweak_repo_rewrite.tmp"
            with open(sandbox_tmp, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            print(f"[DEBUG 物理源] 内存重构完毕，已写入临时沙盒: {sandbox_tmp}")

            # 🌟 核心安全修正：覆盖系统配置文件后，强制校准所有权和权限位，防止 DNF 拒绝读取！
            shell_script = f"cp -f '{sandbox_tmp}' '{target_repo_file}' && chown root:root '{target_repo_file}' && chmod 644 '{target_repo_file}' && rm -f '{sandbox_tmp}'"
            self.verify_and_run_sudo(shell_script)
            
            QMessageBox.information(self.ctx.window, "提示", "配置成功")

        except Exception as e:
            item.setCheckState(Qt.Unchecked if is_now_checked else Qt.Checked)
            QMessageBox.critical(self.ctx.window, "改写失败", f"文件安全改写未完成:\n{e}")
            
        finally:
            self.ctx.repo_list_widget.setEnabled(True)
            self.scan_and_render_system_repos()
            print("========================================================================\n")