import os
import re
import subprocess
from PySide6.QtWidgets import QMessageBox

class GpuManager:
    def __init__(self, app_ctx):
        self.ctx = app_ctx
        self.detected_vendor = "Unknown"  
        self.nvidia_driver_installed = False
        self.vaapi_perfect = False 

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

            if self.ctx.gpu_action_btn:
                if self.vaapi_perfect:
                    self.ctx.gpu_action_btn.setText("🎉 当前多媒体硬解加速已处于完美状态")
                    self.ctx.gpu_action_btn.setEnabled(False)
                else:
                    self.ctx.gpu_action_btn.setEnabled(True)
                    if self.detected_vendor == "NVIDIA":
                        if not self.nvidia_driver_installed: self.ctx.gpu_action_btn.setText("一键安装 NVIDIA 闭源驱动 + 打通全格式硬解")
                        else: self.ctx.gpu_action_btn.setText("一键打通 NVENC / OBS 录屏硬件加速通道")
                    elif self.detected_vendor in ["AMD", "Intel"]: self.ctx.gpu_action_btn.setText(f"一键激活 {self.detected_vendor} 全格式多媒体视频硬解")
                    else: self.ctx.gpu_action_btn.setEnabled(False)
        except Exception as e: print(e)

        if self.ctx.gpu_info_lbl: self.ctx.gpu_info_lbl.setText(gpu_info_text)
        if self.ctx.driver_status_lbl: self.ctx.driver_status_lbl.setText(driver_status_text)

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

        QMessageBox.information(self.ctx.window, "准备整备环境", "工具即将拉起官方 Polkit 授权，请安心等候。")
        cmd = ["pkexec", "sh", "-c", shell_script]
        try:
            if subprocess.run(cmd, capture_output=True, text=True).returncode == 0:
                QMessageBox.information(self.ctx.window, "大获全胜", success_msg)
                self.detect_gpu_and_drivers()
        except Exception as e: print(e)