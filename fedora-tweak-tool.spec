Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 回归标准的 %autosetup，配合 Copr 云端魔法宏全自动解压
%autosetup -n %{name}-%{version}

%build
# 🌟 核心进化 1：在编译构建阶段，强行在 app.py 的第一行插上 Shebang 蛇头
# 这样能100%%保证打包出来的文件绝对不会被系统误当成 Bash 脚本去啃！
sed -i '1i #!/usr/bin/python3' app.py

%install
# 建立合规的系统目录
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 拷贝核心文件
cp app.py %{buildroot}%{_bindir}/fedora-tweak-tool
cp main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

# 规范化定向输出桌面启动图标
echo "[Desktop Entry]" > %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Type=Application" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Name=Fedora Tweak Tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Comment=简易时区修改与 GRUB2 主题智能全家桶安装工具" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Exec=fedora-tweak-tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Icon=system-run" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Terminal=false" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Categories=System;Settings;" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop

%files
# 🌟 核心进化 2：使用 %%attr 魔法属性，强行指定安装后该文件的权限为 0755（可执行）
# 这样无论 Git 仓库里这个文件是什么权限，用户通过 DNF 安装完瞬间，它就自带灵魂！
%attr(0755, root, root) %{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 焊入 Shebang 蛇头并使用 %%attr(0755) 强切文件权限，实现到手一键即用完全体。
