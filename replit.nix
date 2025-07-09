{ pkgs }: {
  deps = [
    # 基础环境
    pkgs.python3
    pkgs.curl
    pkgs.wget
    pkgs.git

    # Redis - WebSocket 和 Celery 支持
    pkgs.redis

    # LibreOffice - 已验证可用
    pkgs.libreoffice

    # 字体支持 - 已验证可用
    pkgs.fontconfig
    pkgs.dejavu_fonts
    
    # 中文字体包
    pkgs.noto-fonts
    pkgs.noto-fonts-cjk
    pkgs.noto-fonts-emoji
    pkgs.noto-fonts-extra
    
    # 常用英文字体
    pkgs.liberation_ttf
    pkgs.source-han-sans
    pkgs.source-han-serif
    
    # 字体配置工具
    pkgs.freetype
    pkgs.xorg.xrdb
    
    # 中文字体支持
    pkgs.wqy_zenhei
    pkgs.wqy_microhei
    
    # 图像处理
    pkgs.imagemagick

    # OCR支持
    pkgs.tesseract

    # PDF工具 - 使用下划线版本
    pkgs.poppler_utils
  ];
}
