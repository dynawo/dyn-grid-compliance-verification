# DyCoV installers

This directory holds the **packaging and distribution machinery** for DyCoV: the
scripts that build the release artifacts and the helper scripts that end users
download from the release page.

It is maintainer-facing. If you are looking for how to install or use DyCoV, see
the user documentation instead:

- [Installation guide](../docs/installation/README.md) — all supported
  installation methods (prebuilt image on WSL/Docker, native Linux).
- [Tutorials](../docs/tutorials/README.md) — how to run DyCoV once installed,
  including [Grid-Forming analysis](../docs/tutorials/grid_forming_analysis.md).
- [Standalone Dynawo PAR utility](../tools/dynawo_par/README.md) — shipped by
  every installation method and as `dycov_par_tool.zip` on the release page.

## Contents

| Path | Role |
| :--- | :--- |
| `prepare_release.sh` | Builds every release artifact. Run it from the repository root — see [RELEASING.md](RELEASING.md). |
| `RELEASING.md` | How to generate and publish a release. |
| `linux_install.sh` | Native Linux installer; shipped to end users as a release artifact. |
| `docker/` | Image definition plus the build/export scripts and the end-user import/run helpers. |
| `wsl/` | Windows WSL installer and launcher shipped to end users. |
| `DGCV_win_installer.iss`, `dycov_GFM_only_setup.iss`, `DyCoV_GFM_only.md` | Legacy Inno Setup installers for native Windows; unused by the current release flow. |

## Building a release

```bash
./installers/prepare_release.sh v0.9.3 /path/to/dynawo
```

The full procedure, prerequisites and post-release checklist are documented in
[RELEASING.md](RELEASING.md).
