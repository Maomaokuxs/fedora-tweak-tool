Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool
# 🌟 官方合规规范：必须明确声明 Source0
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 🌟 官方合规规范：使用最干净的 %autosetup 流
# rpkg 在打包时会自动将 Git 根目录压缩。这里让系统全自动解压并切入标准的构建工作区。
%autosetup -n %{name}-%{version}

%build
# 纯 Python 脚本，无需编译

%install
# 建立合规的虚拟系统根目录
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 🌟 官方合规规范：由于使用了标准的 %autosetup，此时解压出来的源码文件（app.py、main.ui）
# 就雷打不动地平铺在当前的当前工作目录下！直接用当前相对路径拷贝，绝对万无一失！
cp app.py %{buildroot}%{_bindir}/fedora-tweak-tool
chmod +x %{buildroot}%{_bindir}/fedora-tweak-tool

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
%{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 回归标准 %autosetup 构建流，彻底对齐 Copr 自动化解压目录，实现无损编译。
