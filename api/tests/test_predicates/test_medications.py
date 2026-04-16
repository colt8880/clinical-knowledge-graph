"""Unit tests for medication predicates: has_medication_active."""

from __future__ import annotations

from app.evaluator.predicates.medications import eval_has_medication_active
from app.evaluator.graph import ClinicalEntity, CodeRef


def _make_entities() -> dict:
    return {
        "med:atorvastatin": ClinicalEntity(
            id="med:atorvastatin",
            label="Medication",
            display_name="Atorvastatin",
            codes=[CodeRef("rxnorm", "83367")],
        ),
        "med:rosuvastatin": ClinicalEntity(
            id="med:rosuvastatin",
            label="Medication",
            display_name="Rosuvastatin",
            codes=[CodeRef("rxnorm", "301542")],
        ),
    }


class TestHasMedicationActive:
    def test_active_medication_matches(self):
        pc = {"medications": [{
            "id": "m1",
            "codes": [{"system": "rxnorm", "code": "83367"}],
            "status": "active",
        }]}
        result = eval_has_medication_active(
            {"codes": ["med:atorvastatin"]}, pc, _make_entities()
        )
        assert result == "true"

    def test_stopped_medication_does_not_match(self):
        pc = {"medications": [{
            "id": "m1",
            "codes": [{"system": "rxnorm", "code": "83367"}],
            "status": "stopped",
        }]}
        result = eval_has_medication_active(
            {"codes": ["med:atorvastatin"]}, pc, _make_entities()
        )
        assert result == "false"

    def test_no_medications_returns_false(self):
        pc = {"medications": []}
        result = eval_has_medication_active(
            {"codes": ["med:atorvastatin"]}, pc, _make_entities()
        )
        assert result == "false"

    def test_multi_code_list_any_match(self):
        pc = {"medications": [{
            "id": "m1",
            "codes": [{"system": "rxnorm", "code": "301542"}],
            "status": "active",
        }]}
        result = eval_has_medication_active(
            {"codes": ["med:atorvastatin", "med:rosuvastatin"]}, pc, _make_entities()
        )
        assert result == "true"

    def test_wrong_code_returns_false(self):
        pc = {"medications": [{
            "id": "m1",
            "codes": [{"system": "rxnorm", "code": "999999"}],
            "status": "active",
        }]}
        result = eval_has_medication_active(
            {"codes": ["med:atorvastatin"]}, pc, _make_entities()
        )
        assert result == "false"
