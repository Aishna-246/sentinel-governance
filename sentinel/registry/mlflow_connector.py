"""MLflow implementation of the RegistryConnector interface.

This module connects Sentinel to a running MLflow tracking server and
exposes all registered models and their governance metadata (tags,
PII columns, DPDP risk, etc.) via the standard RegistryConnector API.

Usage (CLI)::

    python -m sentinel.registry.mlflow_connector --mlflow-uri http://localhost:5000

Usage (programmatic)::

    from sentinel.registry.mlflow_connector import MLflowConnector

    connector = MLflowConnector("http://localhost:5000")
    cards = connector.crawl_all()
"""

import argparse
import json
import sys
from typing import Optional

import mlflow
from mlflow.tracking import MlflowClient
from rich.console import Console
from rich.table import Table

from sentinel.registry.base_connector import RegistryConnector

console = Console()


class MLflowConnector(RegistryConnector):
    """RegistryConnector implementation for MLflow Model Registry.

    Args:
        mlflow_uri: Base URL of the MLflow tracking server.
                    Defaults to ``"http://localhost:5000"``.

    Example::

        connector = MLflowConnector("http://mlflow.internal:5000")
        if connector.connect():
            cards = connector.crawl_all()
    """

    def __init__(self, mlflow_uri: str = "http://localhost:5000") -> None:
        self.mlflow_uri: str = mlflow_uri
        self._client: Optional[MlflowClient] = None

    # ------------------------------------------------------------------
    # Abstract interface implementation
    # ------------------------------------------------------------------

    @property
    def connector_name(self) -> str:
        """Return the human-readable connector name."""
        return "MLflow"

    def connect(self) -> bool:
        """Establish a connection to the MLflow tracking server.

        Sets the global tracking URI, instantiates :class:`MlflowClient`,
        and performs a lightweight ``search_registered_models`` probe to
        confirm the server is reachable.

        Returns:
            ``True`` if the connection succeeded, ``False`` otherwise.
        """
        try:
            mlflow.set_tracking_uri(self.mlflow_uri)
            self._client = MlflowClient()
            # Probe — will raise if the server is unreachable
            self._client.search_registered_models()
            return True
        except Exception as exc:  # noqa: BLE001
            print(
                f"[{self.connector_name}] Connection failed: {exc}",
                file=sys.stderr,
            )
            return False

    def list_models(self) -> list[dict]:
        """Return a list of all models in the MLflow Model Registry.

        Returns:
            List of dicts with keys:
            ``name``, ``description``, ``tags``, ``latest_version``.
        """
        registered_models = self._client.search_registered_models()
        result: list[dict] = []

        for model in registered_models:
            # latest_versions is sorted newest-first when present
            if model.latest_versions:
                latest_version = model.latest_versions[0].version
            else:
                latest_version = "1"

            result.append(
                {
                    "name": model.name,
                    "description": model.description or "",
                    "tags": dict(model.tags),
                    "latest_version": latest_version,
                }
            )

        return result

    def get_model_versions(self, model_name: str) -> list[dict]:
        """Return all registered versions for *model_name*.

        Args:
            model_name: Exact registered model name in MLflow.

        Returns:
            List of dicts with keys:
            ``version``, ``stage``, ``creation_timestamp``,
            ``source_run_id``, ``artifact_uri``, ``tags``.
        """
        versions = self._client.search_model_versions(f"name='{model_name}'")
        return [
            {
                "version": v.version,
                "stage": v.current_stage,
                "creation_timestamp": v.creation_timestamp,
                "source_run_id": v.run_id,
                "artifact_uri": v.source,
                "tags": dict(v.tags),
            }
            for v in versions
        ]

    def get_model_card(self, model_name: str, version: str) -> dict:
        """Return the full governance model card for a specific version.

        Model-level tags and version-level tags are merged (version tags
        take precedence on key collision) to form the unified ``tags``
        dict, from which governance fields are extracted.

        Args:
            model_name: Exact registered model name in MLflow.
            version:    Version string (e.g. ``"3"``).

        Returns:
            Dict containing governance metadata.  See
            :py:meth:`RegistryConnector.get_model_card` for the full
            required key set.
        """
        model = self._client.get_registered_model(model_name)
        model_version = self._client.get_model_version(model_name, version)

        # Merge tags: model-level first, version-level overrides
        tags: dict[str, str] = {**dict(model.tags), **dict(model_version.tags)}

        # Parse pii_columns — stored as a comma-separated string in tags
        raw_pii: str = tags.get("pii_columns", "")
        pii_columns: list[str] = [col.strip() for col in raw_pii.split(",") if col.strip()] if raw_pii else []

        return {
            "model_name": model_name,
            "version": version,
            "stage": model_version.current_stage,
            "creation_timestamp": model_version.creation_timestamp,
            "description": model.description or "",
            "tags": tags,
            "training_dataset": tags.get("training_dataset", ""),
            "pii_columns": pii_columns,
            "dpdp_risk": tags.get("dpdp_risk", "unknown"),
            "external_api": tags.get("external_api", ""),
            "model_type": tags.get("model_type", ""),
        }


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _build_table(cards: list[dict]) -> Table:
    """Build a Rich table from a list of model cards."""
    table = Table(
        title="[bold cyan]Sentinel — MLflow Model Registry[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        row_styles=["", "dim"],
    )
    table.add_column("Model Name", style="bold white", no_wrap=True)
    table.add_column("Version", justify="center")
    table.add_column("Stage", justify="center")
    table.add_column("DPDP Risk", justify="center")
    table.add_column("PII Columns")
    table.add_column("External API", justify="center")

    for card in cards:
        pii = ", ".join(card["pii_columns"]) if card["pii_columns"] else "[dim]none[/dim]"
        ext_api = card["external_api"] if card["external_api"] else "[dim]—[/dim]"

        # Colour-code DPDP risk for quick scanning
        risk = card["dpdp_risk"]
        if risk.lower() == "high":
            risk_display = f"[bold red]{risk}[/bold red]"
        elif risk.lower() == "medium":
            risk_display = f"[bold yellow]{risk}[/bold yellow]"
        elif risk.lower() == "low":
            risk_display = f"[bold green]{risk}[/bold green]"
        else:
            risk_display = f"[dim]{risk}[/dim]"

        table.add_row(
            card["model_name"],
            card["version"],
            card["stage"],
            risk_display,
            pii,
            ext_api,
        )

    return table


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="sentinel.registry.mlflow_connector",
        description="Crawl the MLflow Model Registry and display governance metadata.",
    )
    parser.add_argument(
        "--mlflow-uri",
        default="http://localhost:5000",
        metavar="URI",
        help="MLflow tracking server URI (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Dump raw model cards as JSON instead of a Rich table.",
    )
    args = parser.parse_args(argv)

    connector = MLflowConnector(mlflow_uri=args.mlflow_uri)

    try:
        cards = connector.crawl_all()
    except ConnectionError:
        console.print(
            "[bold red]MLflow not running.[/bold red] "
            "Start it with: [bold yellow]docker compose up mlflow -d[/bold yellow]"
        )
        sys.exit(1)

    if args.as_json:
        print(json.dumps(cards, indent=2, default=str))
    else:
        console.print(_build_table(cards))


if __name__ == "__main__":
    main()
