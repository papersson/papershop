{
  description = "worklog — query Claude Code transcripts as a work history";

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
              exec ${py}/bin/python ${./scripts/worklog.py} "$@"
            '';
          };
          default = worklog;
        });
    };
}
