import subprocess
from PySide6.QtWidgets import QMessageBox

class TimezoneManager:
    def __init__(self, app_ctx):
        self.ctx = app_ctx
        print("[DEBUG 时区] TimezoneManager 挂载成功。")

    def init_timezone_list(self):
        if not self.ctx.combo: return
        try:
            print("[DEBUG 时区] 开始向系统索要全球合法时区清单...")
            result = subprocess.run(["timedatectl", "list-timezones"], capture_output=True, text=True, check=True)
            all_zones = [zone.strip() for zone in result.stdout.split("\n") if zone.strip()]
            self.ctx.combo.clear() # 前置清空，防止冷热启动重叠
            self.ctx.combo.addItems(all_zones)
            print(f"[DEBUG 时区] 全球时区装填完毕，共加载 {len(all_zones)} 个时区节点。")
        except Exception as e:
            print(f"[DEBUG 时区 警告] 索要清单失败，启用静态安全备份: {e}")
            self.ctx.combo.addItems(["Asia/Shanghai", "UTC"])

    def refresh_current_timezone(self):
        """🌟 核心进化：实现标签文本与下拉框指针的双重联动校准"""
        try:
            result = subprocess.run(["timedatectl", "show", "--property=Timezone", "--value"], capture_output=True, text=True, check=True)
            current_zone = result.stdout.strip()
            print(f"[DEBUG 时区] 探测到系统当前真实时区为: '{current_zone}'")
            
            # 1. 刷新文本标签呈现
            if self.ctx.current_lbl: 
                self.ctx.current_lbl.setText(current_zone)
                
            # 2. 🌟 核心突破：强行让下拉框高亮选中当前时区
            if self.ctx.combo:
                index = self.ctx.combo.findText(current_zone)
                if index != -1:
                    self.ctx.combo.setCurrentIndex(index)
                    print(f"[DEBUG 时区 🚀] 下拉框指针已精准同步拨动至第 {index} 项 ({current_zone})")
                else:
                    print(f"[DEBUG 时区 警告] 下拉框选项中竟然找不到当前时区 '{current_zone}'！")
        except Exception as e:
            print(f"[DEBUG 时区 错误] 获取或同步当前时区失败: {e}")

    def apply_timezone(self):
        if not self.ctx.combo: return
        target_zone = self.ctx.combo.currentText()
        print(f"[DEBUG 时区] 用户触发时区变更 -> 准备写入: {target_zone}")
        
        cmd = ["pkexec", "timedatectl", "set-timezone", target_zone]
        try:
            if subprocess.run(cmd).returncode == 0:
                QMessageBox.information(self.ctx.window, "提示", "配置成功")
                # 满血自我热刷新，再次重组同步率
                self.refresh_current_timezone()
            else:
                print("[DEBUG 时区] 提权写入被系统或用户拦截拒绝。")
        except Exception as e: 
            print(f"[DEBUG 时区 致命] 写入执行发生物理崩溃: {e}")