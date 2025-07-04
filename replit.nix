{ pkgs }: {
  deps = [
    # Python环境
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.setuptools
    pkgs.python312Packages.wheel
    
    # LibreOffice和PDF依赖
    pkgs.libreoffice
    pkgs.unoconv
    
    # 字体配置
    pkgs.fontconfig
    pkgs.dejavu_fonts
    pkgs.liberation_ttf
    pkgs.freefont_ttf
    
    # 虚拟显示
    pkgs.xvfb-run
    pkgs.xorg.xvfb
    
    # 系统工具
    pkgs.curl
    pkgs.wget
    pkgs.gnupg
    pkgs.git
    
    # 数据库客户端
    pkgs.postgresql
    
    # 图像处理
    pkgs.imagemagick
    pkgs.ghostscript
    
    # 开发工具
    pkgs.gcc
    pkgs.pkg-config
  ];
  
  env = {
    # Python环境变量
    PYTHONPATH = "";
    PYTHONUNBUFFERED = "1";
    PYTHONDONTWRITEBYTECODE = "1";
    
    # LibreOffice环境变量
    UNO_PATH = "${pkgs.libreoffice}/lib/libreoffice/program";
    OFFICE_HOME = "${pkgs.libreoffice}/lib/libreoffice";
    
    # 字体配置
    FONTCONFIG_PATH = "${pkgs.fontconfig.out}/etc/fonts";
    
    # 虚拟显示
    DISPLAY = ":99";
  };
}
