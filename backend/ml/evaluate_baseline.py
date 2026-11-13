"""
Evaluate the saved baseline risk model and make charts for the presentation.

Run from backend/ (after train_baseline.py has saved a model):
    python -m ml.evaluate_baseline            # full cleaned data in ml/data/clean
    python -m ml.evaluate_baseline --sample   # 500-row committed sample

Writes PNGs and evaluation_metrics.json to ml/reports/.
"""

import argparse
import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix

from ml.datasets import load_pitcher_games
from ml.train_baseline import (
    FEATURES,
    MODEL_DIR,
    add_features,
    evaluate,
    make_models,
    make_risk_label,
    split_by_date,
)

REPORT_DIR = Path(__file__).parent / "reports"

# The high-risk label is built straight from these columns, so a model that sees them
# can just relearn the rule instead of predicting anything new.
LABEL_COLUMNS = ["pitch_count", "days_rest", "velo_drop"]
# Columns that are close stand-ins for the label columns (pitch_count -> batters faced and
# innings, velo_drop -> this game's fastball velo).
PROXY_COLUMNS = ["batters_faced", "innings_pitched_approx", "avg_fastball_velo"]

FEATURE_SETS = {
    "all_features": FEATURES,
    "no_label_columns": [f for f in FEATURES if f not in LABEL_COLUMNS],
    "no_label_or_proxy_columns": [f for f in FEATURES if f not in LABEL_COLUMNS + PROXY_COLUMNS],
}

NICE_NAMES = {
    "pitch_count": "Pitch count",
    "batters_faced": "Batters faced",
    "innings_pitched_approx": "Innings pitched",
    "avg_velo": "Avg velo (all pitches)",
    "max_velo": "Max velo",
    "min_velo": "Min velo",
    "velo_std": "Velo std dev",
    "avg_spin": "Avg spin",
    "max_spin": "Max spin",
    "avg_extension": "Avg extension",
    "avg_release_pos_x": "Release point (x)",
    "avg_release_pos_z": "Release point (z)",
    "fastball_pct": "Fastball %",
    "avg_fastball_velo": "Avg fastball velo",
    "max_fastball_velo": "Max fastball velo",
    "days_rest": "Days rest",
    "throws_left": "Throws left",
    "velo_drop": "Velo drop vs own avg",
}


def load_games(sample=False, seasons=None):
    # same steps as train_baseline.main so the split matches training
    games = load_pitcher_games(seasons=seasons, sample=sample)
    games = games[games["avg_velo"] >= 75]
    games = add_features(games)
    games["high_risk"] = make_risk_label(games)
    return games


def feature_importance(model, features):
    clf = model.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        values = clf.feature_importances_
    else:  # logistic regression: size of the (scaled) coefficient
        values = abs(clf.coef_[0])
    pairs = sorted(zip(features, values), key=lambda p: p[1], reverse=True)
    return [(f, round(float(v), 4)) for f, v in pairs]


def plot_importance(pairs, title, path, top=10, highlight=()):
    pairs = pairs[:top][::-1]
    names = [NICE_NAMES.get(f, f) for f, _ in pairs]
    values = [v for _, v in pairs]
    colors = ["#d62728" if f in highlight else "#1f77b4" for f, _ in pairs]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(names, values, color=colors)
    ax.set_title(title, fontsize=18)
    ax.set_xlabel("Importance", fontsize=14)
    ax.tick_params(labelsize=13)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if highlight:
        ax.text(0.99, 0.02, "red = column used to build the label", transform=ax.transAxes,
                ha="right", fontsize=12, color="#d62728")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_confusion(cm, title, path):
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.imshow(cm, cmap="Blues")
    labels = ["Low risk", "High risk"]
    ax.set_xticks([0, 1], labels=labels, fontsize=13)
    ax.set_yticks([0, 1], labels=labels, fontsize=13)
    ax.set_xlabel("Predicted", fontsize=14)
    ax.set_ylabel("Actual", fontsize=14)
    ax.set_title(title, fontsize=16)
    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=20, color=color)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_f1_comparison(results, path):
    groups = list(FEATURE_SETS)
    group_labels = ["All features", "Without label\ncolumns", "Without label +\nproxy columns"]
    models = ["logistic_regression", "random_forest"]
    model_labels = ["Logistic regression", "Random forest"]
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 6))
    for k, (m, label) in enumerate(zip(models, model_labels)):
        xs = [i + (k - 0.5) * width for i in range(len(groups))]
        ys = [results[g][m]["f1"] for g in groups]
        bars = ax.bar(xs, ys, width, label=label)
        for bar, y in zip(bars, ys):
            ax.text(bar.get_x() + bar.get_width() / 2, y + 0.015, f"{y:.2f}",
                    ha="center", fontsize=13)
    ax.set_xticks(range(len(groups)), labels=group_labels, fontsize=13)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("F1 score (high-risk class)", fontsize=14)
    ax.set_title("F1 on held-out games, with and without label columns", fontsize=16)
    ax.legend(fontsize=12, frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="use the 500-row committed sample")
    parser.add_argument("--seasons", nargs="+", type=int, default=None)
    parser.add_argument("--model", default=str(MODEL_DIR / "baseline_risk.joblib"))
    parser.add_argument("--out", default=str(REPORT_DIR))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    games = load_games(sample=args.sample, seasons=args.seasons)
    train, test = split_by_date(games)
    y_train, y_test = train["high_risk"], test["high_risk"]
    print(f"Rows: {len(games)}  train: {len(train)}  test: {len(test)}  "
          f"high-risk share: {games['high_risk'].mean():.1%}")

    # 1) the saved model as-is
    saved = joblib.load(args.model)
    saved_model, saved_features = saved["model"], saved["features"]
    saved_metrics = evaluate(saved_model, test[saved_features], y_test)
    cm = confusion_matrix(y_test, saved_model.predict(test[saved_features]), labels=[0, 1])
    importance = feature_importance(saved_model, saved_features)
    print(f"saved model ({saved['name']}): {saved_metrics}")
    print("confusion matrix [[TN, FP], [FN, TP]]:", cm.tolist())
    print("top features:", importance[:5])

    # 2) retrain on the same split with and without the columns the label is built from
    results, fitted = {}, {}
    for set_name, cols in FEATURE_SETS.items():
        results[set_name] = {}
        for name, model in make_models().items():
            model.fit(train[cols], y_train)
            fitted[(set_name, name)] = model
            results[set_name][name] = evaluate(model, test[cols], y_test)
            print(set_name, name, results[set_name][name])

    clean_rf = fitted[("no_label_columns", "random_forest")]
    clean_cols = FEATURE_SETS["no_label_columns"]
    clean_importance = feature_importance(clean_rf, clean_cols)
    clean_cm = confusion_matrix(y_test, clean_rf.predict(test[clean_cols]), labels=[0, 1])

    plot_importance(importance, f"Saved baseline ({saved['name'].replace('_', ' ')}): top features",
                    out / "feature_importance.png", highlight=LABEL_COLUMNS)
    plot_importance(clean_importance, "Random forest without label columns: top features",
                    out / "feature_importance_no_label_columns.png")
    plot_confusion(cm, "Saved baseline: confusion matrix", out / "confusion_matrix.png")
    plot_f1_comparison(results, out / "f1_comparison.png")

    with open(out / "evaluation_metrics.json", "w") as f:
        json.dump({
            "data": "sample" if args.sample else f"clean pitcher_games, seasons={args.seasons or 'all'}",
            "rows": len(games), "train_rows": len(train), "test_rows": len(test),
            "high_risk_share": round(float(games["high_risk"].mean()), 4),
            "test_high_risk_share": round(float(y_test.mean()), 4),
            "saved_model": {"name": saved["name"], "metrics": saved_metrics,
                            "confusion_matrix": cm.tolist(), "feature_importance": importance},
            "retrained": results,
            "no_label_columns_rf": {"confusion_matrix": clean_cm.tolist(),
                                    "feature_importance": clean_importance},
        }, f, indent=2)
    print(f"Wrote charts and evaluation_metrics.json to {out}")


if __name__ == "__main__":
    main()
