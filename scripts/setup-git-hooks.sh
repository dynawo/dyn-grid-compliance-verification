#!/bin/bash
# Registers the custom CSV merge driver in the local git config.
# Run once after cloning the repository.

REPO_ROOT=$(git rev-parse --show-toplevel)

chmod +x "${REPO_ROOT}/scripts/git-merge-csv-ref"

git config merge.csv-ref.name "Example CSV reference driver"
git config merge.csv-ref.driver "bash \"${REPO_ROOT}/scripts/git-merge-csv-ref\" %O %A %B"

echo "CSV merge driver installed successfully."