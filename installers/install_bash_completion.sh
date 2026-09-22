#!/bin/bash
#
# Installs the bash completion of the 'dycov' command into a virtual environment, and makes the
# environment's activation script load it. Both the DyCoV installer and the developer build script
# call it, so a new or modified command is completed without touching this file: the script is
# generated from the CLI parsers themselves.
#
# Usage: install_bash_completion.sh <venv_dir>
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset
set -o errexit -o pipefail

VENV_DIR="$1"
COMPLETION_FILE="$VENV_DIR/share/bash-completion/completions/dycov"
HOOK_MARKER="# DyCoV bash completion"

mkdir -p "$(dirname "$COMPLETION_FILE")"
"$VENV_DIR"/bin/dycov --print-completion bash > "$COMPLETION_FILE"

if ! grep -q "$HOOK_MARKER" "$VENV_DIR"/bin/activate; then
    cat >> "$VENV_DIR"/bin/activate <<EOF

$HOOK_MARKER (bash only; other shells can use 'dycov --print-completion <shell>').
if [ -n "\${BASH_VERSION:-}" ] && [ -r "\$VIRTUAL_ENV/share/bash-completion/completions/dycov" ]; then
    . "\$VIRTUAL_ENV/share/bash-completion/completions/dycov"
fi
EOF
fi
