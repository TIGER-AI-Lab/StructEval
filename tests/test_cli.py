from typer.testing import CliRunner

from structeval.cli import app


def test_cli_help():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.output
    assert "init" in result.output
    assert "evaluate" in result.output
    assert "reproduce" in result.output
    assert "summary" in result.output
    assert "doctor" in result.output
    assert "│ infer" not in result.output
    assert "│ render" not in result.output


def test_hidden_commands_are_still_available():
    runner = CliRunner()

    infer_result = runner.invoke(app, ["infer", "--help"])
    render_result = runner.invoke(app, ["render", "--help"])

    assert infer_result.exit_code == 0
    assert render_result.exit_code == 0


def test_init_writes_templates_without_overwriting(tmp_path, monkeypatch):
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    first = runner.invoke(app, ["init"])
    assert first.exit_code == 0
    assert "Wrote structeval.yaml" in first.output
    assert "Wrote models/models.yaml" in first.output

    (tmp_path / "structeval.yaml").write_text("custom: true\n", encoding="utf-8")

    second = runner.invoke(app, ["init"])
    assert second.exit_code == 0
    assert "Templates already exist" in second.output
    assert (tmp_path / "structeval.yaml").read_text(encoding="utf-8") == "custom: true\n"

    forced = runner.invoke(app, ["init", "--force"])
    assert forced.exit_code == 0
    assert "dataset: dataset/StructEval_dataset.json" in (
        tmp_path / "structeval.yaml"
    ).read_text(encoding="utf-8")


def test_infer_resolves_model_alias_and_cli_overrides(tmp_path, monkeypatch):
    runner = CliRunner()
    captured = {}

    async def fake_infer_file_async(**kwargs):
        captured.update(kwargs)
        return kwargs["output_path"]

    monkeypatch.setattr("structeval.cli.infer_file_async", fake_infer_file_async)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "dataset.json").write_text("[]", encoding="utf-8")
    (tmp_path / "structeval.yaml").write_text(
        "dataset: dataset.json\n"
        "model: alias\n"
        "output_path: out.json\n"
        "api_key_env: CONFIG_KEY\n"
        "split: renderable\n"
        "temperature: 0.3\n",
        encoding="utf-8",
    )
    import os

    os.makedirs("models", exist_ok=True)
    (tmp_path / "models/models.yaml").write_text(
        "models:\n"
        "  alias:\n"
        "    model: openai/real-model\n"
        "    api_key_env: REGISTRY_KEY\n"
        "    temperature: 0.1\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["infer", "--config", "structeval.yaml", "--api-key-env", "CLI_KEY"],
    )

    assert result.exit_code == 0
    assert captured["model"] == "openai/real-model"
    assert captured["api_key_env"] == "CLI_KEY"
    assert captured["split"] == "renderable"
    assert captured["temperature"] == 0.3


def test_infer_default_temperature_matches_paper(tmp_path, monkeypatch):
    runner = CliRunner()
    captured = {}

    async def fake_infer_file_async(**kwargs):
        captured.update(kwargs)
        return kwargs["output_path"]

    monkeypatch.setattr("structeval.cli.infer_file_async", fake_infer_file_async)
    monkeypatch.chdir(tmp_path)

    (tmp_path / "dataset.json").write_text("[]", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "infer",
            "--dataset",
            "dataset.json",
            "--model",
            "openai/gpt-4.1-mini",
            "--output-path",
            "out.json",
        ],
    )

    assert result.exit_code == 0
    assert captured["temperature"] == 0.0


def test_reproduce_applies_paper_settings_and_task_filter(tmp_path, monkeypatch):
    runner = CliRunner()
    captured = {}

    async def fake_run_workflow_async(**kwargs):
        captured.update(kwargs)
        return {
            "inference": "inference.json",
            "images": "images",
            "non_renderable": "non_renderable_format_files",
            "evaluation": "evaluation.json",
            "summary": "summary.json",
            "metadata": "run.json",
        }

    monkeypatch.setattr("structeval.cli.run_workflow_async", fake_run_workflow_async)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "reproduce",
            "--model",
            "openrouter/openai/gpt-4.1-mini",
            "--task",
            "svg",
            "--api-key-env",
            "OPENROUTER_API_KEY",
        ],
    )

    assert result.exit_code == 0
    assert captured["model"] == "openrouter/openai/gpt-4.1-mini"
    assert captured["judge_model"] == "openrouter/openai/gpt-4.1-mini"
    assert captured["api_key_env"] == "OPENROUTER_API_KEY"
    assert captured["judge_api_key_env"] == "OPENROUTER_API_KEY"
    assert captured["task"] == "svg"
    assert captured["concurrency"] == 32
    assert captured["render_concurrency"] == 4
    assert captured["temperature"] == 0.0
    assert captured["judge_temperature"] == 0.0
    assert captured["max_tokens"] is None


def test_reproduce_without_task_runs_full(tmp_path, monkeypatch):
    runner = CliRunner()
    captured = {}

    async def fake_run_workflow_async(**kwargs):
        captured.update(kwargs)
        return {
            "inference": "inference.json",
            "images": "images",
            "non_renderable": "non_renderable_format_files",
            "evaluation": "evaluation.json",
            "summary": "summary.json",
            "metadata": "run.json",
        }

    monkeypatch.setattr("structeval.cli.run_workflow_async", fake_run_workflow_async)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "reproduce",
            "--model",
            "openai/gpt-4.1-mini",
        ],
    )

    assert result.exit_code == 0
    assert captured["task"] is None
    assert captured["concurrency"] == 32
    assert captured["render_concurrency"] == 4
