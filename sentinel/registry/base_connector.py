"""Abstract base class for ML model registry connectors.
To add a new registry (e.g. SageMaker), create a new file
sentinel/registry/sagemaker_connector.py and implement this interface.
Only MLflow is implemented in v1.
"""

from abc import ABC, abstractmethod

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


class RegistryConnector(ABC):
    """Abstract base class that every registry connector must subclass.

    Subclasses are expected to implement all ``@abstractmethod`` members.
    The concrete :py:meth:`crawl_all` method is shared across all connectors
    and should **not** be overridden unless there is a compelling reason.
    """

    # ------------------------------------------------------------------
    # Abstract interface -- every connector MUST implement the items below
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def connector_name(self) -> str:
        """Return a human-readable name for this connector.

        Examples:
            ``"MLflow"``, ``"SageMaker"``, ``"VertexAI"``
        """

    @abstractmethod
    def connect(self) -> bool:
        """Establish a connection to the model registry.

        Returns:
            ``True`` if the connection was established successfully,
            ``False`` otherwise.

        Note:
            Implementations **must not** raise exceptions -- all errors
            should be caught internally and result in a ``False`` return
            value.
        """

    @abstractmethod
    def list_models(self) -> list[dict]:
        """Return a list of all registered models.

        Returns:
            A list of dicts, each containing **at minimum**:

            * ``name``            -- registered model name
            * ``description``     -- free-text description
            * ``tags``            -- dict of key/value tags
            * ``latest_version``  -- latest version string
        """

    @abstractmethod
    def get_model_versions(self, model_name: str) -> list[dict]:
        """Return all versions of a registered model.

        Args:
            model_name: The registered name of the model.

        Returns:
            A list of dicts, each containing **at minimum**:

            * ``version``              -- version string (e.g. ``"3"``)
            * ``stage``                -- lifecycle stage (e.g. ``"Production"``)
            * ``creation_timestamp``   -- Unix ms timestamp of creation
            * ``source_run_id``        -- MLflow / tracker run ID
            * ``artifact_uri``         -- URI pointing to stored artifacts
            * ``tags``                 -- dict of version-level tags
        """

    @abstractmethod
    def get_model_card(self, model_name: str, version: str) -> dict:
        """Return the full model card for a specific model version.

        Args:
            model_name: The registered name of the model.
            version:    The version string to retrieve.

        Returns:
            A dict containing **at minimum**:

            * ``model_name``           -- registered model name
            * ``version``              -- version string
            * ``stage``                -- lifecycle stage
            * ``creation_timestamp``   -- Unix ms timestamp of creation
            * ``tags``                 -- combined model + version tags
            * ``training_dataset``     -- name / URI of the training dataset
            * ``pii_columns``          -- list of PII column names
            * ``dpdp_risk``            -- DPDP risk classification string
            * ``external_api``         -- bool; ``True`` if the model calls
                                         an external API
        """

    # ------------------------------------------------------------------
    # Concrete shared implementation
    # ------------------------------------------------------------------

    def crawl_all(self) -> list[dict]:
        """Connect to the registry and crawl model cards for every model.

        The method:

        1. Calls :py:meth:`connect`.  If it returns ``False``, a
           :py:exc:`ConnectionError` is raised immediately.
        2. Calls :py:meth:`list_models` to discover all registered models.
        3. For each model, calls :py:meth:`get_model_card` using the
           model's ``latest_version``.
        4. Displays a Rich progress bar while iterating.

        Returns:
            A list of model-card dicts -- one per registered model.

        Raises:
            ConnectionError: If :py:meth:`connect` returns ``False``.
        """
        if not self.connect():
            raise ConnectionError(
                f"[{self.connector_name}] Failed to connect to the model registry. "
                "Check your credentials and network access."
            )

        models = self.list_models()
        model_cards: list[dict] = []

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        )

        with progress:
            task = progress.add_task(
                f"[{self.connector_name}] Crawling models...",
                total=len(models),
            )
            for model in models:
                model_name: str = model["name"]
                latest_version: str = model["latest_version"]
                card = self.get_model_card(model_name, latest_version)
                model_cards.append(card)
                progress.advance(task)

        print(f"[{self.connector_name}] Crawled {len(model_cards)} models successfully")
        return model_cards


# Future connectors -- implement RegistryConnector to add support:
# class SageMakerConnector(RegistryConnector): ...
# class VertexAIConnector(RegistryConnector): ...
# class AzureMLConnector(RegistryConnector): ...
