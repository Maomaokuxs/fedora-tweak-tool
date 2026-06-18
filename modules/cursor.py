import os
import re
import shutil
import struct
import tarfile
import zipfile
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtWidgets import QMessageBox, QFileDialog

class CursorManager:
    def __init__(self, app_ctx):
        self.ctx = app_ctx

    def refresh_cursor_themes_combo(self):
        if not self.ctx.cursor_theme_combo: return
        self.ctx.cursor_theme_combo.clear()
        
        search_paths = [
            os.path.expanduser("~/.icons"),              
            os.path.expanduser("~/.local/share/icons"),  
            "/usr/share/icons"                            
        ]
        
        valid_themes = []
        for path in search_paths:
            if not os.path.exists(path): continue
            try:
                for name in os.listdir(path):
                    if name == "default": continue  
                    full_path = os.path.join(path, name)
                    if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, "cursors")):
                        if name not in valid_themes: valid_themes.append(name)
            except Exception as e: print(e)
                
        valid_themes.sort()
        self.ctx.cursor_theme_combo.addItems(valid_themes)
        print(f"[DEBUG 鼠标] 成功装载 {len(valid_themes)} 个可用的光标主题。")
        
        try:
            result = subprocess.run(
                ["kreadconfig6", "--file", "kcminputrc", "--group", "Mouse", "--key", "cursorTheme"], 
                capture_output=True, text=True, check=True
            )
            true_theme = result.stdout.strip()
            print(f"[DEBUG 鼠标联动 🚀] KDE 6 核心层返回的当前真实鼠标主题为: '{true_theme}'")
            
            if true_theme:
                index = self.ctx.cursor_theme_combo.findText(true_theme)
                if index == -1:
                    for i in range(self.ctx.cursor_theme_combo.count()):
                        if self.ctx.cursor_theme_combo.itemText(i).lower() == true_theme.lower():
                            index = i
                            break
                if index != -1:
                    self.ctx.cursor_theme_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"[DEBUG 鼠标抓取 失败] 无法通过 kreadconfig6 捕获状态: {e}")

    def smart_browse_cursor(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.ctx.window, "选择鼠标主题压缩包", os.path.expanduser("~/Downloads"), "鼠标包 (*.tar.gz *.tar.xz *.zip *.tgz)"
        )
        if file_path: self.ctx.cursor_path_edit.setText(file_path)

    def dispatch_cursor_apply(self):
        user_input_path = self.ctx.cursor_path_edit.text().strip() if self.ctx.cursor_path_edit else ""

        if user_input_path:
            if not os.path.exists(user_input_path):
                QMessageBox.critical(self.ctx.window, "错误", "指定的压缩包路径不存在！")
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

                target_theme_source_dir = None
                for root, dirs, files in os.walk(sandbox_dir):
                    if "cursors" in dirs:
                        target_theme_source_dir = root
                        break

                if not target_theme_source_dir:
                    raise ValueError("未在包内找到包含 'cursors' 的合规鼠标主题文件夹！")

                theme_dir_name = os.path.basename(target_theme_source_dir)
                user_icons_root = os.path.expanduser("~/.local/share/icons")
                target_deploy_path = os.path.join(user_icons_root, theme_dir_name)

                os.makedirs(user_icons_root, exist_ok=True)
                if os.path.exists(target_deploy_path): shutil.rmtree(target_deploy_path)
                shutil.copytree(target_theme_source_dir, target_deploy_path)
                self.execute_cursor_apply_core(theme_dir_name)
                self.refresh_cursor_themes_combo()
                
                if self.ctx.cursor_theme_combo:
                    idx = self.ctx.cursor_theme_combo.findText(theme_dir_name)
                    if idx != -1: self.ctx.cursor_theme_combo.setCurrentIndex(idx)

                if self.ctx.cursor_path_edit: self.ctx.cursor_path_edit.clear()
                self.update_cursor_preview()
                QMessageBox.information(self.ctx.window, "成功", f"外部鼠标主题 【{theme_dir_name}】 导入并应用成功！")
            except Exception as e:
                QMessageBox.critical(self.ctx.window, "导入失败", str(e))
            finally:
                if os.path.exists(sandbox_dir): shutil.rmtree(sandbox_dir)
        else:
            if not self.ctx.cursor_theme_combo or self.ctx.cursor_theme_combo.currentIndex() == -1:
                QMessageBox.warning(self.ctx.window, "提示", "请选择本地鼠标主题，或导入外部压缩包！")
                return
            target_theme = self.ctx.cursor_theme_combo.currentText()
            try:
                self.execute_cursor_apply_core(target_theme)
                self.update_cursor_preview()
                QMessageBox.information(self.ctx.window, "切换成功", f"鼠标主题已成功切换为 【{target_theme}】！")
            except Exception as e:
                QMessageBox.critical(self.ctx.window, "失败", str(e))
    
    def execute_cursor_apply_core(self, theme_name):
        user_icons_dir = os.path.expanduser("~/.local/share/icons")
        default_theme_dir = os.path.join(user_icons_dir, "default")
        os.makedirs(default_theme_dir, exist_ok=True)
        
        with open(os.path.join(default_theme_dir, "index.theme"), "w", encoding="utf-8") as f:
            f.write(f"[Icon Theme]\nName=Default\nComment=Default Cursor Theme\nInherits={theme_name}\n")

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

        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "cursor-theme", theme_name], capture_output=True)

        if shutil.which("plasma-apply-cursortheme"):
            subprocess.run(["plasma-apply-cursortheme", theme_name], capture_output=True)

    def update_cursor_preview(self):
        if not self.ctx.cursor_theme_combo or not self.ctx.cursor_preview_lbl: return
        selected_theme = self.ctx.cursor_theme_combo.currentText()
        if not selected_theme: 
            self.ctx.cursor_preview_lbl.setText("暂无预览")
            return
            
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
        
        canvas = QPixmap(128, 128)
        canvas.fill(Qt.transparent)
        preview_success = False

        if theme_path:
            cursors_dir = os.path.join(theme_path, "cursors")
            if os.path.exists(cursors_dir) and os.path.isdir(cursors_dir):
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
                                
                            with open(real_path, "rb") as f: data = f.read()
                                
                            if data[:4] == b"Xcur":
                                ntoc = struct.unpack("<I", data[8:12])[0]
                                img_offset = None
                                pos = 16
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
                    self.ctx.cursor_preview_lbl.setStyleSheet("""
                        QLabel {
                            background-color: rgba(255, 255, 255, 0.04);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 8px;
                        }
                    """)
                    self.ctx.cursor_preview_lbl.setPixmap(canvas)

        if not preview_success:
            self.ctx.cursor_preview_lbl.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px dashed rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    color: #777777;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
            self.ctx.cursor_preview_lbl.setText(f"🎨\n{selected_theme}\n[无标准素材]")