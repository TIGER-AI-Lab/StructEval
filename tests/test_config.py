import asyncio
import json

from structeval.config import (
    filter_by_split,
    filter_by_task,
    load_model_registry,
    resolve_model_spec,
    task_filter_label,
)
from structeval.workflows import infer_file_async, run_workflow_async


def test_model_registry_resolves_alias_and_passthrough(tmp_path):
    registry_path = tmp_path / "models.yaml"
    registry_path.write_text(
        """
models:
  alias:
    model: openai/real-model
    api_key_env: OPENAI_API_KEY
    api_base: https://example.test/v1
    temperature: 0.2
    litellm_params:
      extra: value
""",
        encoding="utf-8",
    )

    registry = load_model_registry(registry_path)
    resolved = resolve_model_spec("alias", registry)
    passthrough = resolve_model_spec("openai/direct", registry)

    assert resolved.model == "openai/real-model"
    assert resolved.api_key_env == "OPENAI_API_KEY"
    assert resolved.api_base == "https://example.test/v1"
    assert resolved.defaults["temperature"] == 0.2
    assert resolved.litellm_params == {"extra": "value"}
    assert passthrough.model == "openai/direct"


def test_filter_by_split():
    data = [
        {"task_id": "1", "rendering": True},
        {"task_id": "2", "rendering": False},
    ]

    assert [item["task_id"] for item in filter_by_split(data, "full")] == ["1", "2"]
    assert [item["task_id"] for item in filter_by_split(data, "renderable")] == ["1"]
    assert [item["task_id"] for item in filter_by_split(data, "nonrenderable")] == ["2"]


def test_filter_by_task_supports_paper_subtask_aliases():
    data = [
        {"task_id": "svg", "input_type": "Text", "output_type": "SVG"},
        {"task_id": "html", "input_type": "Text", "output_type": "HTML"},
        {"task_id": "json-yaml", "input_type": "JSON", "output_type": "YAML"},
    ]

    assert [item["task_id"] for item in filter_by_task(data, "svg")] == ["svg"]
    assert [item["task_id"] for item in filter_by_task(data, "T->SVG")] == ["svg"]
    assert [item["task_id"] for item in filter_by_task(data, "JSON->YAML")] == ["json-yaml"]
    assert task_filter_label("Text to SVG") == "T->SVG"


def test_infer_applies_split_before_limit(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset.json"
    output = tmp_path / "out.json"
    dataset.write_text(
        json.dumps(
            [
                {"task_id": "r1", "query": "render 1", "rendering": True},
                {"task_id": "n1", "query": "nonrender 1", "rendering": False},
                {"task_id": "n2", "query": "nonrender 2", "rendering": False},
            ]
        ),
        encoding="utf-8",
    )

    async def fake_run_inference_async(model, queries, **kwargs):
        assert queries == ["nonrender 1"]
        return ["generation"]

    monkeypatch.setattr("structeval.workflows.run_inference_async", fake_run_inference_async)

    asyncio.run(
        infer_file_async(
            dataset=dataset,
            output_path=output,
            model="openai/test",
            split="nonrenderable",
            limit=1,
        )
    )

    written = json.loads(output.read_text(encoding="utf-8"))
    assert [item["task_id"] for item in written] == ["n1"]
    assert written[0]["generation"] == "generation"


def test_run_workflow_evaluate_runs_outside_current_event_loop(tmp_path, monkeypatch):
    dataset = tmp_path / "dataset.json"
    dataset.write_text("[]", encoding="utf-8")
    captured_render = {}

    async def fake_infer_file_async(**kwargs):
        kwargs["output_path"].write_text("[]", encoding="utf-8")
        return kwargs["output_path"]

    async def fake_render_file_async(**kwargs):
        captured_render.update(kwargs)
        return kwargs["input_path"]

    def fake_evaluate_file(**kwargs):
        asyncio.run(asyncio.sleep(0))
        kwargs["output_path"].write_text("[]", encoding="utf-8")
        kwargs["summary_path"].write_text("{}", encoding="utf-8")

    monkeypatch.setattr("structeval.workflows.infer_file_async", fake_infer_file_async)
    monkeypatch.setattr("structeval.workflows.render_file_async", fake_render_file_async)
    monkeypatch.setattr("structeval.workflows.evaluate_file", fake_evaluate_file)

    paths = asyncio.run(
        run_workflow_async(
            dataset=dataset,
            output_dir=tmp_path / "run",
            model="openai/test",
            judge_model="openai/judge",
            render_concurrency=3,
        )
    )

    metadata = json.loads((tmp_path / "run" / "run.json").read_text(encoding="utf-8"))
    assert captured_render["render_concurrency"] == 3
    assert metadata["settings"]["render_concurrency"] == 3
    assert (tmp_path / "run" / "evaluation.json").exists()
    assert paths["summary"].endswith("summary.json")
