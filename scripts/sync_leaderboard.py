#!/usr/bin/env python3
"""Export reviewed StructEval runs as a portable, score-only website snapshot.

Reads the sibling evaluation repo without changing it or running model code.
Only runs explicitly listed in evaluation-sources.json can enter the board.
"""

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
DATA = SITE / "static" / "data"
SUBSETS = ("t_generation", "t_conversion", "v_generation", "v_conversion")


def read_json(path):
    return json.loads(path.read_text())


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def subset(task):
    return ("v" if task["rendering"] else "t") + (
        "_generation" if task["input_type"] == "Text" else "_conversion"
    )


def mean(items, field="score"):
    return round(math.fsum(item[field] for item in items) / len(items) * 100, 2) if items else None


def export_run(root, source, dataset, dataset_hash, metadata):
    path = root / source["evaluation"]
    raw = path.read_bytes()
    records = json.loads(raw)
    ids = [row["task_id"] for row in records]
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= dataset.keys():
        raise ValueError(f"{path}: empty results, duplicate IDs, or unknown tasks")
    scores = []
    for record in records:
        task = dataset[record["task_id"]]
        for field in ("input_type", "output_type", "rendering"):
            if record[field] != task[field]:
                raise ValueError(f"{path}: task {record['task_id']} has mismatched {field}")
        for field in ("final_eval_score", "render_score"):
            value = record.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{path}: task {record['task_id']} has invalid {field}")
        scores.append({"task_id": record["task_id"], "subset": subset(task),
                       "score": record["final_eval_score"], "render_score": record["render_score"]})
    complete = set(ids) == dataset.keys()
    visual = [s for s in scores if s["subset"].startswith("v_")]
    text = [s for s in scores if s["subset"].startswith("t_")]
    metrics = {"overall": mean(scores), "renderable": mean(visual), "non_renderable": mean(text),
               "render_rate": mean(scores, "render_score")}
    metrics.update({key: mean([s for s in scores if s["subset"] == key]) for key in SUBSETS})
    row = {**metadata[source["model_key"]], **source,
           "score_aggregation": "Mean over evaluated examples",
           "complete": complete, "n": len(scores), "expected_n": len(dataset),
           "subset_counts": dict(Counter(s["subset"] for s in scores)), "metrics": metrics,
           "artifact_url": f"./static/data/artifacts/{source['id']}.json"}
    # Keep only relative source paths and numeric scores; never publish raw model outputs.
    evidence = {"run": row, "dataset_sha256": dataset_hash,
                "evaluation_sha256": sha256(raw), "score_scale": "Per-task 0–1; aggregate 0–100",
                "aggregation": "Arithmetic mean over evaluated examples; failed renders remain included.",
                "task_scores": sorted(scores, key=lambda s: s["task_id"])}
    return row, evidence


def latest_results(rows):
    """One row per model; completed runs take precedence over partial updates.

    Choose by evaluation date, then coverage. Ties retain the first configured
    source, never the highest score. Undated historical results are fallbacks.
    """
    selected = {}
    def priority(row):
        return (row["complete"], row["evaluated_on"] or "", row["n"])
    for row in rows:
        key = row["model_key"]
        if key not in selected or priority(row) > priority(selected[key]):
            selected[key] = row
    return sorted(selected.values(), key=lambda row: (
        not row["complete"], -row["metrics"]["overall"] if row["complete"] else 0, row["name"]
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SITE.parent / "StructEval")
    args = parser.parse_args()
    sources = read_json(DATA / "evaluation-sources.json")
    metadata = read_json(DATA / "model-metadata.json")["models"]
    raw_dataset = (args.source / sources["dataset"]).read_bytes()
    tasks = json.loads(raw_dataset)
    dataset = {task["task_id"]: task for task in tasks}
    if len(dataset) != 2035 or len(tasks) != len(dataset):
        raise ValueError("Expected the complete 2,035-example StructEval dataset with unique task IDs")
    rows, artifacts = [], {}
    for source in sources["runs"]:
        row, evidence = export_run(args.source, source, dataset, sha256(raw_dataset), metadata)
        if row["id"] in artifacts:
            raise ValueError(f"Duplicate run ID: {row['id']}")
        rows.append(row)
        artifacts[row["id"]] = evidence

    paper = read_json(DATA / "paper-baseline.json")
    mapping = dict(zip(SUBSETS, ("se_t_gen", "se_t_conv", "se_v_gen", "se_v_conv")))
    for index, original in enumerate(paper["rows"]):
        rows.append({**metadata[original["model"]], "id": f"paper-{index}", "model_key": original["model"],
                     "n": 2035, "expected_n": 2035, "complete": True,
                     "score_aggregation": "Reported average of four subset scores",
                     "evaluated_on": None, "judge": "Published paper protocol",
                     "metrics": {"overall": original["average"],
                                 **{key: original[field] for key, field in mapping.items()}},
                     "artifact_url": "./static/data/paper-baseline.json",
                     "notes": "Original website paper results; exact evaluation date and model snapshot not recorded in that table."})

    rows = latest_results(rows)
    snapshot = {"schema_version": 3, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "dataset_n": len(dataset), "dataset_sha256": sha256(raw_dataset),
                "results": rows}
    # Validate every source before replacing any exported file.
    out = DATA / "artifacts"
    out.mkdir(exist_ok=True)
    for run_id, evidence in artifacts.items():
        (out / f"{run_id}.json").write_text(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False) + "\n")
    temp = DATA / "leaderboard.json.tmp"
    temp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    temp.replace(DATA / "leaderboard.json")
    print(f"Imported {len(artifacts)} evaluation runs plus {len(paper['rows'])} paper baselines.")
    for row in rows:
        status = "ranked" if row["complete"] else "pending"
        print(f"{status:9} {row['name']:25} {row['n']:4}/2035  {row['metrics']['overall']:.2f}%  {row['judge']}")


if __name__ == "__main__":
    main()
