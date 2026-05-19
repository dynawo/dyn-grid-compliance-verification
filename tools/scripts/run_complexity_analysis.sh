#!/bin/bash
#
# Runs the cyclomatic complexity audit (tools/analyze_complexity.py) against the project.
# Ensures a virtual environment exists (creating or rebuilding it via build_and_install.sh
# if needed), installs radon/xenon/plotly/kaleido, then executes the analysis and reports
# results as CSV and PNG/HTML charts under complexity_report/.
#
#
# (c) Rte 2024
#     Developed by Grupo AIA
#

# Safer scripting options
set -o nounset -o noclobber
set -o errexit -o pipefail

# Variables
VENV_DIR="$PWD"/dycov_venv
SCRIPT_PATH="tools/analyze_complexity.py"
BUILD_SCRIPT="build_and_install.sh"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Trying $BUILD_SCRIPT..."
    if [ -f "$BUILD_SCRIPT" ]; then
        bash "$BUILD_SCRIPT"
    else
        echo "⚠️ $BUILD_SCRIPT not found. Creating virtual environment manually..."
        python3 -m venv "$VENV_DIR"
    fi
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install additional dependencies for complexity analysis
echo "Installing analysis dependencies..."
pip install radon xenon plotly kaleido

# Run the Python analysis script
echo "Running complexity analysis..."
python "$SCRIPT_PATH"

# Deactivate virtual environment
deactivate

echo "✅ Analysis completed. Check generated files (CSV and PNG)."