# AGENTS.md

Compact notes for OpenCode sessions. Everything here is verified against the repo; omit anything the code makes obvious.

## Repo shape
- Single-file app. `envious.py` (~1200 lines) contains the CLI parser, offline mode, and the curses UI (`EnviousApp` class). No package layout, no tests, no CI, no Makefile, no pre-commit hooks.
- Requires Linux + NVIDIA driver ≥ 555.xx on a Maxwell-or-newer GPU. Without a GPU the app is unrunnable; verify changes via `python -m py_compile` and `ruff check` instead.

## Toolchain
- Python `>=3.10` (`.python-version` is `system`; do not assume pyenv pinning).
- Formatter/linter is **ruff** (`[tool.ruff] line-length = 120` in `pyproject.toml`). A stale `.pylintrc` (line-length 100) is checked in but gitignored and unused — trust ruff. Run `ruff format envious.py` and `ruff check envious.py` before committing.
- No test suite exists. Do not fabricate one.

## Critical quirks an agent will get wrong
- `envious.py` does `import pynvml as nv`, but the actual dependency is **`nvidia-ml-py`** (declared in `pyproject.toml` and `requirements.txt`); it installs the `pynvml` module. Never add `pynvml` from PyPI as a dep or run `pip install pynvml` — that's a different, unmaintained package.
- Memory clock offsets are stored/reported to the user in **half NVML's units** (matches GreenWithEnvy / MSI Afterburner, *not* `nvidia-settings`). Writing: `nvmlDeviceSetMemClkVfOffset(gpu, mem_offset * 2)` (see `envious.py:273,305`). Reading: divide by 2 (see `envious.py:398`). Any new memory-clock code path must preserve both.
- NVML returns negative VF offsets as huge unsigned ints. Wrap any read of `nvmlDeviceGetGpcClkVfOffset` / `nvmlDeviceGetMemClkVfOffset` with `rectify_nvml_overflow()` at `envious.py:130`.
- Profile directory is decided at `envious.py:172-175`: `/var/lib/envious` **only** when the script's realpath dir is `/usr/bin` (i.e. installed via `install.sh`); otherwise it's the script's own directory. There is no env-var override.
- Profile files are named `profile{N}_{gpu_number}.bnt` with N in **1..4**, five lines: core offset, mem offset, power limit (W), fan policy (0 auto / 1 manual), fan speed %. `.bnt` is a legacy of the project's old name "BlissfulNvidiaTool" and is in `.gitignore` — don't rename the extension casually.
- Offline vs interactive dispatch happens in `main()` at `envious.py:1192-1206`: any `--set-*` flag forces `run_offline()`; otherwise the curses dashboard runs. `--set-profile` short-circuits the other offline setters (see `envious.py:203`).
- There is **no root pre-check**. Root-requiring NVML setters simply log the caught `NVMLError` and continue; don't add an `os.geteuid()` guard unless asked.
- `curses`, `ctypes`, and `psutil` are imported **inside** `run_interactive` / `_dashboard` (`envious.py:338,345,347`) so offline mode stays fast and dependency-light. Keep them lazy; hoisting them breaks the intent.
- Fan speed is clamped to 30–100% manually in code (`envious.py:246,264,310`) — NVML itself would accept more. Preserve the floor.

## Adding a CLI flag = 3-place update
1. `argparse` entry in `parse_args()` (`envious.py:55`).
2. Handling in `EnviousApp.run_offline()` or the curses dispatcher.
3. `envious.1` man page — README explicitly directs users to `man envious` for the full option list.

## Versioning (three sources, keep in sync)
- `version = "1.6"` in `pyproject.toml`
- `__VERSION__ = "1.60"` in `envious.py:52` (note the differing format)
- `.TH ENVIOUS 1 ... "envious 1.6"` header line in `envious.1`

## Install / packaging
- `install.sh` copies `envious.py` → `/usr/bin/envious`, gzips `envious.1` → `/usr/share/man/man1/envious.1.gz`, and creates `/var/lib/envious`. Because of the `/usr/bin` path check above, this is what activates system-wide profile storage. `uninstall.sh` reverses it. Both require root.
- No build step, no wheel publishing config; `pyproject.toml` is metadata only.
