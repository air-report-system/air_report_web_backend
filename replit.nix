{ pkgs }: {
  deps = [
    # Python环境
    pkgs.python3

    # LibreOffice和PDF依赖
    pkgs.libreoffice-fresh

    # 字体配置
    pkgs.fontconfig
    pkgs.dejavu_fonts
    pkgs.liberation_ttf

    # 虚拟显示
    pkgs.xvfb-run

    # 系统工具
    pkgs.curl
    pkgs.wget
    pkgs.git

    # 数据库客户端
    pkgs.postgresql

    # 开发工具
    pkgs.gcc
  ];
}
