{ pkgs, ... }: {

  channel = "stable-23.11";
  packages = [
    pkgs.python311,
    pkgs.python311Packages.pip,
    pkgs.azure-cli,
    pkgs.gh,
    pkgs.zip,
    # requirements.txt から追加
    pkgs.python311Packages.azure-functions,
    pkgs.python311Packages.requests,
    pkgs.python311Packages.azure-ai-translation-text,
    pkgs.python311Packages.azure-core,
    pkgs.python311Packages.azure-data-tables,
    pkgs.python311Packages.pytest
  ];
  env = {};
  idx = {
    extensions = [];
    previews = {
      enable = true;
    };
  };
}
