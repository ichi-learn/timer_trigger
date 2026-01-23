{ pkgs, ... }: {
  channel = "stable-23.11";
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.azure-cli
    pkgs.gh
    pkgs.zip
  ];
  env = {};
  idx = {
    extensions = [];
    previews = {
      enable = true;
    };
  };
}
