# Updating the leaderboard

The page reads `static/data/leaderboard.json`. The chart and table share the same
results and filters. The leaderboard appears immediately after the compact hero.

## Refresh from the evaluation repository

From this website directory, run:

```bash
python3 scripts/sync_leaderboard.py --source ../StructEval
```

This reads the sibling repository without modifying it or starting inference.
No API keys or third-party JavaScript chart service are needed.

The importer reads the reviewed run list in `static/data/evaluation-sources.json`
and checks every task ID against `dataset/StructEval_dataset.json`. It rejects
unknown/duplicate IDs, mismatched task metadata, non-finite scores, scores outside
0–1, and missing scores. Failed renders with a recorded numeric score remain in
the denominator. A run is complete only if it covers all 2,035 unique tasks.
Incomplete models appear at the bottom of the table with their progress,
without a rank or overall score, and are excluded from plots.

The importer recomputes overall and subset scores from `final_eval_score` in the
raw evaluation artifacts. It exports score-only evidence to `static/data/artifacts/`
with per-task scores, subset counts, and SHA-256 hashes of the dataset and original
evaluation file. Generated answers, prompts, credentials, and machine-local
absolute paths are not copied into the site. Readers can download each row's
numeric evidence and reproduce its averages without access to the source repo.

A refresh is a saved snapshot, not a live feed. Commit the generated data and
artifacts with the website when publishing an update. The date shown on the page
is the snapshot import date; it does not claim that models were evaluated that day.

## One leaderboard

All models share one table and chart. New models are added directly to this list.
The All, Open Source, and Closed Source controls filter both views. All models
share one overall ranking by score, with no separate category sections. Filtering,
searching, and changing the column sort preserve overall ranks. Every row has a
category badge and a light green (open) or blue (closed) background.
The chart uses company logos with a small solid green circle (open) or blue
diamond (closed) at the lower-right corner, separated by a white outline.
The legend explains both symbols, and model details explicitly
show the category. Logos are bundled locally in
`static/images/providers/`; their source and license are recorded there. The
`providerLogos` mapping in `static/js/index.js` assigns each provider an asset
(Qwen uses its own logo). Unknown providers or failed image loads retain a category
marker. Model names and exact scores remain available on hover, click, and focus.
Categories use the
metadata's `access` field, which records weight availability.
Each `model_key` appears once, using its most recent completed evaluation.
An unfinished update does not replace a completed result. If no complete result
exists, the latest partial run supplies the pending row and its progress.
Selection uses evaluation date, then coverage; ties retain the first configured
source, never whichever judge produced the higher score.

The original website's results in `static/data/paper-baseline.json` supply
fallback rows until newer completed evaluations are available. For example,
GPT-4.1 mini now appears once with its updated score. Nemotron 3 Ultra's two judge
runs produce one pending model row, currently covering 912 of 2,035 tasks.

Recorded scores are preserved: imported runs average all evaluated examples,
while the original table reports an average of four subset scores. Each row
retains `score_aggregation`, judge, and evidence links. Run evidence also records
protocol and environment notes. The chart uses completed results. Its vertical
axis fits the currently plotted scores with padding and rounded ticks, bounded
by 0–100%. It recalculates when filtering, searching, or changing the horizontal
axis; single-model selections retain a nonzero range.

The release-date view offers a Best-score line, disabled by default. This step
line takes the highest score on each release date, then the running maximum
across the currently visible models. It ends at the latest visible release and
updates with category and search filters. It describes current scores ordered by
release date, not historical benchmark results. It is omitted for fewer than two
distinct release dates and is not shown on the model-size axis.

The GPT-6 Luna run scored by local Gemma 4 E4B is excluded from the import list,
table, chart, and published score artifacts. Only add it back after an evaluation
with the agreed judge has been reviewed.

## Add a reviewed run

1. Save the run's full evaluation JSON and document the exact model/provider,
   model snapshot when available, dataset, judge, generation settings, rendering
   environment, and evaluation date in the evaluation repository.
2. Add its model metadata to `static/data/model-metadata.json` with source links.
3. Add a unique run ID, model key, source-relative evaluation path, date, judge,
   and protocol source to `static/data/evaluation-sources.json`.
4. Run the importer. Review scores, coverage, and renderer failures before
   publishing. Do not list smoke tests or incomplete generation
   outputs as full evaluations.
5. Refresh the browser to see the updated table and both chart axes.

The local small-model batch also contains inference work without completed
scoring. Those outputs must acquire reviewed evaluation artifacts before adding
rows to the leaderboard.

## Release dates and model size

Metadata is maintained separately from evaluation scores. `release_date` uses
vendor-documented availability, not the run date, a training cutoff, or the date
encoded in a model snapshot. `release_note` records qualifications such as preview
availability (DeepSeek V4 Flash), stable GA (Gemini 2.0 Flash), or the Qwen3.7 Plus
June 1 availability versus May 26 snapshot date. Historical API aliases can change;
the June DeepSeek result must not be relabeled as a later V4 update.

`parameters_b` is the vendor-reported total parameter count in billions, including
embeddings when the model card reports them. For example, Qwen2.5 7B uses 7.61B.
`active_parameters_b` is a separate MoE field, never substituted for total size.
Llama's 8B values are the vendor's reported model size class. Unknown or undisclosed
counts stay `null`, display as “Not disclosed,” and are omitted from the size plot.
That axis uses a logarithmic scale and reports the number of excluded models.

Every published release date has a linked official source. Parameter source links
are included for known sizes. Open/closed refers to weight availability, not price.

## Local preview

```bash
python3 -m http.server 8001 --bind 127.0.0.1
```

Open http://127.0.0.1:8001/ using HTTP; `file://` browsing blocks JSON fetching in
some browsers. The site remains compatible with a GitHub Pages project subpath.
