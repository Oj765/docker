"""Minimal synthetic training entrypoint for hackathon demos.

This keeps the current base intact while providing a documented place to train
an XGBoost model once historical or synthetic data is available.
"""

from pathlib import Path


def main() -> None:
    model_path = Path(__file__).with_name("xgb_virality.model")
    print(
        "No training dataset is checked into the repo yet. "
        f"When you add one, save the trained model to: {model_path}"
    )


if __name__ == "__main__":
    main()
