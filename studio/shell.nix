# The studio's system layer, shared by studio/flake.nix (what an installed plugin carries) and the
# papershop flake's `studio` shell. Python packages are pinned by kit/uv.lock and Node packages by
# each engine's package-lock.json. The headless browser is not here: nixpkgs' Chromium is
# Linux-only, so `studio doctor` resolves it.
{ pkgs }:
pkgs.mkShell {
  packages = with pkgs; [ python312 uv nodejs_22 ffmpeg sox ];
  STUDIO_ENV = "nix";
}
