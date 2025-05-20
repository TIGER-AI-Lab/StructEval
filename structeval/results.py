#!/usr/bin/env python3
"""
summarize_eval_scores.py
Scan the `experiment_results` directory and aggregate final_eval_score
into tidy CSVs + a tiny JSON index of task groups.

Usage:
    python summarize_eval_scores.py  \
        --root experiment_results    \
        --out-dir summary_outputs
"""

import argparse
import json
import csv
from pathlib import Path
from collections import defaultdict
import pandas as pd

def load_eval_file(path: Path) -> list[dict]:
    """Return list of evaluation dicts from a JSON file."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Some writers wrap objects instead of lists—normalize.
    return data if isinstance(data, list) else [data]

def collect_scores(root: Path) -> tuple[dict, dict]:
    """
    Returns
    -------
    renderable : {model: {task_name: [scores...]}}
    nonrender  : {model: {task_name: [scores...]}}
    """
    renderable = defaultdict(lambda: defaultdict(list))
    nonrender  = defaultdict(lambda: defaultdict(list))

    for model_dir in root.iterdir():
        if not model_dir.is_dir():
            continue
        model = model_dir.name
        for kind, store in [
            ("evaluate_renderable.json", renderable),
            ("evaluate_nonrenderable.json", nonrender),
        ]:
            for record in load_eval_file(model_dir / kind):
                task   = record.get("task_name", record.get("task_id", "UNKNOWN_TASK"))
                score  = record.get("final_eval_score")
                if score is not None:
                    store[model][task].append(float(score))
    return renderable, nonrender

def average_scores(nested: dict) -> pd.DataFrame:
    """
    nested = {model: {task: [scores]}}
    Returns a DataFrame with model rows, task columns, plus 'average_score'.
    """
    # Collate per-model averages
    model_rows = {}
    for model, task_dict in nested.items():
        row = {task: sum(scores) / len(scores) for task, scores in task_dict.items()}
        model_rows[model] = row
    df = pd.DataFrame.from_dict(model_rows, orient="index").sort_index()
    df["average_score"] = df.mean(axis=1, skipna=True)
    return df

def main(root_dir: str, out_dir: str):
    root = Path(root_dir)
    out  = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    renderable, nonrender = collect_scores(root)

    # Save grouped-task index for quick reference
    task_groups = {
        "renderable": sorted({t for tasks in renderable.values() for t in tasks}),
        "non_renderable": sorted({t for tasks in nonrender.values() for t in tasks}),
    }
    (out / "task_groups.json").write_text(json.dumps(task_groups, indent=2))

    # Build & export CSVs
    for name, nested in [("renderable", renderable), ("nonrenderable", nonrender)]:
        df = average_scores(nested)
        df.to_csv(out / f"{name}_scores.csv", float_format="%.4f")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", "-r", default="experiment_results",
                        help="Path to experiment_results directory")
    parser.add_argument("--out-dir", "-o", default="summary_outputs",
                        help="Where to write CSV and JSON summaries")
    args = parser.parse_args()
    main(args.root, args.out_dir)