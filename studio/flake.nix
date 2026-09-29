{
  description = "studio — the system layer of the studio plugin (`nix develop .#studio`)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      forAll = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ];
    in
    {
      devShells = forAll (system: rec {
        studio = import ./shell.nix { pkgs = nixpkgs.legacyPackages.${system}; };
        default = studio;
      });
    };
}
