# Dev shell on NixOS: `nix-shell`, then `ruff check .`, `ruff format .`, `pytest`, and in frontend/ `npm run dev`.
# Uses the default python3, whose packages are prebuilt (python311's are not and build pandas from source).
{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  packages = [
    pkgs.ruff
    pkgs.nodejs # frontend/ (Svelte); CI uses the version in frontend/.nvmrc
    (pkgs.python3.withPackages (ps: [ ps.pytest ]))
  ];
}
