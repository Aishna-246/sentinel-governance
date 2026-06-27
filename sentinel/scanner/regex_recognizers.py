"""Indian PII recognizers for Presidio Analyzer."""

from typing import List
from presidio_analyzer import Pattern, PatternRecognizer, AnalyzerEngine, RecognizerRegistry


class IndianPIIRecognizers:
    """Helper class to get all Indian PII recognizers compatible with Presidio."""

    @classmethod
    def get_all(cls) -> List[PatternRecognizer]:
        """Return a list of Presidio PatternRecognizer objects for Indian PII."""
        recognizers = []

        # 1. AADHAAR_NUMBER
        aadhaar_pattern = Pattern(
            name="aadhaar_pattern",
            regex=r"(\d{4}[- ]?\d{4}[- ]?\d{4})",
            score=0.95,
        )
        recognizers.append(
            PatternRecognizer(
                supported_entity="AADHAAR_NUMBER",
                patterns=[aadhaar_pattern],
                context=["aadhaar", "aadhar", "uid", "uidai"],
            )
        )

        # 2. PAN_NUMBER
        pan_pattern = Pattern(
            name="pan_pattern",
            regex=r"([A-Z]{5}[0-9]{4}[A-Z]{1})",
            score=0.95,
        )
        recognizers.append(
            PatternRecognizer(
                supported_entity="PAN_NUMBER",
                patterns=[pan_pattern],
                context=["pan", "permanent", "account"],
            )
        )

        # 3. INDIAN_MOBILE
        mobile_pattern_1 = Pattern(
            name="indian_mobile_pattern_1",
            regex=r"(\+91[\-\s]?)?[6-9]\d{9}",
            score=0.85,
        )
        mobile_pattern_2 = Pattern(
            name="indian_mobile_pattern_2",
            regex=r"(0)?[6-9]\d{9}",
            score=0.85,
        )
        recognizers.append(
            PatternRecognizer(
                supported_entity="INDIAN_MOBILE",
                patterns=[mobile_pattern_1, mobile_pattern_2],
                context=["mobile", "phone", "contact", "whatsapp"],
            )
        )

        # 4. VOTER_ID
        voter_pattern = Pattern(
            name="voter_pattern",
            regex=r"([A-Z]{3}[0-9]{7})",
            score=0.80,
        )
        recognizers.append(
            PatternRecognizer(
                supported_entity="VOTER_ID",
                patterns=[voter_pattern],
                context=["voter", "epic", "election"],
            )
        )

        # 5. INDIAN_PASSPORT
        passport_pattern = Pattern(
            name="passport_pattern",
            regex=r"([A-Z]{1}[0-9]{7})",
            score=0.80,
        )
        recognizers.append(
            PatternRecognizer(
                supported_entity="INDIAN_PASSPORT",
                patterns=[passport_pattern],
                context=["passport"],
            )
        )

        return recognizers


if __name__ == "__main__":
    # Test cases
    test_cases = {
        "AADHAAR_NUMBER": {
            "valid": "my aadhaar is 1234 5678 9012",
            "invalid": "number is 123 456",
        },
        "PAN_NUMBER": {
            "valid": "PAN card ABCDE1234F",
            "invalid": "code is AB123",
        },
        "INDIAN_MOBILE": {
            "valid": "call me on 9876543210",
            "invalid": "call 12345",
        },
        "VOTER_ID": {
            "valid": "voter id ABC1234567",
            "invalid": "id AB123",
        },
        "INDIAN_PASSPORT": {
            "valid": "passport number A1234567",
            "invalid": "ref 12345678",
        },
    }

    # Setup Presidio AnalyzerEngine with custom recognizers
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    for recognizer in IndianPIIRecognizers.get_all():
        registry.add_recognizer(recognizer)

    analyzer = AnalyzerEngine(registry=registry)

    # Run tests
    for entity, samples in test_cases.items():
        valid_res = analyzer.analyze(
            text=samples["valid"], language="en", entities=[entity]
        )
        invalid_res = analyzer.analyze(
            text=samples["invalid"], language="en", entities=[entity]
        )

        has_valid = any(r.entity_type == entity for r in valid_res)
        has_invalid = any(r.entity_type == entity for r in invalid_res)

        if has_valid and not has_invalid:
            print(f"{entity}: PASS")
        else:
            print(f"{entity}: FAIL")
