{ pkgs }: {
  deps = [
    # Python环境
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.setuptools
    pkgs.python3Packages.wheel

    # LibreOffice和PDF依赖
    pkgs.libreoffice-fresh
    pkgs.python3Packages.uno

    # 字体配置和字体包
    pkgs.fontconfig
    pkgs.dejavu_fonts
    pkgs.liberation_ttf
    pkgs.noto-fonts
    pkgs.noto-fonts-cjk
    pkgs.noto-fonts-emoji

    # 虚拟显示和图形支持
    pkgs.xvfb-run
    pkgs.xorg.xorgserver
    pkgs.dbus

    # 系统工具
    pkgs.curl
    pkgs.wget
    pkgs.git
    pkgs.bash
    pkgs.coreutils
    pkgs.findutils
    pkgs.gnugrep
    pkgs.gnused

    # 数据库客户端
    pkgs.postgresql

    # 开发工具
    pkgs.gcc
    pkgs.pkg-config

    # 图像处理库（用于OCR等功能）
    pkgs.imagemagick
    pkgs.tesseract
    pkgs.poppler_utils
  ];
}
