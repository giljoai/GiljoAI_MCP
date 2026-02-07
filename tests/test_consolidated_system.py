"""
Comprehensive tests for the consolidated template system (Project 3.9.b)
Tests the unified template manager, polymorphic augmentation, and performance
"""

import sys
import time
from pathlib import Path

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.enums import AgentRole, ProjectType

# NOTE: TemplateAugmentation removed (Handover 0423 - model deleted, using dicts only)
from src.giljo_mcp.template_manager import apply_augmentation, extract_variables, process_template


class TestPolymorphicAugmentation:
    """Test the unified polymorphic augmentation function"""

    def test_augmentation_with_dict(self):
        """Test augmentation with dictionary input"""
        content = "Base template content"

        # Test append
        aug_dict = {"type": "append", "content": "Additional content"}
        result = apply_augmentation(content, aug_dict)
        assert "Base template content" in result
        assert "Additional content" in result

        # Test prepend
        aug_dict = {"type": "prepend", "content": "Prefix content"}
        result = apply_augmentation(content, aug_dict)
        assert result.startswith("Prefix content")

        # Test replace
        aug_dict = {"type": "replace", "content": "NEW", "target": "Base"}
        result = apply_augmentation(content, aug_dict)
        assert result == "NEW template content"

        # Test inject
        aug_dict = {"type": "inject", "content": "INJECTED", "target": "template"}
        result = apply_augmentation(content, aug_dict)
        assert "template\nINJECTED" in result

    def test_augmentation_with_object_like_dict(self):
        """Test augmentation with object-like dictionary (simulates DB model)"""
        content = "Base template content"

        # NOTE: TemplateAugmentation model removed (Handover 0423)
        # Test with object-like dict that mimics the old model structure
        class MockAugmentation:
            def __init__(self, aug_type, content, target=None):
                self.augmentation_type = aug_type
                self.content = content
                self.target_section = target

        # Create mock objects with same attributes as old TemplateAugmentation
        aug_obj = MockAugmentation("append", "Additional content")

        # Test with object
        result = apply_augmentation(content, aug_obj)
        assert "Additional content" in result

        # Test inject with object
        aug_obj2 = MockAugmentation("inject", "INJECTED", "template")
        result = apply_augmentation(content, aug_obj2)
        assert "template\nINJECTED" in result

    def test_augmentation_handles_both_key_names(self):
        """Test that augmentation handles both 'type' and 'augmentation_type' keys"""
        content = "Base content"

        # Test with 'augmentation_type' key
        aug = {"augmentation_type": "append", "content": "Added"}
        result = apply_augmentation(content, aug)
        assert "Added" in result

        # Test with 'target_section' key
        aug = {"type": "replace", "content": "NEW", "target_section": "Base"}
        result = apply_augmentation(content, aug)
        assert result == "NEW content"


class TestTemplateProcessing:
    """Test the complete template processing pipeline"""

    def test_process_template_with_variables(self):
        """Test template processing with variable substitution"""
        template = "Hello {name}, welcome to {project}"
        variables = {"name": "Tester", "project": "GiljoAI"}

        result = process_template(template, variables)
        assert result == "Hello Tester, welcome to GiljoAI"

    def test_process_template_with_augmentations(self):
        """Test template processing with augmentations"""
        template = "Base template"
        variables = {}
        augmentations = [{"type": "append", "content": "Section 1"}, {"type": "append", "content": "Section 2"}]

        result = process_template(template, variables, augmentations)
        assert "Base template" in result
        assert "Section 1" in result
        assert "Section 2" in result

    def test_process_template_complete_pipeline(self):
        """Test complete processing with variables and augmentations"""
        template = "Project: {project_name}\nRole: {role}"
        variables = {"project_name": "Test Project", "role": "Tester"}
        augmentations = [
            {"type": "append", "content": "Additional Instructions:\n- Test thoroughly"},
            {"type": "prepend", "content": "PRIORITY: High\n"},
        ]

        result = process_template(template, variables, augmentations)
        assert "PRIORITY: High" in result
        assert "Test Project" in result
        assert "Tester" in result
        assert "Test thoroughly" in result

    def test_extract_variables(self):
        """Test variable extraction from templates"""
        template = "Hello {name}, your {role} in {project} starts {date}"
        variables = extract_variables(template)

        assert variables == ["name", "role", "project", "date"]

        # Test with duplicate variables
        template = "The {item} costs {price}. Buy {item} for {price}!"
        variables = extract_variables(template)
        assert variables == ["item", "price"]  # No duplicates


class TestPerformanceRequirements:
    """Test performance meets <0.1ms requirement"""

    def test_augmentation_performance(self):
        """Test augmentation speed"""
        content = "Base template " * 100  # Larger content
        augmentation = {"type": "append", "content": "Additional content"}

        # Warm up
        apply_augmentation(content, augmentation)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            apply_augmentation(content, augmentation)
        end = time.perf_counter()

        avg_ms = ((end - start) / iterations) * 1000
        assert avg_ms < 0.1, f"Augmentation took {avg_ms:.4f}ms, exceeds 0.1ms target"

    def test_variable_substitution_performance(self):
        """Test variable substitution speed"""
        template = " ".join([f"{{var_{i}}}" for i in range(50)])
        variables = {f"var_{i}": f"value_{i}" for i in range(50)}

        # Warm up
        process_template(template, variables)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            process_template(template, variables)
        end = time.perf_counter()

        avg_ms = ((end - start) / iterations) * 1000
        assert avg_ms < 0.1, f"Processing took {avg_ms:.4f}ms, exceeds 0.1ms target"

    def test_complete_pipeline_performance(self):
        """Test complete pipeline performance"""
        template = "Mission: {mission}\n" * 20
        variables = {"mission": "Test performance of the system"}
        augmentations = [
            {"type": "append", "content": "Additional section"},
            {"type": "prepend", "content": "Header section"},
        ]

        # Warm up
        process_template(template, variables, augmentations)

        # Measure
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            process_template(template, variables, augmentations)
        end = time.perf_counter()

        avg_ms = ((end - start) / iterations) * 1000
        assert avg_ms < 0.1, f"Pipeline took {avg_ms:.4f}ms, exceeds 0.1ms target"


class TestEnumConsolidation:
    """Test that enums are properly consolidated"""

    def test_agent_role_enum(self):
        """Test AgentRole enum is accessible and complete"""
        roles = [role.value for role in AgentRole]
        assert "orchestrator" in roles
        assert "analyzer" in roles
        assert "implementer" in roles
        assert "tester" in roles

    def test_project_type_enum(self):
        """Test ProjectType enum is accessible"""
        types = [t.value for t in ProjectType]
        assert len(types) > 0  # Should have project types


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_augmentation(self):
        """Test with empty augmentation"""
        content = "Template"
        result = apply_augmentation(content, {})
        assert result == content

    def test_missing_target_for_replace(self):
        """Test replace without target"""
        content = "Template"
        aug = {"type": "replace", "content": "New"}
        result = apply_augmentation(content, aug)
        assert result == content  # Should return unchanged

    def test_target_not_found_for_inject(self):
        """Test inject when target not found"""
        content = "Template"
        aug = {"type": "inject", "content": "New", "target": "NotFound"}
        result = apply_augmentation(content, aug)
        assert result == content  # Should return unchanged

    def test_invalid_augmentation_type(self):
        """Test with invalid augmentation type"""
        content = "Template"
        aug = {"type": "invalid_type", "content": "New"}
        result = apply_augmentation(content, aug)
        assert result == content  # Should return unchanged

    def test_nested_variables(self):
        """Test nested variable patterns"""
        template = "Value: {{nested: {var}}}"
        variables = {"var": "test"}
        result = process_template(template, variables)
        assert "{{nested: test}}" in result

    def test_special_characters_in_variables(self):
        """Test special characters in variable values"""
        template = "Query: {sql}"
        variables = {"sql": "SELECT * FROM users WHERE name='O\\'Brien'"}
        result = process_template(template, variables)
        assert "O\\'Brien" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
