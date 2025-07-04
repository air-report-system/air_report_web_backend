{ pkgs }: {
  deps = [
    # 基础环境
    pkgs.python3
    pkgs.curl
    pkgs.wget
    pkgs.git

    # LibreOffice - 已验证可用
    pkgs.libreoffice

    # 字体支持 - 已验证可用
    pkgs.fontconfig
    pkgs.dejavu_fonts

    # 图像处理
    pkgs.imagemagick

    # OCR支持
    pkgs.tesseract

    # PDF工具 - 使用下划线版本
    pkgs.poppler_utils
  ];
}
