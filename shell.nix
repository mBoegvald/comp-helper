# Dev shell on NixOS: `nix-shell`, then `ruff check .`, `ruff format .` and `pytest`.
# Uses the default python3, whose packages are prebuilt (python311's are not and build pandas from source).
{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  packages = [
    pkgs.ruff
    (pkgs.python3.withPackages (ps: [ ps.pytest ]))
  ];
}
