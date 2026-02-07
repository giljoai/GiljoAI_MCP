"""
Unit tests for quality_standards field migration (Handover 0316).

TDD RED phase: These tests should FAIL until the model is updated.
"""

from sqlalchemy import Text

from src.giljo_mcp.models.products import Product


def test_quality_standards_field_exists():
    """Test that quality_standards field exists on Product model"""
    assert hasattr(Product, "quality_standards"), "Product model should have quality_standards field"


def test_quality_standards_nullable():
    """Test that quality_standards field is nullable"""
    column = Product.__table__.columns.get("quality_standards")
    assert column is not None, "quality_standards column should exist in Product table"
    assert column.nullable is True, "quality_standards column should be nullable"


def test_quality_standards_is_text_type():
    """Test that quality_standards is Text type"""
    column = Product.__table__.columns.get("quality_standards")
    assert column is not None, "quality_standards column should exist in Product table"
    assert isinstance(column.type, Text), "quality_standards column should be Text type"


def test_quality_standards_comment():
    """Test that quality_standards has proper comment"""
    column = Product.__table__.columns.get("quality_standards")
    assert column is not None, "quality_standards column should exist in Product table"
    assert column.comment is not None, "quality_standards column should have a comment"
    assert "quality standards" in column.comment.lower(), "Comment should describe quality standards purpose"
