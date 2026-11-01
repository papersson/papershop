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
          # sops and age for script/secrets and script/doctor, outside the studio shell; bootstrap
          # links them at .cache/tools/secrets.
          secrets = pkgs.symlinkJoin { name = "papershop-secrets"; paths = [ pkgs.sops pkgs.age ]; };
          # nixpkgs' ClickHouse aborts at start on the cloud machines' kernel ("Cannot allocate
          # ThreadStack"); ClickHouse's own static build of the same version runs there, so x86_64
          # Linux takes that, pinned by checksum, and other systems take nixpkgs'.
          clickhouse-static =
            if system == "x86_64-linux" then
              pkgs.stdenvNoCC.mkDerivation rec {
                pname = "clickhouse-static";
                version = "26.5.1.882";
                src = pkgs.fetchurl {
                  url = "https://packages.clickhouse.com/tgz/stable/clickhouse-common-static-${version}-amd64.tgz";
                  hash = "sha256-2T4On29oTwsjO4LL35bozJQotXRHxfTtK31yNoyXTmY=";
                };
                dontFixup = true;
                installPhase = ''
                  mkdir -p $out/bin
                  cp usr/bin/clickhouse $out/bin/clickhouse
                  for tool in server client local; do ln -s clickhouse $out/bin/clickhouse-$tool; done
                '';
              }
            else pkgs.clickhouse;
          # The servers the wide-events film runs for real (films/observability-wide-events in
          # studio-journey): the shop's spans go through the OpenTelemetry Collector into ClickHouse,
          # orders live in Postgres, and Prometheus and Loki are the older stores it compares them with.
          # Opt-in (script/bootstrap --observability); about 1.5 GB from the Nix cache.
          observability = pkgs.symlinkJoin {
            name = "papershop-observability";
            paths = with pkgs; [ clickhouse-static postgresql_17 prometheus prometheus.cli grafana-loki opentelemetry-collector-contrib ];
          };
          default = worklog;
        });

      # `nix develop .#tutor`: the system tools of the retired tutor plugin's kit, which every tutor
      # lesson copied and still rebuilds with (Manim's cairo/pango,
      # Kokoro's espeak-ng, ffmpeg, the IBM Plex fonts) plus uv; the Python packages are pinned in
      # the copied kit's requirements.txt, installed into the project's venv.
      devShells = forAll (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in {
          tutor = pkgs.mkShell {
            packages = with pkgs; [ python311 uv ffmpeg espeak-ng cairo pango pkg-config ibm-plex ];
            FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ pkgs.ibm-plex ]; };
            shellHook = ''
              echo "tutor dev shell: for lessons made with the retired tutor plugin; new videos use the studio plugin"
            '';
          };

          # `nix develop .#studio`: the studio plugin's shell, defined once in studio/shell.nix.
          studio = import ./studio/shell.nix { inherit pkgs; };
        });
    };
}
