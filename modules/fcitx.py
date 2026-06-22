import os
import re
import shutil
import tarfile
import zipfile
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QFileDialog

class FcitxManager:
    def __init__(self, app_ctx):
        self.ctx = app_ctx
        self.config_path = os.path.expanduser("~/.config/fcitx5/conf/classicui.conf")
        self.user_themes = os.path.expanduser("~/.local/share/fcitx5/themes")
        self.sys_themes = "/usr/share/fcitx5/themes"

    # ── public api ──────────────────────────────────────────────

    def refresh_current_theme(self):
        cfg = self._read_config()
        if not self.ctx.fcitx_current_theme_lbl:
            return
        light = cfg.get("Theme", "默认")
        dark = cfg.get("DarkTheme", "默认")
        auto = cfg.get("UseDarkTheme", "False")
        status = f"浅色主题：【{light}】  深色主题：【{dark}】"
        if auto == "True":
            status += "  ⚡ 自动切换已开启"
        self.ctx.fcitx_current_theme_lbl.setText(status)

    def refresh_theme_combos(self):
        themes = self._scan_themes()
        cfg = self._read_config()
        for combo_name, key in [("fcitx_theme_combo", "Theme"),
                                ("fcitx_dark_theme_combo", "DarkTheme")]:
            combo = getattr(self.ctx, combo_name, None)
            if not combo:
                continue
            combo.clear()
            combo.addItems(themes)
            current = cfg.get(key)
            if current:
                idx = combo.findText(current)
                if idx != -1:
                    combo.setCurrentIndex(idx)
        check = self.ctx.fcitx_auto_switch_check
        if check:
            check.setChecked(cfg.get("UseDarkTheme", "False") == "True")

    def smart_browse_theme(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.ctx.window, "选择 Fcitx5 主题压缩包",
            os.path.expanduser("~/Downloads"),
            "主题包 (*.tar.gz *.tar.xz *.zip *.tgz)"
        )
        if file_path:
            self.ctx.fcitx_path_edit.setText(file_path)

    def dispatch_apply(self):
        user_path = self.ctx.fcitx_path_edit.text().strip() if self.ctx.fcitx_path_edit else ""

        if user_path:
            if not os.path.exists(user_path):
                QMessageBox.critical(self.ctx.window, "错误", "指定的压缩包路径不存在！")
                return
            self._import_from_archive(user_path)
        else:
            light = self.ctx.fcitx_theme_combo.currentText() if self.ctx.fcitx_theme_combo else ""
            dark = self.ctx.fcitx_dark_theme_combo.currentText() if self.ctx.fcitx_dark_theme_combo else ""
            auto = self.ctx.fcitx_auto_switch_check.isChecked() if self.ctx.fcitx_auto_switch_check else False
            if not light and not dark:
                QMessageBox.warning(self.ctx.window, "提示", "请至少选择一个主题！")
                return
            self._apply_config(light, dark, auto)

    # ── config read / write ─────────────────────────────────────

    def _read_config(self):
        cfg = {}
        if not os.path.exists(self.config_path):
            return cfg
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^\s*(Theme|DarkTheme|UseDarkTheme)\s*=\s*(.+)\s*$', line)
                    if m:
                        cfg[m.group(1)] = m.group(2).strip()
        except Exception:
            pass
        return cfg

    def _apply_config(self, light_theme, dark_theme, auto_switch):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            lines = []
            keys_written = set()
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            new_lines = []
            for line in lines:
                stripped = line.strip()
                m = re.match(r'^\s*(Theme|DarkTheme|UseDarkTheme)\s*=', stripped)
                if m:
                    key = m.group(1)
                    if key not in keys_written:
                        if key == "Theme" and light_theme:
                            new_lines.append(f"Theme={light_theme}\n")
                        elif key == "DarkTheme" and dark_theme:
                            new_lines.append(f"DarkTheme={dark_theme}\n")
                        elif key == "UseDarkTheme":
                            new_lines.append(f"UseDarkTheme={'True' if auto_switch else 'False'}\n")
                        else:
                            new_lines.append(line)
                        keys_written.add(key)
                    continue
                new_lines.append(line)
            if "Theme" not in keys_written and light_theme:
                new_lines.append(f"Theme={light_theme}\n")
            if "DarkTheme" not in keys_written and dark_theme:
                new_lines.append(f"DarkTheme={dark_theme}\n")
            if "UseDarkTheme" not in keys_written:
                new_lines.append(f"UseDarkTheme={'True' if auto_switch else 'False'}\n")
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            subprocess.run(["fcitx5-remote", "-r"], capture_output=True)
            self.refresh_current_theme()
            self.refresh_theme_combos()
            QMessageBox.information(self.ctx.window, "成功", "输入法主题配置已应用")
        except Exception as e:
            QMessageBox.critical(self.ctx.window, "失败", f"应用配置失败：{e}")

    # ── theme scanning ──────────────────────────────────────────

    def _scan_themes(self):
        themes = []
        for root in [self.user_themes, self.sys_themes]:
            if not os.path.exists(root):
                continue
            try:
                for name in os.listdir(root):
                    theme_dir = os.path.join(root, name)
                    if os.path.isdir(theme_dir) and os.path.exists(os.path.join(theme_dir, "theme.conf")):
                        if name not in themes:
                            themes.append(name)
            except Exception:
                pass
        themes.sort(key=str.lower)
        return themes

    # ── archive import ──────────────────────────────────────────

    def _import_from_archive(self, archive_path):
        sandbox = "/tmp/fcitx_theme_sandbox"
        if os.path.exists(sandbox):
            shutil.rmtree(sandbox)
        os.makedirs(sandbox, exist_ok=True)
        try:
            if archive_path.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as z:
                    z.extractall(sandbox)
            elif archive_path.endswith((".tar.xz", ".xz")):
                with tarfile.open(archive_path, "r:xz") as t:
                    t.extractall(sandbox)
            else:
                with tarfile.open(archive_path, "r:gz") as t:
                    t.extractall(sandbox)
            theme_dir = None
            for root, dirs, files in os.walk(sandbox):
                if "theme.conf" in files:
                    theme_dir = root
                    break
            if not theme_dir:
                raise ValueError("压缩包内未找到包含 theme.conf 的有效 Fcitx5 主题！")
            theme_name = os.path.basename(theme_dir)
            target = os.path.join(self.user_themes, theme_name)
            os.makedirs(self.user_themes, exist_ok=True)
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(theme_dir, target)
            self._apply_config(theme_name, theme_name, False)
        except Exception as e:
            QMessageBox.critical(self.ctx.window, "导入失败", str(e))
        finally:
            if os.path.exists(sandbox):
                shutil.rmtree(sandbox)
