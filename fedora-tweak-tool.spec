Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool
# 🌟 核心修改 1：删掉原本的 https 下载链接，改用本地源码声明
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 🌟 核心修改 2：告诉构建器，不要尝试去跨目录解压，因为 Git 已经把源码拉到当前开发目录里了
# -c 代表在解压前先创建目录，-T 代表禁止全自动默认解压行为
%setup -q -c -T

%build
# 纯 Python 脚本，不需要编译

%install
# 🌟 核心修改 3：因为 Git 把源码拉到了上层工作区，我们直接去上层工作区（_builddir/..）拷贝文件
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 从 Git 克隆的真实根目录下拿取文件
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
- 切换到现代化 Git SCM 直取源码流打包，彻底告别 Source0 404 网络依赖。
