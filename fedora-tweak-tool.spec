Name:           fedora-tweak-tool
Version:        1.0.0
Release:        1%{?dist}
Summary:        基于 PySide6 的简易 Fedora 系统调节工具

License:        GPLv3+
URL:            https://github.com/Maomaokuxs/fedora-tweak-tool

# 🌟 必须保留的功臣：Copr 官方 rpkg 魔法宏，解决找不到源码包的问题
Source0:        {{{ git_dir_pack }}}

BuildArch:      noarch
Requires:       python3-pyside6
Requires:       polkit
Requires:       grub2-tools

%description
一个为 Fedora 打造的系统调节工具，目前支持免核心破坏的系统时区修改，
以及针对多分辨率、重名变体全家桶的 GRUB2 主题智能解压、安全备份与自动编译。

%prep
# 🌟 必须保留的功臣：配合打包宏，全自动解压铺平目录
{{{ git_dir_setup_macro }}}

%build
# 🌟 权限补丁 1：强制塞入 Python 蛇头
sed -i '1i #!/usr/bin/python3' app.py

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/fedora-tweak-tool
mkdir -p %{buildroot}%{_datadir}/applications

# 畅通无阻的平铺拷贝
cp app.py %{buildroot}%{_bindir}/fedora-tweak-tool
cp main.ui %{buildroot}%{_datadir}/fedora-tweak-tool/main.ui

# 桌面图标
echo "[Desktop Entry]" > %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Type=Application" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Name=Fedora Tweak Tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Comment=简易时区修改与 GRUB2 主题智能全家桶安装工具" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Exec=fedora-tweak-tool" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Icon=system-run" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Terminal=false" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop
echo "Categories=System;Settings;" >> %{buildroot}%{_datadir}/applications/fedora-tweak-tool.desktop

%files
# 🌟 权限补丁 2：无视 Git 原生权限，落地强制赋予 0755
%attr(0755, root, root) %{_bindir}/fedora-tweak-tool
%{_datadir}/fedora-tweak-tool/main.ui
%{_datadir}/applications/fedora-tweak-tool.desktop

%changelog
* Tue Jun 16 2026 biyuan <biyuan@fedoraproject.org> - 1.0.0-1
- 合并 rpkg 魔法宏与 attr 权限覆盖，实现最终一键可用。
