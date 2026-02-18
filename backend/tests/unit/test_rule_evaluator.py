"""
MANDATORY unit tests for rule condition evaluator.
ALL 16 tests must pass before Phase 3B is considered complete.

Run: pytest tests/unit/test_rule_evaluator.py -v
"""
import pytest

from app.workers.rule_engine import evaluate_conditions


class TestRuleEvaluator:
    """Tests for evaluate_conditions function."""
    
    def test_single_gt_condition_true(self):
        """Test single greater-than condition that is true."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 50}
            ]
        }
        metrics = {"temperature": 60}
        
        assert evaluate_conditions(condition, metrics) is True
    
    def test_single_gt_condition_false(self):
        """Test single greater-than condition that is false."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 50}
            ]
        }
        metrics = {"temperature": 40}
        
        assert evaluate_conditions(condition, metrics) is False
    
    def test_single_lt_condition_true(self):
        """Test single less-than condition that is true."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "pressure", "operator": "lt", "value": 100}
            ]
        }
        metrics = {"pressure": 80}
        
        assert evaluate_conditions(condition, metrics) is True
    
    def test_single_lt_condition_false(self):
        """Test single less-than condition that is false."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "pressure", "operator": "lt", "value": 100}
            ]
        }
        metrics = {"pressure": 120}
        
        assert evaluate_conditions(condition, metrics) is False
    
    def test_single_eq_condition_true(self):
        """Test single equals condition that is true."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "status", "operator": "eq", "value": 1}
            ]
        }
        metrics = {"status": 1}
        
        assert evaluate_conditions(condition, metrics) is True
    
    def test_single_neq_condition_true(self):
        """Test single not-equals condition that is true."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "status", "operator": "neq", "value": 0}
            ]
        }
        metrics = {"status": 1}
        
        assert evaluate_conditions(condition, metrics) is True
    
    def test_and_both_true_returns_true(self):
        """Test AND with both conditions true returns true."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 50},
                {"parameter": "pressure", "operator": "lt", "value": 100}
            ]
        }
        metrics = {"temperature": 60, "pressure": 80}
        
        assert evaluate_conditions(condition, metrics) is True
    
    def test_and_one_false_returns_false(self):
        """Test AND with one condition false returns false."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 50},
                {"parameter": "pressure", "operator": "lt", "value": 100}
            ]
        }
        metrics = {"temperature": 60, "pressure": 120}
        
        assert evaluate_conditions(condition, metrics) is False
    
    def test_or_one_true_returns_true(self):
        """Test OR with one condition true returns true."""
        condition = {
            "operator": "OR",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 100},
                {"parameter": "pressure", "operator": "lt", "value": 100}
            ]
        }
        metrics = {"temperature": 60, "pressure": 80}
        
        assert evaluate_conditions(condition, metrics) is True
    
    def test_or_both_false_returns_false(self):
        """Test OR with both conditions false returns false."""
        condition = {
            "operator": "OR",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 100},
                {"parameter": "pressure", "operator": "gt", "value": 100}
            ]
        }
        metrics = {"temperature": 60, "pressure": 80}
        
        assert evaluate_conditions(condition, metrics) is False
    
    def test_nested_and_or_complex_tree(self):
        """Test nested AND/OR condition tree."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 50},
                {
                    "operator": "OR",
                    "conditions": [
                        {"parameter": "pressure", "operator": "lt", "value": 50},
                        {"parameter": "humidity", "operator": "gt", "value": 80}
                    ]
                }
            ]
        }
        metrics = {"temperature": 60, "pressure": 100, "humidity": 90}
        
        # temperature > 50 (True) AND (pressure < 50 (False) OR humidity > 80 (True))
        # True AND (False OR True) = True AND True = True
        assert evaluate_conditions(condition, metrics) is True
    
    def test_missing_parameter_returns_false_not_exception(self):
        """Test that missing parameter returns False, not exception."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "gt", "value": 50}
            ]
        }
        metrics = {"pressure": 100}  # Missing 'temperature'
        
        # Should return False, not raise exception
        assert evaluate_conditions(condition, metrics) is False
    
    def test_unknown_operator_returns_false_not_exception(self):
        """Test that unknown operator returns False, not exception."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temperature", "operator": "unknown", "value": 50}
            ]
        }
        metrics = {"temperature": 60}
        
        # Should return False, not raise exception
        assert evaluate_conditions(condition, metrics) is False
    
    def test_empty_conditions_list_returns_false(self):
        """Test that empty conditions list returns False."""
        condition = {
            "operator": "AND",
            "conditions": []
        }
        metrics = {"temperature": 60}
        
        assert evaluate_conditions(condition, metrics) is False
    
    def test_invalid_condition_tree_dict_returns_false(self):
        """Test that invalid condition tree returns False."""
        condition = {}  # Missing operator and conditions
        metrics = {"temperature": 60}
        
        assert evaluate_conditions(condition, metrics) is False
    
    def test_deeply_nested_three_levels(self):
        """Test deeply nested condition tree (3 levels)."""
        condition = {
            "operator": "AND",
            "conditions": [
                {"parameter": "temp", "operator": "gt", "value": 50},
                {
                    "operator": "OR",
                    "conditions": [
                        {"parameter": "pressure", "operator": "lt", "value": 100},
                        {
                            "operator": "AND",
                            "conditions": [
                                {"parameter": "humidity", "operator": "gt", "value": 70},
                                {"parameter": "voltage", "operator": "gte", "value": 220}
                            ]
                        }
                    ]
                }
            ]
        }
        metrics = {
            "temp": 60,
            "pressure": 150,
            "humidity": 80,
            "voltage": 230
        }
        
        # temp > 50 (True) AND (pressure < 100 (False) OR (humidity > 70 (True) AND voltage >= 220 (True)))
        # True AND (False OR (True AND True)) = True AND (False OR True) = True AND True = True
        assert evaluate_conditions(condition, metrics) is True
