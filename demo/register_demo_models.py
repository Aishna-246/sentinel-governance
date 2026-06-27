"""Register 3 demo models in MLflow to simulate RupeeScore AI.

This script populates a local MLflow registry at http://localhost:5000
with three fictional Indian fintech models so that Sentinel can crawl and
display governance metadata without needing a real production registry.

Models registered
-----------------
1. rupee_credit_scorer   — Logistic Regression credit-scoring model (Production)
2. fraud_flag_classifier — Random Forest fraud-detection model (Staging)
3. support_chatbot_groq  — LLM proxy wrapper via Groq API (Production)

Usage::

    python demo/register_demo_models.py
"""

import io
import sys

# MLflow 3.x prints emoji characters when ending runs (e.g. 🏃).
# On Windows with the default cp1252 console encoding this raises a
# UnicodeEncodeError inside MLflow's own internals.  Reconfigure stdout/stderr
# to UTF-8 so the emoji passes through cleanly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time

import mlflow
import mlflow.sklearn
import numpy as np
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

MLFLOW_URI = "http://localhost:5000"

mlflow.set_tracking_uri(MLFLOW_URI)
client = MlflowClient()

# Shared dummy training data — same shape for all sklearn models
np.random.seed(42)
X = np.random.rand(100, 5)
y = np.random.randint(0, 2, 100)


def _transition(model_name: str, version: str, stage: str) -> None:
    """Transition a registered model version to the given stage."""
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=False,
    )


def _set_model_tags(model_name: str, version: str, tags: dict[str, str]) -> None:
    """Write governance tags to both the registered model and the model version.

    ``mlflow.set_tags()`` inside a run sets *run-level* tags, which are NOT
    surfaced by ``get_registered_model()`` or ``get_model_version()``.
    This helper writes to the correct registry objects so that
    ``RegistryConnector.get_model_card()`` can read them.
    """
    for key, value in tags.items():
        client.set_registered_model_tag(model_name, key, value)
        client.set_model_version_tag(model_name, version, key, value)


# ---------------------------------------------------------------------------
# Model 1 — rupee_credit_scorer (LogisticRegression)
# ---------------------------------------------------------------------------

with mlflow.start_run(run_name="credit_scorer_training") as run1:
    model1 = LogisticRegression(max_iter=200)
    model1.fit(X, y)

    mlflow.log_params({"model_type": "logistic_regression", "features": 5})
    mlflow.log_metric("accuracy", 0.82)
    mlflow.sklearn.log_model(model1, "model")

    mlflow.set_tags(
        {
            "pii_columns": "aadhaar_hash,pan_number,mobile,full_name",
            "training_dataset": "demo/rupee_credit_data.csv",
            "dpdp_risk": "high",
            "model_type": "classification",
        }
    )
    run1_id = run1.info.run_id

mv1 = mlflow.register_model(
    model_uri=f"runs:/{run1_id}/model",
    name="rupee_credit_scorer",
)
# Allow MLflow time to finalise registration before transitioning
time.sleep(2)
_transition("rupee_credit_scorer", mv1.version, "Production")
_set_model_tags(
    "rupee_credit_scorer",
    mv1.version,
    {
        "pii_columns": "aadhaar_hash,pan_number,mobile,full_name",
        "training_dataset": "demo/rupee_credit_data.csv",
        "dpdp_risk": "high",
        "model_type": "classification",
    },
)
print("Registered rupee_credit_scorer -> Production")

# ---------------------------------------------------------------------------
# Model 2 — fraud_flag_classifier (RandomForestClassifier)
# ---------------------------------------------------------------------------

with mlflow.start_run(run_name="fraud_classifier_training") as run2:
    model2 = RandomForestClassifier(n_estimators=100, random_state=42)
    model2.fit(X, y)

    mlflow.log_params({"model_type": "random_forest", "n_estimators": 100})
    mlflow.log_metric("accuracy", 0.91)
    mlflow.sklearn.log_model(model2, "model")

    mlflow.set_tags(
        {
            "pii_columns": "device_id,ip_address,pan_number,email",
            "training_dataset": "demo/fraud_training_data.csv",
            "dpdp_risk": "medium",
            "model_type": "classification",
        }
    )
    run2_id = run2.info.run_id

mv2 = mlflow.register_model(
    model_uri=f"runs:/{run2_id}/model",
    name="fraud_flag_classifier",
)
time.sleep(2)
_transition("fraud_flag_classifier", mv2.version, "Staging")
_set_model_tags(
    "fraud_flag_classifier",
    mv2.version,
    {
        "pii_columns": "device_id,ip_address,pan_number,email",
        "training_dataset": "demo/fraud_training_data.csv",
        "dpdp_risk": "medium",
        "model_type": "classification",
    },
)
print("Registered fraud_flag_classifier -> Staging")

# ---------------------------------------------------------------------------
# Model 3 — support_chatbot_groq (LLM proxy — placeholder sklearn model)
# ---------------------------------------------------------------------------

with mlflow.start_run(run_name="chatbot_config") as run3:
    # LLM API wrapper: no real training — log a trivial placeholder model
    # so MLflow has a valid artifact URI to register against.
    placeholder = LogisticRegression(max_iter=1)
    placeholder.fit(X, y)
    mlflow.sklearn.log_model(placeholder, "model")

    mlflow.log_params(
        {
            "provider": "groq",
            "model": "llama3-8b-8192",
            "temperature": 0.7,
        }
    )

    mlflow.set_tags(
        {
            "model_type": "llm_proxy",
            "external_api": "groq",
            "sends_pii_risk": "true",
            "dpdp_risk": "high",
            "training_dataset": "",
            "pii_columns": "",
        }
    )
    run3_id = run3.info.run_id

mv3 = mlflow.register_model(
    model_uri=f"runs:/{run3_id}/model",
    name="support_chatbot_groq",
)
time.sleep(2)
_transition("support_chatbot_groq", mv3.version, "Production")
_set_model_tags(
    "support_chatbot_groq",
    mv3.version,
    {
        "model_type": "llm_proxy",
        "external_api": "groq",
        "sends_pii_risk": "true",
        "dpdp_risk": "high",
        "training_dataset": "",
        "pii_columns": "",
    },
)
print("Registered support_chatbot_groq -> Production")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print()
print("All 3 RupeeScore AI models registered successfully.")
print("Open http://localhost:5000 to verify.")
