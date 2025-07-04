{ pkgs }: {
  deps = [
    # Python环境 - 项目核心运行环境
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.setuptools
    pkgs.python3Packages.wheel

    # LibreOffice - Word转PDF核心依赖
    pkgs.libreoffice-fresh

    # 字体支持 - 中英文文档渲染必需
    pkgs.fontconfig
    pkgs.dejavu_fonts
    pkgs.liberation_ttf
    pkgs.noto-fonts
    pkgs.noto-fonts-cjk-sans
    pkgs.noto-fonts-cjk-serif

    # 虚拟显示 - LibreOffice headless模式必需
    pkgs.xvfb-run

    # 图像处理 - OCR和图片处理
    pkgs.imagemagick
    pkgs.tesseract4

    # PDF工具 - PDF处理和转换
    pkgs.poppler-utils

    # 系统工具 - 基础命令
    pkgs.curl
    pkgs.wget
    pkgs.git
    pkgs.bash
    pkgs.coreutils
    pkgs.findutils
    pkgs.gnugrep
    pkgs.gnused

    # 数据库 - PostgreSQL支持
    pkgs.postgresql

    # 编译工具 - Python包编译需要
    pkgs.gcc
    pkgs.pkg-config

    # 文件类型检测 - python-magic依赖
    pkgs.file

    # 网络工具 - API调用和下载
    pkgs.openssl
    pkgs.ca-certificates
  ];
}
