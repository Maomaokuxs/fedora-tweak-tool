Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool
Source0:        https://github.com/Maomaokuxs/fedora-tweak-tool/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
# 运行所需的系统依赖，DNF 安装时会自动补齐
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 解压源码包，GitHub 默认生成的目录名是 仓库名-版本号（带v）
%setup -q -n fedora-tweak-tool-1.0.0

%build
# 纯 Python 脚本，不需要编译阶段

%install
# 1. 创建符合 FHS 规范的系统目录
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 2. 安装核心脚本到 /usr/bin 并赋予可执行权限
cp app.py %{buildroot}%{_bindir}/fedora-tweak-tool
chmod +x %{buildroot}%{_bindir}/fedora-tweak-tool

# 3. 将 main.ui 安装到 /usr/share/fedora-tweak-tool 目录下
cp main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

# 4. 动态生成一个桌面快捷菜单启动图标（.desktop 文件）
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
# 明确声明这个 RPM 包所拥有的全部文件所有权
%{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 智能全家桶版本首次打包，支持系统时区调节与 .tar.xz/.zip GRUB 主题无损同步编译，内置桌面图标。
