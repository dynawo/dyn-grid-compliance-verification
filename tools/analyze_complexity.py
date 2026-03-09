import csv
import json
import re
import subprocess
from pathlib import Path

import plotly.express as px

# Project folder (adjust if needed)
project_folder = Path.cwd() / "src"

# Output folder in current working directory
output_folder = Path.cwd() / "complexity_report"
output_folder.mkdir(parents=True, exist_ok=True)

# Run Radon to get cyclomatic complexity
radon_cmd = ["radon", "cc", str(project_folder), "-j"]
result = subprocess.run(radon_cmd, capture_output=True, text=True)

if result.returncode != 0:
    print("Error: Radon not found or invalid path.")
    exit()

radon_data = json.loads(result.stdout)

complexity_records = []
for file, functions in radon_data.items():
    for func in functions:
        complexity_records.append(
            {
                "file": file,
                "name": func["name"],
                "complexity": func["complexity"],
                "rank": func["rank"],
            }
        )

# Identify critical functions (E/F)
critical_functions = [f for f in complexity_records if f["rank"] in ["E", "F"]]

# Count call frequency
call_counts = {}
for py_file in project_folder.rglob("*.py"):
    content = py_file.read_text(encoding="utf-8")
    for func in complexity_records:
        pattern = rf"\b{func['name']}\("
        count = len(re.findall(pattern, content))
        call_counts[func["name"]] = call_counts.get(func["name"], 0) + count

for func in complexity_records:
    func["call_frequency"] = call_counts.get(func["name"], 0)

# Save CSV report
csv_file = output_folder / "complexity_report.csv"
with csv_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["file", "name", "complexity", "rank", "call_frequency"])
    writer.writeheader()
    writer.writerows(complexity_records)

# Generate visualizations
fig_hist = px.histogram(
    complexity_records, x="complexity", nbins=20, title="Cyclomatic Complexity Distribution"
)
fig_top = px.bar(
    sorted(complexity_records, key=lambda x: x["complexity"], reverse=True)[:10],
    x="name",
    y="complexity",
    color="rank",
    title="Top 10 Most Complex Functions",
)

# Save charts in output folder
try:
    fig_hist.write_image(str(output_folder / "complexity_histogram.png"))
    fig_top.write_image(str(output_folder / "top_complex_functions.png"))
    print("✅ Charts saved as PNG.")
except Exception:
    print("⚠️ PNG export failed. Saving as HTML instead.")
    fig_hist.write_html(str(output_folder / "complexity_histogram.html"))
    fig_top.write_html(str(output_folder / "top_complex_functions.html"))
    print("✅ Charts saved as HTML.")

print(f"Analysis complete. CSV saved as {csv_file}.")
print("Critical functions (E/F):")
for func in critical_functions:
    print(f"- {func['name']} (Complexity: {func['complexity']}, Calls: {func['call_frequency']})")
