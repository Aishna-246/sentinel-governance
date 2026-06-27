"""Hybrid PII scanner combining Indian PII regex recognizers and Presidio NER."""

import os
import sys
from typing import List, Dict, Any
import pandas as pd

# Allow running this file directly from anywhere in the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sentinel.scanner.regex_recognizers import IndianPIIRecognizers
from sentinel.scanner.presidio_engine import PresidioNEREngine

DPDP_CATEGORY_MAP = {
    "AADHAAR_NUMBER": "identifier",
    "PAN_NUMBER": "identifier",
    "VOTER_ID": "identifier",
    "INDIAN_PASSPORT": "identifier",
    "INDIAN_MOBILE": "contact",
    "PHONE_NUMBER": "contact",
    "EMAIL_ADDRESS": "contact",
    "PERSON": "personal_name",
    "LOCATION": "location",
    "DATE_TIME": "date",
    "CREDIT_CARD": "financial",
}

INDIAN_ENTITIES = {
    "AADHAAR_NUMBER",
    "PAN_NUMBER",
    "VOTER_ID",
    "INDIAN_PASSPORT",
    "INDIAN_MOBILE",
}


class HybridPIIScanner:
    """Combines Indian PII regex recognizers and Presidio NER for PII classification."""

    def __init__(self):
        """Initialize the scanner with both standard Presidio NER and Indian PII recognizers."""
        self.ner_engine = PresidioNEREngine()
        self.analyzer = self.ner_engine.analyzer

        # Register Indian PII recognizers
        for recognizer in IndianPIIRecognizers.get_all():
            self.analyzer.registry.add_recognizer(recognizer)

    def scan_dataframe(self, df: pd.DataFrame, sample_size: int = 20) -> List[Dict[str, Any]]:
        """Scan a pandas DataFrame for PII columns."""
        results = []

        for column_name in df.columns:
            # 1. Take up to sample_size sample values (drop nulls, convert to string)
            samples = df[column_name].dropna().astype(str).tolist()
            samples = samples[:sample_size]

            if not samples:
                # Handle empty column
                results.append(
                    {
                        "column_name": column_name,
                        "is_pii": False,
                        "status": "clean",
                        "confidence": 0.0,
                        "entity_type": "none",
                        "dpdp_category": "none",
                        "detection_method": "none",
                        "sample_hits": 0,
                        "total_samples": 0,
                    }
                )
                continue

            # 2. For each sample run the combined AnalyzerEngine
            indian_hits = []
            ner_hits = []
            sample_hits = 0

            for sample_str in samples:
                hits = self.analyzer.analyze(text=sample_str, language="en")
                if hits:
                    sample_hits += 1
                    for hit in hits:
                        if hit.entity_type in INDIAN_ENTITIES:
                            indian_hits.append(hit)
                        else:
                            ner_hits.append(hit)

            # 4. Compute confidence & detection method
            if indian_hits:
                confidence = max(hit.score for hit in indian_hits)
                detection_method = "indian_regex"
                # Pick the highest scoring Indian hit
                primary_hit = max(indian_hits, key=lambda h: h.score)
                entity_type = primary_hit.entity_type
            elif ner_hits:
                confidence = max(hit.score for hit in ner_hits)
                detection_method = "presidio_ner"
                # Pick the highest scoring NER hit
                primary_hit = max(ner_hits, key=lambda h: h.score)
                entity_type = primary_hit.entity_type
            else:
                confidence = 0.0
                detection_method = "none"
                entity_type = None

            # Bug 2 Post-processing:
            # If the only entity type detected is ORGANIZATION and no Indian-specific entity was found
            all_detected_types = {hit.entity_type for hit in (indian_hits + ner_hits)}
            if all_detected_types == {"ORGANIZATION"}:
                confidence -= 0.40

            # 5. Classify status
            if confidence >= 0.85:
                is_pii = True
                status = "confirmed"
            elif 0.50 <= confidence < 0.85:
                is_pii = True
                status = "review_required"
            else:
                is_pii = False
                status = "clean"

            # Bug 1 Fix:
            # When a column's final status is "clean" (is_pii=False),
            # the returned dict should have entity_type="none" and dpdp_category="none"
            if is_pii:
                dpdp_category = DPDP_CATEGORY_MAP.get(entity_type, "unknown") if entity_type else "unknown"
            else:
                entity_type = "none"
                dpdp_category = "none"

            results.append(
                {
                    "column_name": column_name,
                    "is_pii": is_pii,
                    "status": status,
                    "confidence": confidence,
                    "entity_type": entity_type,
                    "dpdp_category": dpdp_category,
                    "detection_method": detection_method,
                    "sample_hits": sample_hits,
                    "total_samples": len(samples),
                }
            )

        return results

    def scan_csv(self, filepath: str) -> List[Dict[str, Any]]:
        """Load CSV with pandas, call scan_dataframe, and return results."""
        df = pd.read_csv(filepath)
        return self.scan_dataframe(df)

    def scan_text(self, text: str) -> Dict[str, Any]:
        """Run the combined AnalyzerEngine on a raw string."""
        results = self.analyzer.analyze(text=text, language="en")
        entity_types = sorted(list({r.entity_type for r in results}))
        confidence = max([r.score for r in results]) if results else 0.0
        pii_detected = any(r.score >= 0.50 for r in results)

        return {
            "pii_detected": pii_detected,
            "entity_types": entity_types,
            "confidence": confidence,
        }


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    # Create demo folder if it doesn't exist
    os.makedirs("demo", exist_ok=True)

    csv_path = "demo/test_pii.csv"

    # Define test data
    data = {
        "aadhaar_no": [
            "1234 5678 9012",
            "9876 5432 1098",
            "1111 2222 3333",
            "4444 5555 6666",
            "7777 8888 9999",
        ],
        "pan_number": [
            "ABCDE1234F",
            "XYZAB9876G",
            "PQRST5678H",
            "LMNOP2345I",
            "FGHIJ6789K",
        ],
        "full_name": [
            "Rahul Sharma",
            "Priya Patel",
            "Amit Kumar",
            "Sneha Singh",
            "Vikram Gupta",
        ],
        "loan_amount": ["250000", "75000", "500000", "125000", "350000"],
        "mobile": [
            "9876543210",
            "8765432109",
            "7654321098",
            "9123456789",
            "8234567890",
        ],
        "user_segment": [
            "AGE_25_35",
            "PREMIUM",
            "AGE_36_45",
            "STANDARD",
            "AGE_18_24",
        ],
    }

    # Save to CSV
    df_test = pd.DataFrame(data)
    df_test.to_csv(csv_path, index=False)
    print(f"Created test PII dataset at {csv_path}")

    # Run scanner
    scanner = HybridPIIScanner()
    scan_results = scanner.scan_csv(csv_path)

    # Initialize Rich Table
    console = Console()
    table = Table(title="Hybrid PII Scanner Results")
    table.add_column("Column", justify="left", style="cyan", no_wrap=True)
    table.add_column("PII?", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Confidence", justify="right")
    table.add_column("Entity Type", justify="left")
    table.add_column("DPDP Category", justify="left")

    for row in scan_results:
        status = row["status"]
        if status == "confirmed":
            color = "bold red"
        elif status == "review_required":
            color = "bold yellow"
        else:
            color = "bold green"

        table.add_row(
            row["column_name"],
            f"[{color}]{row['is_pii']}[/{color}]",
            f"[{color}]{status}[/]",
            f"[{color}]{row['confidence']:.2f}[/]",
            str(row["entity_type"] or "N/A"),
            row["dpdp_category"],
        )

    console.print(table)
