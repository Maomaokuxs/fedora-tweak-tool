Name:           fedora-tweak-tool
Version:        1.1.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool

# Copr 官方 rpkg 魔法宏
Source0:        {{{ git_dir_pack }}}

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools
Requires:       pciutils

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
针对多分辨率变体全家桶的 GRUB2 主题智能解压、安全备份与双模切换，
以及涵盖 NVIDIA/AMD/Intel 的全显卡多媒体硬件加速智能探知与一键修复引擎。

%prep
# 配合打包宏，全自动解压铺平目录
{{{ git_dir_setup_macro }}}

%build
# 强制塞入 Python 蛇头，防止被误认为 Bash 脚本
sed -i '1i #!/usr/bin/python3' app.py

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 畅通无阻的平铺拷贝
cp app.py %{buildroot}%{_bindir}/fedora-tweak-tool
cp main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

# 规范化定向输出桌面启动图标
echo "[Desktop Entry]" > %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Type=Application" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Name=Fedora Tweak Tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Comment=简易时区修改、GRUB2 智能主题全家桶与显卡加速配置" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Exec=fedora-tweak-tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Icon=system-run" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Terminal=false" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Categories=System;Settings;" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
# 🌟 彻底消灭鬼影窗口的双保险
echo "StartupNotify=true" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "StartupWMClass=fedora-tweak-tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop

%files
# 无视 Git 原生权限，落地强制赋予 0755
%attr(0755, root, root) %{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.1.1-1
- 尝试修复快捷方式与窗口管理的断层

* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.1.0-1
- 【重磅】新增显卡硬件加速智能面板，支持探知 Intel/AMD/NVIDIA 显卡并一键部署 RPM Fusion 满血编解码环境。
- 【重磅】合并 GRUB 主题应用按钮，支持“外部解压安装”与“本地已存主题一键切换”双模智能调度。
- 引入 pciutils 依赖以支持底层硬件扫描。

* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 初始版本发布，支持基本的时区修改与外部 GRUB 主题去重安装，修复文件权限与 Copr 打包流。
