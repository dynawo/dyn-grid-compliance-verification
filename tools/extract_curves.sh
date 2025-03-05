#!/bin/bash

# Check if the necessary arguments were provided
if [ "$#" -ne 2 ]; then
    echo "usage: $0 <results_directory_input> <rename_directory_output>"
    echo ""
    echo "positional arguments:"
    echo "  results_directory_input     enter the output path of the dycov Tool"
    echo "  rename_directory_output     enter the path to the reference curves"
    exit 1
fi

# Directories passed as arguments
RESULTS_DIR="$1"
RENAME_DIR="$2"

# Create the Rename folder if it doesn't exist
mkdir -p "$RENAME_DIR"

# Find all "curves_calculated.csv" files in the Results folder
find "$RESULTS_DIR" -type f -name "curves_calculated.csv" | while read -r file; do
    # Get the directory of the file
    dir=$(dirname "$file")

    # Extract the three parent folders
    parent1=$(basename "$dir")
    parent2=$(basename "$(dirname "$dir")")
    parent3=$(basename "$(dirname "$(dirname "$dir")")")

    # Create the new file name
    new_name="${parent3}.${parent2}.${parent1}.csv"

    # Copy and rename the file
    cp "$file" "$RENAME_DIR/$new_name"
done