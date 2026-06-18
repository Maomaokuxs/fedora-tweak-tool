import os
import re
import shutil
import tarfile
import zipfile
import subprocess
from PySide6.QtWidgets import QMessageBox, QFileDialog, QInputDialog

class GrubManager:
    def __init__(self, app_ctx):
        self.ctx = app_ctx
        self.system_themes_root = "/usr/share/grub/themes" 

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
            if self.ctx.current_grub_lbl: self.ctx.current_grub_lbl.setText(status_text)
        except Exception as e: print(e)

    def refresh_local_themes_combo(self):
        if not self.ctx.grub_theme_combo or not os.path.exists(self.system_themes_root): return
        valid_themes = []
        try:
            for name in os.listdir(self.system_themes_root):
                full_path = os.path.join(self.system_themes_root, name)
                if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "theme.txt")): valid_themes.append(name)
            valid_themes.sort()
            self.ctx.grub_theme_combo.clear()
            self.ctx.grub_theme_combo.addItems(valid_themes)
        except Exception as e: print(e)

    def dispatch_grub_apply(self):
        user_input_path = self.ctx.grub_path_edit.text().strip()
        if user_input_path: self.apply_grub_theme_archive(user_input_path)
        else: self.apply_local_grub_theme_switch()

    def apply_local_grub_theme_switch(self):
        if not self.ctx.grub_theme_combo or self.ctx.grub_theme_combo.currentIndex() == -1: return
        selected_name = self.ctx.grub_theme_combo.currentText()
        target_theme_txt = os.path.join(self.system_themes_root, selected_name, "theme.txt")
        shell_script = f"sed -i '/^GRUB_THEME=/d' /etc/default/grub && echo 'GRUB_THEME=\"{target_theme_txt}\"' >> /etc/default/grub && grub2-mkconfig -o /boot/grub2/grub.cfg"
        if subprocess.run(["pkexec", "sh", "-c", shell_script]).returncode == 0:
            QMessageBox.information(self.ctx.window, "成功", f"成功切换本地已有主题：【{selected_name}】")
            self.refresh_current_grub_theme()

    def smart_browse_grub(self):
        file_path, _ = QFileDialog.getOpenFileName(self.ctx.window, "选择 GRUB 主题", os.path.expanduser("~/Downloads"), "所有文件 (*)")
        if file_path: self.ctx.grub_path_edit.setText(file_path)

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
                chosen, ok = QInputDialog.getItem(self.ctx.window, "选择版本", "分辨率款式选择：", sorted(list(detected_themes.keys())), current=0, editable=False)
                if not ok: return
                final_source_dir = detected_themes[chosen]
            final_theme_dir_name = os.path.basename(final_source_dir)
        except Exception as e: QMessageBox.critical(self.ctx.window, "解析失败", str(e)); return

        target_system_path = os.path.join(self.system_themes_root, final_theme_dir_name)
        shell_script = f"mkdir -p \"{self.system_themes_root}\" && cp -r \"{final_source_dir}\" \"{target_system_path}\" && sed -i '/^GRUB_THEME=/d' /etc/default/grub && echo 'GRUB_THEME=\"{os.path.join(target_system_path, 'theme.txt')}\"' >> /etc/default/grub && grub2-mkconfig -o /boot/grub2/grub.cfg"
        if subprocess.run(["pkexec", "sh", "-c", shell_script]).returncode == 0:
            QMessageBox.information(self.ctx.window, "成功", "外部主题安装应用成功！")
            self.refresh_current_grub_theme(); self.refresh_local_themes_combo(); self.ctx.grub_path_edit.clear()
        if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)