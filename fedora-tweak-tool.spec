Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 🌟 降维打击 1：不进行任何常规解压，直接在云端当前的 Git 根目录就地展开
%setup -c -T

%build
# 纯 Python 脚本，不需要编译

%install
# 创建规范的系统目录
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 🌟 降维打击 2：利用 rpkg 动态环境变量 %{_sourcedir} 
# 无论 Copr 的沙箱怎么重定向，这个变量永远能100%精准定位到随 Git 一起拉下来的原始 app.py 和 main.ui！
cp %{_sourcedir}/app.py %{buildroot}%{_bindir}/fedora-tweak-tool
chmod +x %{buildroot}%{_bindir}/fedora-tweak-tool

cp %{_sourcedir}/main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

# 动态生成桌面快捷菜单启动图标
cat << 'EOF' > %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
[Desktop Entry]
Type=Application
Name=Fedora Tweak Tool
Comment=简易时区修改与 GRUB2 主题智能全家桶安装工具
Exec=fedora-tweak-tool
Icon=system-run
Terminal=false
Categories=System;Settings;
EOF

%files
%{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 使用 %{_sourcedir} 动态环境变量重构，彻底解决 Chroot 真实环境下的路径丢失问题。
