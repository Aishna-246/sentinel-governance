"""Presidio NER engine for general PII detection."""

from typing import List, Dict, Any
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider


class PresidioNEREngine:
    """Wrapper around Microsoft Presidio's AnalyzerEngine for general NER-based PII detection."""

    def __init__(self):
        """Initialize the Presidio NER engine using the spacy en_core_web_lg model."""
        config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
        }
        try:
            provider = NlpEngineProvider(nlp_configuration=config)
            nlp_engine = provider.create_engine()
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        except Exception as e:
            raise RuntimeError(
                "spaCy model not found. Run: python -m spacy download en_core_web_lg"
            ) from e

    def analyse_text(self, text: str) -> List[Dict[str, Any]]:
        """Analyze text to find general PII entities.

        Detects PERSON, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION, DATE_TIME,
        CREDIT_CARD, and IBAN_CODE.
        """
        entities_to_detect = [
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "LOCATION",
            "DATE_TIME",
            "CREDIT_CARD",
            "IBAN_CODE",
        ]
        results = self.analyzer.analyze(
            text=text, language="en", entities=entities_to_detect
        )

        output = []
        for r in results:
            output.append(
                {
                    "entity_type": r.entity_type,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "text_found": text[r.start : r.end],
                }
            )
        return output

    def analyse_column(self, column_name: str, samples: List[str]) -> Dict[str, Any]:
        """Run analyze_text on up to 20 samples from a column and aggregate results."""
        target_samples = samples[:20]
        entity_types_found = set()
        max_score = 0.0
        sample_hits = 0

        for sample in target_samples:
            found = self.analyse_text(sample)
            if found:
                sample_hits += 1
                for item in found:
                    entity_types_found.add(item["entity_type"])
                    if item["score"] > max_score:
                        max_score = item["score"]

        return {
            "column_name": column_name,
            "entity_types_found": sorted(list(entity_types_found)),
            "max_score": max_score,
            "sample_hits": sample_hits,
            "total_samples": len(target_samples),
        }


if __name__ == "__main__":
    import json

    try:
        engine = PresidioNEREngine()

        # Test 1: analyse_text
        text_sample = "Contact John Smith at john@example.com or 9876543210"
        print("=== Test 1: analyse_text ===")
        print(f"Input: '{text_sample}'")
        text_results = engine.analyse_text(text_sample)
        print("Output:")
        print(json.dumps(text_results, indent=2))
        print()

        # Test 2: analyse_column
        col_name = "notes"
        column_samples = [
            "email me at test@gmail.com",
            "no pii here",
            "call 9876543210",
        ]
        print("=== Test 2: analyse_column ===")
        print(f"Column: '{col_name}'")
        print(f"Samples: {column_samples}")
        column_results = engine.analyse_column(col_name, column_samples)
        print("Output:")
        print(json.dumps(column_results, indent=2))

    except Exception as err:
        print(f"Error occurred: {err}")
