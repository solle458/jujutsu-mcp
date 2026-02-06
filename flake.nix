{
  description = "Jujutsu MCP Server - MCP server for Jujutsu (jj) version control system";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            jujutsu
            python311
            uv
          ];

          shellHook = ''
            export JJ_CONFIG="$PWD/.jjconfig"
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
            echo "Jujutsu Master Environment Loaded"
            echo "Python: $(python3 --version)"
            echo "Jujutsu: $(jj --version)"
            echo "UV: $(uv --version)"
          '';
        };
      }
    );
}
