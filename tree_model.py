"""Compare a decision tree on the existing walk-forward development folds."""

from datetime import timedelta
import json

import sklearn
from sklearn.tree import DecisionTreeRegressor

from baseline_delay import PROJECT, metrics
from train_delay_model import MedianChangeModel
from trend_baseline import load_rows, predict_trend
from walk_forward import START, FIRST_VALIDATION, END


FEATURE_NAMES = [
    "current_delay",
    "previous_delay_change",
    "previous_gap_minutes",
    "missing_history",
]

TREE_SETTINGS = {
    "criterion": "squared_error",
    "max_depth": 4,
    "min_samples_leaf": 100,
    "random_state": 42,
}


def features(row):
    previous = row["previous_delay"]
    age = row["previous_age_seconds"]

    valid = (
        previous is not None
        and 0 <= previous <= 997
        and age is not None
        and 0 < age <= 1800
    )

    if not valid:
        return [row["initial"], 0, 0, 1]

    return [
        row["initial"],
        row["initial"] - previous,
        age / 60,
        0,
    ]


def score(rows, predictions):
    return metrics([
        (float(prediction), row["outcome"], row["horizon"])
        for row, prediction in zip(rows, predictions, strict=True)
    ])


def run():
    rows = load_rows()
    folds = []
    day = FIRST_VALIDATION

    while day < END:
        training = [row for row in rows if START <= row["day"] < day]
        validation = [row for row in rows if row["day"] == day]

        if not training or not validation:
            raise ValueError(f"Missing examples for {day}")

        # X contains only information known at prediction time.
        x_train = [features(row) for row in training]

        # y is the later observed change we want the tree to learn.
        y_train = [
            row["outcome"] - row["initial"]
            for row in training
        ]

        tree = DecisionTreeRegressor(**TREE_SETTINGS)
        tree.fit(x_train, y_train)

        predicted_changes = tree.predict([
            features(row) for row in validation
        ])

        tree_predictions = [
            max(0, row["initial"] + float(change))
            for row, change in zip(
                validation, predicted_changes, strict=True
            )
        ]

        previous_model = MedianChangeModel(True).fit(training)

        predictions = {
            "persistence": [row["initial"] for row in validation],
            "recent_trend": [predict_trend(row) for row in validation],
            "learned_history": [
                previous_model.predict(row) for row in validation
            ],
            "decision_tree": tree_predictions,
        }

        scores = {
            name: score(validation, values)
            for name, values in predictions.items()
        }

        folds.append({
            "date": str(day),
            "training_pairs": len(training),
            "validation_pairs": len(validation),
            "metrics": scores,
            "tree_depth": int(tree.get_depth()),
            "tree_leaves": int(tree.get_n_leaves()),
        })

        print(
            f"{day} | n={len(validation)} | "
            f"persistence={scores['persistence']['mae_minutes']:.3f} | "
            f"learned={scores['learned_history']['mae_minutes']:.3f} | "
            f"tree={scores['decision_tree']['mae_minutes']:.3f}",
            flush=True,
        )

        day += timedelta(days=1)

    total_pairs = sum(fold["validation_pairs"] for fold in folds)

    pooled = {
        name: sum(
            fold["metrics"][name]["mae_minutes"]
            * fold["validation_pairs"]
            for fold in folds
        ) / total_pairs
        for name in predictions
    }

    report = {
        "sklearn_version": sklearn.__version__,
        "features": FEATURE_NAMES,
        "tree_settings": TREE_SETTINGS,
        "target": "Later reported delay minus current reported delay",
        "scope": "Conditional observed updates 8–12 minutes later",
        "validation_pairs": total_pairs,
        "pooled_mae_minutes": pooled,
        "folds": folds,
        "limitations": [
            "Development comparison, not independent final testing.",
            "Tree uses squared-error training; evaluation uses MAE.",
            "Pairs overlap and missing unchanged reports bias sampling.",
            "Reported-delay prediction, not verified arrival accuracy.",
            "December 6–7 remains excluded.",
        ],
    }

    output = PROJECT / "data/processed/tree_development.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")

    print("\nPooled MAE in minutes:")
    for name, mae in pooled.items():
        print(f"{name}: {mae:.4f}")

    print(f"\nSaved: {output}")
    print("Reserved test dates NOT scored.")


if __name__ == "__main__":
    run()