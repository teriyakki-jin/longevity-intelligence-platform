"""Biological age clock training pipeline with Optuna HPO and MLflow logging."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import optuna
import pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import KBinsDiscretizer

from longevity.common.config import load_yaml_config
from longevity.common.logging import configure_logging, get_logger
from longevity.models.bioage.blood_clock import BLOOD_CLOCK_FEATURES, BloodAgeClock

logger = get_logger(__name__)

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _prepare_stratification_labels(y: pd.Series, n_bins: int = 10) -> np.ndarray:
    """Create age decile labels for stratified CV."""
    discretizer = KBinsDiscretizer(n_bins=n_bins, encode="ordinal", strategy="quantile")
    return discretizer.fit_transform(y.values.reshape(-1, 1)).ravel().astype(int)


def _compute_cv_mae(
    X: pd.DataFrame,
    y: pd.Series,
    params: dict[str, Any],
    n_folds: int = 5,
) -> float:
    """Compute cross-validated MAE for a given LightGBM parameter set."""
    import lightgbm as lgb

    strat_labels = _prepare_stratification_labels(y)
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    maes = []
    for train_idx, val_idx in skf.split(X, strat_labels):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(period=-1)],
        )
        preds = model.predict(X_val)
        maes.append(float(np.mean(np.abs(preds - y_val))))

    return float(np.mean(maes))


def build_optuna_objective(X: pd.DataFrame, y: pd.Series, n_folds: int):
    """Build Optuna objective function for HPO."""
    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective": "regression",
            "metric": "mae",
            "verbosity": -1,
            "random_state": 42,
            "n_estimators": trial.suggest_int("n_estimators", 200, 2000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
            "num_leaves": trial.suggest_int("num_leaves", 20, 300),
        }
        return _compute_cv_mae(X, y, params, n_folds)

    return objective


def train_bioage_clock(
    data_path: str | Path,
    config_path: str | Path = "config/bioage.yaml",
    output_dir: str | Path = "models/bioage",
    n_hpo_trials: int = 100,
    n_cv_folds: int = 5,
) -> BloodAgeClock:
    """Full training pipeline for the biological age blood clock.

    Args:
        data_path: Path to processed NHANES feature parquet.
        config_path: Path to bioage config YAML.
        output_dir: Directory to save trained model.
        n_hpo_trials: Number of Optuna HPO trials.
        n_cv_folds: Number of cross-validation folds.

    Returns:
        Fitted BloodAgeClock model.
    """
    config = load_yaml_config(config_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("loading_training_data", path=str(data_path))
    df = pd.read_parquet(data_path)

    # Filter to adults with age data
    df = df.dropna(subset=["age_years"])
    df = df[df["age_years"].between(18, 85)].copy()

    # Prepare feature matrix
    feature_cols = [c for c in BLOOD_CLOCK_FEATURES if c in df.columns and c != "sex_encoded"]
    if "sex" in df.columns:
        feature_cols.append("sex")

    X = df[feature_cols].copy()
    y = df["age_years"].copy()

    logger.info("training_data_ready", n_samples=len(X), n_features=len(X.columns))

    # Train/validation split (80/20 stratified)
    strat_labels = _prepare_stratification_labels(y)
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=strat_labels
    )

    mlflow.set_experiment(config.get("output", {}).get("mlflow_experiment", "bioage-blood-clock"))

    with mlflow.start_run(run_name="bioage_hpo"):
        mlflow.log_params({
            "n_samples": len(X_train),
            "n_features": len(X_train.columns),
            "n_hpo_trials": n_hpo_trials,
            "n_cv_folds": n_cv_folds,
        })

        # Phase 1: HPO with Optuna
        logger.info("starting_hpo", n_trials=n_hpo_trials)
        study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        study.optimize(
            build_optuna_objective(X_train, y_train, n_cv_folds),
            n_trials=n_hpo_trials,
            show_progress_bar=True,
        )

        best_params = study.best_params
        best_cv_mae = study.best_value
        logger.info("hpo_complete", best_cv_mae=f"{best_cv_mae:.3f}", best_params=best_params)
        mlflow.log_metric("best_cv_mae", best_cv_mae)
        mlflow.log_params({f"best_{k}": v for k, v in best_params.items()})

        # Phase 2: Train final model on full training set
        best_params.update({"objective": "regression", "metric": "mae",
                             "verbosity": -1, "random_state": 42})
        clock = BloodAgeClock(params=best_params)
        clock.fit(X_train, y_train, eval_set=(X_val, y_val))

        # Phase 3: Evaluate on validation set
        val_result = clock.predict_biological_age(X_val, true_age=y_val)
        val_preds = np.array(val_result["biological_age"])
        val_true = y_val.values

        val_mae = float(np.mean(np.abs(val_preds - val_true)))
        val_r, _ = stats.pearsonr(val_preds, val_true)
        accel = val_preds - val_true

        logger.info(
            "validation_metrics",
            mae=f"{val_mae:.3f}",
            pearson_r=f"{val_r:.3f}",
            accel_mean=f"{accel.mean():.2f}",
            accel_std=f"{accel.std():.2f}",
        )
        mlflow.log_metrics({
            "val_mae": val_mae,
            "val_pearson_r": val_r,
            "accel_mean": float(accel.mean()),
            "accel_std": float(accel.std()),
        })

        # Save model
        model_path = out_dir / "blood_clock.joblib"
        clock.save(model_path)
        mlflow.log_artifact(str(model_path))

        logger.info("training_complete", model_path=str(model_path), val_mae=f"{val_mae:.3f}")

    return clock


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Train biological age blood clock")
    parser.add_argument("--data", default="data/processed/nhanes_features.parquet",
                        help="Path to processed feature parquet")
    parser.add_argument("--config", default="config/bioage.yaml")
    parser.add_argument("--output", default="models/bioage")
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    train_bioage_clock(
        data_path=args.data,
        config_path=args.config,
        output_dir=args.output,
        n_hpo_trials=args.trials,
        n_cv_folds=args.folds,
    )


if __name__ == "__main__":
    main()
