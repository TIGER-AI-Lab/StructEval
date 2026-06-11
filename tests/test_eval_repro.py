import json

from structeval.eval_engine.eval_nonrenderable import evaluate_nonrenderable
from structeval.eval_engine.main import calculate_final_score
from structeval.workflows import evaluate_file


def test_nonrenderable_missing_file_continues(tmp_path):
    valid_file = tmp_path / "valid.json"
    valid_file.write_text(json.dumps({"spaceship": {"crew": {"engineer": "Ada"}}}), encoding="utf-8")
    items = [
        {
            "task_id": "000500",
            "render_score": 1,
            "output_file": None,
            "raw_output_metric": ["spaceship.crew.engineer"],
        },
        {
            "task_id": "000501",
            "render_score": 1,
            "output_file": str(valid_file),
            "raw_output_metric": ["spaceship.crew.engineer"],
        },
    ]

    result = evaluate_nonrenderable(items, str(tmp_path))

    assert result[0]["key_validation_score"] == 0
    assert result[1]["key_validation_score"] == 1


def test_score_formula_unchanged():
    renderable = {"rendering": True, "render_score": 1, "raw_output_score": 0.5, "VQA_score": 0.5}
    calculate_final_score(renderable)
    assert renderable["final_eval_score"] == 0.6

    non_renderable = {"rendering": False, "render_score": 1, "key_validation_score": 0.5}
    calculate_final_score(non_renderable)
    assert non_renderable["final_eval_score"] == 0.6


def test_evaluate_file_uses_given_nonrenderable_dir(tmp_path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "evaluation.json"
    img_path = tmp_path / "images"
    expected_dir = tmp_path / "custom_nonrenderable"
    input_path.write_text(
        json.dumps([{"task_id": "000500", "rendering": False, "render_score": 0}]),
        encoding="utf-8",
    )

    def fake_evaluate_dataset(data, images, *args, **kwargs):
        assert kwargs["non_renderable_dir"] == str(expected_dir)
        data[0]["final_eval_score"] = 0
        return data

    monkeypatch.setattr("structeval.workflows.evaluate_dataset", fake_evaluate_dataset)

    evaluate_file(
        input_path=input_path,
        output_path=output_path,
        img_path=img_path,
        non_renderable_output_dir=expected_dir,
    )

    assert output_path.exists()
