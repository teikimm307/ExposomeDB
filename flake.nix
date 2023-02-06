{
  description = "Juni's Vanilla Flake Template";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-22.11";
    flake-utils = {
      url = "github:numtide/flake-utils";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils }:
    with flake-utils.lib;
    eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        version = "0.1.0";
        name = "package name";
        myR = pkgs.rWrapper.override{ packages = with pkgs.rPackages; [ crul ]; };
      in {

        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [ python3 poetry myR ];
        };

        defaultPackage = pkgs.stdenv.mkDerivation { inherit name version; };

        formatter = nixpkgs.legacyPackages."${system}".nixfmt;

      });
}
