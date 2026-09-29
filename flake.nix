{
  description = "papershop — worklog (a work-history CLI), and the tutor and studio dev shells";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      forAll = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ];
    in
    {
      packages = forAll (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          py = pkgs.python3.withPackages (ps: [ ps.duckdb ]);
        in
        rec {
          worklog = pkgs.writeShellApplication {
            name = "worklog";
            runtimeInputs = [ py pkgs.duckdb ];
            text = ''
              # FTS lives in a writable cache; the store-resident duckdb can't
              # write extensions next to itself. DB defaults to the same cache
              # but stays overridable (e.g. WORKLOG_DB=~/.claude/worklog.duckdb).
              cache="''${XDG_CACHE_HOME:-$HOME/.cache}/worklog"
              mkdir -p "$cache/ext"
              export WORKLOG_DUCKDB_EXTENSION_DIR="$cache/ext"
              export WORKLOG_DB="''${WORKLOG_DB:-$cache/worklog.duckdb}"
              exec ${py}/bin/python ${./worklog/scripts/worklog.py} "$@"
            '';
          };
          default = worklog;
        });

      # `nix develop .#tutor`: the system side of the tutor plugin's pipeline (Manim's cairo/pango,
      # Kokoro's espeak-ng, ffmpeg, the IBM Plex fonts) plus uv; the Python packages are pinned in
      # tutor/skills/tutor/kit/requirements.txt and installed into a per-project venv by setup.sh.
      devShells = forAll (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in {
          tutor = pkgs.mkShell {
            packages = with pkgs; [ python311 uv ffmpeg espeak-ng cairo pango pkg-config ibm-plex ];
            FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ pkgs.ibm-plex ]; };
            shellHook = ''
              echo "tutor dev shell: run <plugin>/skills/tutor/scripts/setup.sh PROJECT_DIR to create the venv"
            '';
          };

          # `nix develop .#studio`: the studio plugin's shell, defined once in studio/shell.nix.
          studio = import ./studio/shell.nix { inherit pkgs; };
        });
    };
}
