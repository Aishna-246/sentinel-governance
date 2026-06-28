import json
import os
from rich.console import Console


class LineageGraphBuilder:
    def __init__(self) -> None:
        self.console = Console()

    def build_graph(self, model_cards: list[dict]) -> dict:
        nodes: list[dict] = []
        edges: list[dict] = []

        for index, model_card in enumerate(model_cards):
            y_position = index * 200
            model_name = model_card.get("model_name", "")
            version = model_card.get("version", "")
            stage = model_card.get("stage", "")
            dpdp_risk = model_card.get("dpdp_risk", "")
            pii_columns = model_card.get("pii_columns", []) or []
            training_dataset = model_card.get("training_dataset", "")
            external_api = model_card.get("external_api", "") or ""
            sends_pii_risk = model_card.get("sends_pii_risk", "false")
            has_vendor = bool(str(external_api).strip())
            has_dataset = bool(str(training_dataset).strip())

            dataset_node_id = f"ds_{model_name}"
            model_node_id = f"model_{model_name}"
            api_node_id = f"api_{model_name}"
            vendor_node_id = f"vendor_{external_api}_{model_name}" if has_vendor else None
            decision_node_id = f"decision_{model_name}"
            audit_node_id = f"audit_{model_name}"

            if has_dataset:
                nodes.append(
                    {
                        "id": dataset_node_id,
                        "type": "dataset",
                        "position": {"x": 0, "y": y_position},
                        "data": {
                            "label": os.path.basename(training_dataset),
                            "pii_columns": pii_columns,
                            "dpdp_risk": dpdp_risk,
                            "full_path": training_dataset,
                        },
                    }
                )

            nodes.append(
                {
                    "id": model_node_id,
                    "type": "model",
                    "position": {"x": 300, "y": y_position},
                    "data": {
                        "label": model_name,
                        "version": version,
                        "stage": stage,
                        "dpdp_risk": dpdp_risk,
                        "pii_columns": pii_columns,
                    },
                }
            )

            nodes.append(
                {
                    "id": api_node_id,
                    "type": "api",
                    "position": {"x": 600, "y": y_position},
                    "data": {
                        "label": "FastAPI Endpoint",
                        "endpoint": f"/predict/{model_name}",
                    },
                }
            )

            if has_vendor:
                nodes.append(
                    {
                        "id": vendor_node_id,
                        "type": "llm_vendor",
                        "position": {"x": 900, "y": y_position - 80},
                        "data": {
                            "label": str(external_api).upper(),
                            "provider": external_api,
                            "pii_risk": sends_pii_risk,
                        },
                    }
                )

            decision_position_y = y_position + 80 if has_vendor else y_position
            nodes.append(
                {
                    "id": decision_node_id,
                    "type": "decision",
                    "position": {"x": 900, "y": decision_position_y},
                    "data": {
                        "label": "Automated Decision",
                        "model": model_name,
                    },
                }
            )

            nodes.append(
                {
                    "id": audit_node_id,
                    "type": "audit",
                    "position": {"x": 1200, "y": y_position},
                    "data": {
                        "label": "Audit Log",
                        "retention_days": 365,
                    },
                }
            )

            def edge_data(pii_flow: bool) -> dict:
                data = {"pii_flow": pii_flow}
                if pii_flow:
                    data["style"] = {
                        "stroke": "#C0392B",
                        "strokeDasharray": "5,5",
                    }
                return data

            if has_dataset:
                edges.append(
                    {
                        "id": f"edge_{dataset_node_id}_{model_node_id}",
                        "source": dataset_node_id,
                        "target": model_node_id,
                        "type": "smoothstep",
                        "animated": False,
                        "data": edge_data(bool(pii_columns)),
                    }
                )

            edges.append(
                {
                    "id": f"edge_{model_node_id}_{api_node_id}",
                    "source": model_node_id,
                    "target": api_node_id,
                    "type": "smoothstep",
                    "animated": False,
                    "data": edge_data(bool(pii_columns)),
                }
            )

            if has_vendor and vendor_node_id:
                edges.append(
                    {
                        "id": f"edge_{api_node_id}_{vendor_node_id}",
                        "source": api_node_id,
                        "target": vendor_node_id,
                        "type": "smoothstep",
                        "animated": False,
                        "data": edge_data(True),
                    }
                )

            edges.append(
                {
                    "id": f"edge_{api_node_id}_{decision_node_id}",
                    "source": api_node_id,
                    "target": decision_node_id,
                    "type": "smoothstep",
                    "animated": False,
                    "data": edge_data(False),
                }
            )

            edges.append(
                {
                    "id": f"edge_{decision_node_id}_{audit_node_id}",
                    "source": decision_node_id,
                    "target": audit_node_id,
                    "type": "smoothstep",
                    "animated": False,
                    "data": edge_data(False),
                }
            )

        return {"nodes": nodes, "edges": edges}

    def save_graph(self, model_cards: list[dict], output_path: str = "docs/lineage_graph.json") -> dict:
        graph = self.build_graph(model_cards)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(graph, output_file, indent=2)
        node_count = len(graph.get("nodes", []))
        edge_count = len(graph.get("edges", []))
        self.console.print(f"Lineage graph saved to {output_path}")
        self.console.print(f"Nodes: {node_count}, Edges: {edge_count}")
        return graph


if __name__ == "__main__":
    default_path = os.path.join("docs", "model_cards.json")
    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as cards_file:
            model_cards = json.load(cards_file)
    else:
        model_cards = [
            {
                "model_name": "test_model",
                "version": "1",
                "stage": "Production",
                "dpdp_risk": "high",
                "pii_columns": ["aadhaar_no", "pan_number"],
                "training_dataset": "demo/test_data.csv",
                "external_api": "groq",
                "sends_pii_risk": "true",
            }
        ]

    builder = LineageGraphBuilder()
    graph = builder.save_graph(model_cards)
    print(f"Total nodes: {len(graph.get('nodes', []))}, Total edges: {len(graph.get('edges', []))}")
