"""Tests for the predicate parser and overlap computation.

Covers: age range extraction, condition handling (conjunctive and disjunctive),
observation parsing, medication handling, risk scores, smoking status,
plain English rendering, and overlap computation between Rec pairs.
"""

import json
import sys
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from predicate_parser import (
    DisjunctiveGroup,
    EligibilityCriteria,
    eligibility_to_plain_english,
    parse_eligibility,
)


# ---------------------------------------------------------------------------
# parse_eligibility — age ranges
# ---------------------------------------------------------------------------


class TestAgeExtraction:
    def test_age_between(self):
        elig = parse_eligibility('{"all_of": [{"age_between": {"min": 40, "max": 75}}]}')
        assert elig.age_min == 40
        assert elig.age_max == 75
        assert elig.effective_age_min == 40
        assert elig.effective_age_max == 75

    def test_age_gte(self):
        elig = parse_eligibility(
            '{"all_of": [{"age_greater_than_or_equal": {"value": 76}}]}'
        )
        assert elig.age_gte == 76
        assert elig.effective_age_min == 76
        assert elig.effective_age_max is None

    def test_age_between_and_gte_takes_max(self):
        elig = parse_eligibility(
            '{"all_of": [{"age_between": {"min": 18, "max": 120}}, '
            '{"age_greater_than_or_equal": {"value": 50}}]}'
        )
        assert elig.effective_age_min == 50  # max(18, 50)
        assert elig.effective_age_max == 120

    def test_age_range_str_bounded(self):
        elig = EligibilityCriteria(age_min=40, age_max=75)
        assert elig.age_range_str() == "40–75"

    def test_age_range_str_lower_only(self):
        elig = EligibilityCriteria(age_gte=76)
        assert elig.age_range_str() == "≥76"

    def test_age_range_str_any(self):
        elig = EligibilityCriteria()
        assert elig.age_range_str() == "any age"


# ---------------------------------------------------------------------------
# parse_eligibility — conditions (conjunctive vs disjunctive)
# ---------------------------------------------------------------------------


class TestConditionExtraction:
    def test_conjunctive_required(self):
        """Conditions in all_of are conjunctive requirements."""
        elig = parse_eligibility(
            '{"all_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}]}'
        )
        assert elig.required_conditions == ["cond:diabetes"]
        assert len(elig.disjunctive_groups) == 0

    def test_excluded_conditions(self):
        """Conditions in none_of are excluded."""
        elig = parse_eligibility(
            '{"none_of": [{"has_condition_history": {"codes": ["cond:ascvd-established"]}}]}'
        )
        assert elig.excluded_conditions == ["cond:ascvd-established"]

    def test_disjunctive_conditions(self):
        """Conditions in any_of are tracked as a disjunctive group."""
        elig = parse_eligibility(
            '{"any_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}, '
            '{"has_active_condition": {"codes": ["cond:hypertension"]}}]}'
        )
        assert len(elig.required_conditions) == 0
        assert len(elig.disjunctive_groups) == 1
        assert set(elig.disjunctive_groups[0].conditions) == {
            "cond:diabetes",
            "cond:hypertension",
        }

    def test_disjunctive_with_smoking(self):
        """any_of can mix condition and smoking predicates."""
        elig = parse_eligibility(
            '{"any_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}, '
            '{"smoking_status_is": {"values": ["current"]}}]}'
        )
        assert len(elig.disjunctive_groups) == 1
        group = elig.disjunctive_groups[0]
        assert group.conditions == ["cond:diabetes"]
        assert group.smoking_values == ["current"]


# ---------------------------------------------------------------------------
# parse_eligibility — USPSTF statin Grade B (real predicate tree)
# ---------------------------------------------------------------------------


class TestRealPredicateTrees:
    GRADE_B_JSON = json.dumps(
        {
            "all_of": [
                {"age_between": {"min": 40, "max": 75}},
                {
                    "none_of": [
                        {"has_condition_history": {"codes": ["cond:ascvd-established"]}},
                        {
                            "most_recent_observation_value": {
                                "code": "obs:ldl-cholesterol",
                                "window": "P2Y",
                                "comparator": "gte",
                                "threshold": 190,
                                "unit": "mg/dL",
                            }
                        },
                        {
                            "has_condition_history": {
                                "codes": ["cond:familial-hypercholesterolemia"]
                            }
                        },
                    ]
                },
                {
                    "any_of": [
                        {"has_active_condition": {"codes": ["cond:dyslipidemia"]}},
                        {"has_active_condition": {"codes": ["cond:diabetes"]}},
                        {"has_active_condition": {"codes": ["cond:hypertension"]}},
                        {
                            "smoking_status_is": {
                                "values": ["current", "current_some_day", "current_every_day"]
                            }
                        },
                    ]
                },
                {
                    "risk_score_compares": {
                        "name": "ascvd_10yr",
                        "comparator": "gte",
                        "threshold": 10,
                    }
                },
            ]
        }
    )

    def test_grade_b_age(self):
        elig = parse_eligibility(self.GRADE_B_JSON)
        assert elig.effective_age_min == 40
        assert elig.effective_age_max == 75

    def test_grade_b_exclusions(self):
        elig = parse_eligibility(self.GRADE_B_JSON)
        assert "cond:ascvd-established" in elig.excluded_conditions
        assert "cond:familial-hypercholesterolemia" in elig.excluded_conditions

    def test_grade_b_excluded_observations(self):
        elig = parse_eligibility(self.GRADE_B_JSON)
        assert len(elig.excluded_observations) == 1
        assert elig.excluded_observations[0]["code"] == "obs:ldl-cholesterol"

    def test_grade_b_disjunctive_risk_factors(self):
        elig = parse_eligibility(self.GRADE_B_JSON)
        assert len(elig.disjunctive_groups) == 1
        group = elig.disjunctive_groups[0]
        assert set(group.conditions) == {
            "cond:dyslipidemia",
            "cond:diabetes",
            "cond:hypertension",
        }
        assert "current" in group.smoking_values

    def test_grade_b_risk_score(self):
        elig = parse_eligibility(self.GRADE_B_JSON)
        assert len(elig.risk_scores) == 1
        assert elig.risk_scores[0]["name"] == "ascvd_10yr"
        assert elig.risk_scores[0]["threshold"] == 10

    def test_grade_b_no_conjunctive_conditions(self):
        """Grade B has no conjunctive required conditions — they're all in any_of."""
        elig = parse_eligibility(self.GRADE_B_JSON)
        assert elig.required_conditions == []

    KDIGO_SGLT2_JSON = json.dumps(
        {
            "all_of": [
                {"age_between": {"min": 18, "max": 120}},
                {
                    "most_recent_observation_value": {
                        "code": "obs:egfr",
                        "window": "P2Y",
                        "comparator": "gte",
                        "threshold": 20,
                        "unit": "mL/min/1.73m2",
                    }
                },
                {
                    "any_of": [
                        {
                            "all_of": [
                                {"has_active_condition": {"codes": ["cond:diabetes"]}},
                                {
                                    "most_recent_observation_value": {
                                        "code": "obs:egfr",
                                        "window": "P2Y",
                                        "comparator": "lt",
                                        "threshold": 60,
                                        "unit": "mL/min/1.73m2",
                                    }
                                },
                            ]
                        },
                        {
                            "most_recent_observation_value": {
                                "code": "obs:urine-acr",
                                "window": "P2Y",
                                "comparator": "gte",
                                "threshold": 200,
                                "unit": "mg/g",
                            }
                        },
                    ]
                },
            ],
            "none_of": [
                {
                    "has_medication_active": {
                        "codes": ["med:empagliflozin", "med:dapagliflozin"]
                    }
                }
            ],
        }
    )

    def test_kdigo_sglt2_disjunctive(self):
        """KDIGO SGLT2 rec has nested any_of with all_of inside — should create disjunctive group."""
        elig = parse_eligibility(self.KDIGO_SGLT2_JSON)
        assert len(elig.disjunctive_groups) == 1
        group = elig.disjunctive_groups[0]
        # Diabetes condition and eGFR obs from the nested all_of,
        # plus urine-acr obs from the other branch
        assert "cond:diabetes" in group.conditions

    def test_kdigo_sglt2_excluded_meds(self):
        elig = parse_eligibility(self.KDIGO_SGLT2_JSON)
        assert "med:empagliflozin" in elig.excluded_medications
        assert "med:dapagliflozin" in elig.excluded_medications


# ---------------------------------------------------------------------------
# parse_eligibility — medications
# ---------------------------------------------------------------------------


class TestMedicationExtraction:
    def test_required_medication(self):
        elig = parse_eligibility(
            '{"all_of": [{"has_medication_active": {"codes": ["med:atorvastatin"]}}]}'
        )
        assert elig.required_medications == ["med:atorvastatin"]

    def test_excluded_medication(self):
        elig = parse_eligibility(
            '{"none_of": [{"has_medication_active": {"codes": ["med:atorvastatin", "med:rosuvastatin"]}}]}'
        )
        assert set(elig.excluded_medications) == {"med:atorvastatin", "med:rosuvastatin"}


# ---------------------------------------------------------------------------
# eligibility_to_plain_english
# ---------------------------------------------------------------------------


class TestPlainEnglish:
    def test_basic_rendering(self):
        elig = EligibilityCriteria(age_min=40, age_max=75)
        text = eligibility_to_plain_english(elig)
        assert "Age: 40–75" in text

    def test_disjunctive_rendering(self):
        group = DisjunctiveGroup(
            conditions=["cond:diabetes", "cond:hypertension"],
            smoking_values=["current"],
        )
        elig = EligibilityCriteria(age_min=40, age_max=75, disjunctive_groups=[group])
        text = eligibility_to_plain_english(elig)
        assert "Requires ANY of:" in text
        assert "Diabetes" in text
        assert "Hypertension" in text
        assert "smoking: current" in text

    def test_exclusion_rendering(self):
        elig = EligibilityCriteria(excluded_conditions=["cond:ascvd-established"])
        text = eligibility_to_plain_english(elig)
        assert "Excludes: Ascvd Established" in text

    def test_manual_review_flag(self):
        elig = EligibilityCriteria(manual_review_notes=["Complex nesting"])
        text = eligibility_to_plain_english(elig)
        assert "Manual review" in text


# ---------------------------------------------------------------------------
# Overlap computation
# ---------------------------------------------------------------------------

# Import overlap function — discover-interactions.py has a hyphenated name,
# so we use importlib. Set __name__ properly to avoid dataclass issue on 3.14.
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "discover_interactions",
    Path(__file__).parent.parent / "discover-interactions.py",
)
_mod = _ilu.module_from_spec(_spec)
sys.modules["discover_interactions"] = _mod  # register before exec to fix dataclass
_spec.loader.exec_module(_mod)
compute_overlap = _mod.compute_overlap
RecInfo = _mod.RecInfo


class TestOverlapComputation:
    def _make_rec(
        self,
        rec_id: str,
        guideline_id: str,
        eligibility_json: str,
        action_entities: list[str] | None = None,
    ) -> "RecInfo":
        elig = parse_eligibility(eligibility_json)
        return RecInfo(
            id=rec_id,
            title=rec_id,
            evidence_grade="B",
            intent="primary_prevention",
            guideline_id=guideline_id,
            source_section="Test",
            structured_eligibility_raw=eligibility_json,
            eligibility=elig,
            action_entity_ids=action_entities or [],
        )

    def test_age_overlap(self):
        a = self._make_rec("a", "g1", '{"all_of": [{"age_between": {"min": 40, "max": 75}}]}')
        b = self._make_rec("b", "g2", '{"all_of": [{"age_between": {"min": 18, "max": 75}}]}')
        result = compute_overlap(a, b)
        assert result.age_overlaps is True
        assert "40–75" in result.age_overlap

    def test_age_no_overlap(self):
        a = self._make_rec("a", "g1", '{"all_of": [{"age_between": {"min": 18, "max": 75}}]}')
        b = self._make_rec(
            "b", "g2", '{"all_of": [{"age_greater_than_or_equal": {"value": 76}}]}'
        )
        result = compute_overlap(a, b)
        assert result.age_overlaps is False
        assert "NO OVERLAP" in result.age_overlap

    def test_condition_conflict(self):
        a = self._make_rec(
            "a",
            "g1",
            '{"all_of": [{"has_active_condition": {"codes": ["cond:ascvd-established"]}}]}',
        )
        b = self._make_rec(
            "b",
            "g2",
            '{"none_of": [{"has_condition_history": {"codes": ["cond:ascvd-established"]}}]}',
        )
        result = compute_overlap(a, b)
        assert result.condition_compatible is False

    def test_shared_therapeutic_targets(self):
        a = self._make_rec(
            "a",
            "g1",
            '{"all_of": [{"age_between": {"min": 40, "max": 75}}]}',
            action_entities=["med:atorvastatin", "med:rosuvastatin"],
        )
        b = self._make_rec(
            "b",
            "g2",
            '{"all_of": [{"age_between": {"min": 40, "max": 75}}]}',
            action_entities=["med:atorvastatin"],
        )
        result = compute_overlap(a, b)
        assert "med:atorvastatin" in result.shared_therapeutic_targets
        assert result.candidate_type == "convergence"

    def test_modification_candidate(self):
        a = self._make_rec(
            "a",
            "g1",
            '{"all_of": [{"age_between": {"min": 40, "max": 75}}]}',
            action_entities=["med:atorvastatin"],
        )
        b = self._make_rec(
            "b",
            "g2",
            '{"all_of": [{"age_between": {"min": 40, "max": 75}}]}',
            action_entities=["med:lisinopril"],
        )
        result = compute_overlap(a, b)
        assert result.candidate_type == "modification"
        assert len(result.shared_therapeutic_targets) == 0

    def test_no_interaction_from_no_overlap(self):
        a = self._make_rec("a", "g1", '{"all_of": [{"age_between": {"min": 40, "max": 75}}]}')
        b = self._make_rec(
            "b", "g2", '{"all_of": [{"age_greater_than_or_equal": {"value": 76}}]}'
        )
        result = compute_overlap(a, b)
        assert result.candidate_type == "no_interaction"

    def test_disjunctive_not_fully_excluded(self):
        """If only one branch of an any_of is excluded, pair is still compatible."""
        a = self._make_rec(
            "a",
            "g1",
            '{"any_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}, '
            '{"has_active_condition": {"codes": ["cond:hypertension"]}}]}',
        )
        b = self._make_rec(
            "b",
            "g2",
            '{"none_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}]}',
        )
        result = compute_overlap(a, b)
        # Patient with hypertension (not diabetes) can satisfy both
        assert result.condition_compatible is True

    def test_disjunctive_all_excluded(self):
        """If ALL branches of an any_of are excluded (condition-only), pair is incompatible."""
        a = self._make_rec(
            "a",
            "g1",
            '{"any_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}, '
            '{"has_active_condition": {"codes": ["cond:hypertension"]}}]}',
        )
        b = self._make_rec(
            "b",
            "g2",
            '{"none_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}, '
            '{"has_active_condition": {"codes": ["cond:hypertension"]}}]}',
        )
        result = compute_overlap(a, b)
        assert result.condition_compatible is False

    def test_disjunctive_with_obs_branch_not_excluded(self):
        """If a disjunction has observation branches alongside excluded conditions,
        the observation branches provide alternative paths — pair stays compatible."""
        # Mimics KDIGO SGLT2: any_of [diabetes+eGFR<60, ACR>=200]
        # Even if diabetes is excluded, ACR>=200 branch still works
        a = self._make_rec(
            "a",
            "g1",
            json.dumps(
                {
                    "any_of": [
                        {"has_active_condition": {"codes": ["cond:diabetes"]}},
                        {
                            "most_recent_observation_value": {
                                "code": "obs:urine-acr",
                                "window": "P2Y",
                                "comparator": "gte",
                                "threshold": 200,
                                "unit": "mg/g",
                            }
                        },
                    ]
                }
            ),
        )
        b = self._make_rec(
            "b",
            "g2",
            '{"none_of": [{"has_active_condition": {"codes": ["cond:diabetes"]}}]}',
        )
        result = compute_overlap(a, b)
        # Patient with ACR>=200 (no diabetes) can satisfy both
        assert result.condition_compatible is True
