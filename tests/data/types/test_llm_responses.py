import pytest

from data.types.llm_responses import PlanResponse
from data.types.plan import Approach, BetSizing


class TestPlanResponse:
    """Test suite for PlanResponse model."""

    def test_valid_response_parsing(self):
        """Test parsing of valid JSON responses."""
        valid_json = """
        {
            "approach": "aggressive",
            "reasoning": "High card with potential to bluff",
            "bet_sizing": "medium",
            "bluff_threshold": 0.6,
            "fold_threshold": 0.3
        }
        """
        result = PlanResponse.parse_llm_response(valid_json)

        assert result["approach"] == "aggressive"
        assert result["reasoning"] == "High card with potential to bluff"
        assert result["bet_sizing"] == "medium"
        assert result["bluff_threshold"] == 0.6
        assert result["fold_threshold"] == 0.3

    def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        invalid_json = "Not a JSON string"
        result = PlanResponse.parse_llm_response(invalid_json)

        # Should return default values
        assert result["approach"] == "balanced"
        assert result["reasoning"] == "Default plan due to parse error"
        assert result["bet_sizing"] == "medium"
        assert result["bluff_threshold"] == 0.5
        assert result["fold_threshold"] == 0.3

    def test_missing_fields(self):
        """Test handling of JSON missing required fields."""
        incomplete_json = """
        {
            "approach": "aggressive",
            "reasoning": "High card with potential to bluff"
        }
        """
        result = PlanResponse.parse_llm_response(incomplete_json)

        # Should return default values due to validation failure
        assert result["approach"] == "balanced"
        assert result["reasoning"] == "Default plan due to parse error"

    def test_invalid_field_values(self):
        """Test handling of invalid field values."""
        invalid_values = """
        {
            "approach": "not_valid_approach",
            "reasoning": "High card with potential to bluff",
            "bet_sizing": "medium",
            "bluff_threshold": 1.5,
            "fold_threshold": -0.1
        }
        """
        result = PlanResponse.parse_llm_response(invalid_values)

        # Should return default values due to validation failure
        assert result["approach"] == "balanced"
        assert 0 <= result["bluff_threshold"] <= 1
        assert 0 <= result["fold_threshold"] <= 1

    def test_direct_model_validation(self):
        """Test direct model validation without parsing."""
        valid_data = {
            "approach": "aggressive",
            "reasoning": "Valid reasoning",
            "bet_sizing": "medium",
            "bluff_threshold": 0.6,
            "fold_threshold": 0.3,
        }
        model = PlanResponse(**valid_data)

        assert model.approach == Approach.AGGRESSIVE
        assert model.reasoning == "Valid reasoning"
        assert model.bet_sizing == BetSizing.MEDIUM
        assert model.bluff_threshold == 0.6
        assert model.fold_threshold == 0.3

    @pytest.mark.parametrize(
        "invalid_reasoning",
        [
            "",  # Empty string
            "   ",  # Whitespace only
            "ab",  # Too short
            "a" * 201,  # Too long
        ],
    )
    def test_invalid_reasoning(self, invalid_reasoning):
        """Test validation of invalid reasoning values."""
        data = {
            "approach": "aggressive",
            "reasoning": invalid_reasoning,
            "bet_sizing": "medium",
            "bluff_threshold": 0.6,
            "fold_threshold": 0.3,
        }
        with pytest.raises(ValueError):
            PlanResponse(**data)

    @pytest.mark.parametrize(
        "threshold,field_name",
        [
            (-0.1, "bluff_threshold"),
            (1.1, "bluff_threshold"),
            (-0.1, "fold_threshold"),
            (1.1, "fold_threshold"),
            ("not_a_number", "bluff_threshold"),
            ("not_a_number", "fold_threshold"),
        ],
    )
    def test_invalid_thresholds(self, threshold, field_name):
        """Test validation of invalid threshold values."""
        data = {
            "approach": "aggressive",
            "reasoning": "Valid reasoning",
            "bet_sizing": "medium",
            "bluff_threshold": 0.5,
            "fold_threshold": 0.5,
        }
        data[field_name] = threshold

        with pytest.raises(ValueError):
            PlanResponse(**data)

    def test_whitespace_handling(self):
        """Test handling of whitespace in reasoning field."""
        data = {
            "approach": "aggressive",
            "reasoning": "  Valid reasoning with whitespace  ",
            "bet_sizing": "medium",
            "bluff_threshold": 0.6,
            "fold_threshold": 0.3,
        }
        model = PlanResponse(**data)

        # Should strip whitespace
        assert model.reasoning == "Valid reasoning with whitespace"

    def test_model_dump(self):
        """Test model serialization to dict."""
        data = {
            "approach": "aggressive",
            "reasoning": "Valid reasoning",
            "bet_sizing": "medium",
            "bluff_threshold": 0.6,
            "fold_threshold": 0.3,
        }
        model = PlanResponse(**data)
        dumped = model.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["approach"] == "aggressive"
        assert dumped["reasoning"] == "Valid reasoning"
        assert dumped["bet_sizing"] == "medium"
        assert dumped["bluff_threshold"] == 0.6
        assert dumped["fold_threshold"] == 0.3
