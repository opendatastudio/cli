{
  description = "Development Flake environment the opendata.studio CLI";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/23.11";

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem
    (system: let
      pkgs = import nixpkgs {
        inherit system;
      };
    in {
      devShells.default = pkgs.mkShell {
        buildInputs = [
          pkgs.pre-commit
          pkgs.python311
          # Workaround for library linking issue on NixOS
          pkgs.python311Packages.matplotlib
        ];

        shellHook = ''
          VENV=.venv
          if test -d $VENV; then
            source ./$VENV/bin/activate
          fi
        '';
      };
    });
}
