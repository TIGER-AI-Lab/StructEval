input_text = """
Text -> Angular: 50
Text -> CSV: 50
Text -> Canvas: 50
Text -> HTML: 50
Text -> JSON: 50
Text -> Latex: 50
Text -> Markdown: 50
Text -> Matplotlib: 50
Text -> Mermaid: 50
Text -> TOML: 50
Text -> React: 50
Text -> SVG: 50
Text -> Tikz: 50
Text -> Typst: 50
Text -> Vega: 50
Text -> Vue: 50
Text -> XML: 50
Text -> YAML: 50

### Web Development Conversion(405):

Markdown → HTML: 50
HTML → React: 45
React → HTML: 45
Vue → HTML: 40
HTML → Vue: 40
Angular → React: 35
Markdown → React: 30
HTML → Angular: 30
Markdown → Vue: 25
Angular → HTML: 20
Angular → Vue: 15
Vue → React: 15
Markdown → Angular: 10
React → Angular: 5
Vue → Angular: 0

### Plot Conversion(100):

Matplotlib → TikZ: 100
TikZ → Matplotlib: 0

### Data Representation Conversion(280)

CSV → JSON: 50
JSON → CSV: 45
XML → JSON: 40
JSON → XML: 35
YAML → JSON: 25
JSON → YAML: 20
XML → CSV: 15
CSV → XML: 10
XML → YAML: 10
YAML → XML: 10
YAML → CSV: 5
TOML → JSON: 5
CSV → YAML: 5
TOML → YAML: 5
TOML → XML: 0
"""

# Parse lines
task_lines = []
for line in input_text.splitlines():
    line = line.strip()
    if "→" in line or "->" in line:
        # Remove ": number" if present
        if ":" in line:
            line = line.split(":")[0].strip()
        task_lines.append(line)

# Write to file
with open("tasks_only.txt", "w", encoding="utf-8") as f:
    for task in task_lines:
        f.write(task + "\n")

print(f"✅ Extracted {len(task_lines)} tasks to tasks_only.txt")