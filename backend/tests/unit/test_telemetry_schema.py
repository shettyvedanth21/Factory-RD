"""
Unit tests for telemetry schemas and topic parsing.
Run: pytest tests/unit/test_telemetry_schema.py -v
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "telemetry"))

from schemas import TelemetryPayload, parse_topic


class TestTelemetryPayload:
    """Tests for TelemetryPayload schema."""
    
    def test_valid_payload_parses_correctly(self):
        """Test that a valid payload with timestamp and metrics parses correctly."""
        payload = TelemetryPayload(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            metrics={"temperature": 45.5, "pressure": 101.3, "rpm": 1500}
        )
        
        assert payload.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert payload.metrics == {"temperature": 45.5, "pressure": 101.3, "rpm": 1500}
    
    def test_empty_metrics_raises_validation_error(self):
        """Test that empty metrics dict raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryPayload(
                timestamp=datetime.utcnow(),
                metrics={}
            )
        
        assert "metrics cannot be empty" in str(exc_info.value)
    
    def test_non_numeric_metric_raises_validation_error(self):
        """Test that non-numeric metric values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryPayload(
                timestamp=datetime.utcnow(),
                metrics={"temperature": "high"}  # String instead of number
            )
        
        error_msg = str(exc_info.value)
        # Pydantic validation happens before custom validator
        assert "temperature" in error_msg
        assert ("unable to parse string" in error_msg or "must be numeric" in error_msg)
    
    def test_timestamp_defaults_to_none_and_server_provides_fallback(self):
        """Test that timestamp is optional and defaults to None."""
        payload = TelemetryPayload(
            metrics={"temperature": 25.0}
        )
        
        assert payload.timestamp is None
        assert payload.metrics == {"temperature": 25.0}
    
    def test_mixed_int_and_float_metrics_valid(self):
        """Test that both int and float metric values are valid."""
        payload = TelemetryPayload(
            metrics={"temperature": 45.5, "rpm": 1500, "count": 42}
        )
        
        assert isinstance(payload.metrics["temperature"], float)
        assert isinstance(payload.metrics["rpm"], int)
        assert isinstance(payload.metrics["count"], int)
    
    def test_multiple_non_numeric_metrics_validation(self):
        """Test validation fails with multiple non-numeric values."""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryPayload(
                metrics={
                    "temperature": 45.5,
                    "status": "OK",  # Invalid
                    "pressure": 101.3
                }
            )
        
        error_msg = str(exc_info.value)
        # Pydantic validation happens before custom validator
        assert "status" in error_msg
        assert ("unable to parse string" in error_msg or "must be numeric" in error_msg)


class TestParseTopic:
    """Tests for parse_topic function."""
    
    def test_parse_topic_valid_input_returns_factory_and_device(self):
        """Test that valid topic returns (factory_slug, device_key)."""
        factory_slug, device_key = parse_topic("factories/vpc/devices/M01/telemetry")
        
        assert factory_slug == "vpc"
        assert device_key == "M01"
    
    def test_parse_topic_invalid_format_raises_value_error(self):
        """Test that invalid topic format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic("invalid/topic/format")
        
        assert "Invalid topic format" in str(exc_info.value)
    
    def test_parse_topic_too_few_segments_raises(self):
        """Test that topic with too few segments raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic("factories/vpc/devices")
        
        assert "Invalid topic format" in str(exc_info.value)
    
    def test_parse_topic_wrong_prefix_raises(self):
        """Test that topic with wrong prefix raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic("wrong/vpc/devices/M01/telemetry")
        
        assert "Invalid topic format" in str(exc_info.value)
    
    def test_parse_topic_wrong_devices_segment_raises(self):
        """Test that topic with wrong 'devices' segment raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic("factories/vpc/wrong/M01/telemetry")
        
        assert "Invalid topic format" in str(exc_info.value)
    
    def test_parse_topic_wrong_telemetry_segment_raises(self):
        """Test that topic with wrong 'telemetry' segment raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_topic("factories/vpc/devices/M01/wrong")
        
        assert "Invalid topic format" in str(exc_info.value)
    
    def test_parse_topic_different_factory_and_device(self):
        """Test parsing with different factory and device identifiers."""
        factory_slug, device_key = parse_topic("factories/acme/devices/PUMP-5/telemetry")
        
        assert factory_slug == "acme"
        assert device_key == "PUMP-5"
    
    def test_parse_topic_hyphenated_identifiers(self):
        """Test parsing with hyphenated identifiers."""
        factory_slug, device_key = parse_topic("factories/test-factory/devices/device-123/telemetry")
        
        assert factory_slug == "test-factory"
        assert device_key == "device-123"
