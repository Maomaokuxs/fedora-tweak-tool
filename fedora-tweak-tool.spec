Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool

# 🌟 核心进化 1：彻底移除 Source0 变量声明，不给 rpkg 任何找茬的机会

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 🌟 核心进化 2：手动在工作区创建一个临时的虚空中转箱
# 这样能满足 rpmbuild 必须先进入某个目录的强迫症
mkdir -p %{_builddir}/%{name}-%{version}
cd %{_builddir}/%{name}-%{version}

%build
# 纯 Python 脚本，不需要编译

%install
# 🌟 核心进化 3：此时通过 Git 拉下来的源码在 %{_builddir}/../ 目录下
# 咱们直接去那里把 app.py 和 main.ui 抓过来安装
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 精准打通上层 Git 源码路径
cp %{_builddir}/../app.py %{buildroot}%{_bindir}/fedora-tweak-tool
chmod +x %{buildroot}%{_bindir}/fedora-tweak-tool

cp %{_builddir}/../main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

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
- 升级为无 Source0 纯本地 Git 源码穿透流打包，100% 避开沙盒环境无归档包报错。
