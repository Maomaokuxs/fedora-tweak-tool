Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool

# 告诉系统，源码就是 Git 自动归档过来的那套东西
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 🌟 核心修正 1：用最正统的 %setup 宏。
# -c 代表全自动创建并切入 fedora-tweak-tool-1.0.0 目录
# -T 代表我们手工接管解压，-D 代表不擦除目录
# 这是 Fedora 官方打包处理 Git 纯源码流的标准起手式
%setup -c -T -D

%build
# 纯 Python 脚本，无需编译

%install
# 建立合规的虚拟根目录系统
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 🌟 核心修正 2：利用 %{_sourcedir}。
# 因为在 rpkg 流中，克隆下来的原始文件雷打不动地躺在 %{_sourcedir} 里面！
# 无论沙箱怎么漂移，这两行拷贝绝对稳如老狗，直接命中！
cp %{_sourcedir}/app.py %{buildroot}%{_bindir}/fedora-tweak-tool
chmod +x %{buildroot}%{_bindir}/fedora-tweak-tool

cp %{_sourcedir}/main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

# 🌟 核心修正 3：规范化 echo 生成桌面图标，不多占构建目录的一丝资源
echo "[Desktop Entry]" > %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Type=Application" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Name=Fedora Tweak Tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Comment=简易时区修改与 GRUB2 主题智能全家桶安装工具" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Exec=fedora-tweak-tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Icon=system-run" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Terminal=false" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Categories=System;Settings;" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop

%files
# 严格盘点，多一个少一个都会在打包时报错
%{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 采用规范的 %setup 挂载与 %{_sourcedir} 变量对齐沙箱二进制环境。
