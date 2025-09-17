"""
Comprehensive test suite for MissionTemplateGenerator.

Tests template generation, role-specific missions, project-type customization,
behavioral instructions, and integration with orchestrator.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.giljo_mcp.mission_templates import MissionTemplateGenerator
from src.giljo_mcp.enums import ProjectType, AgentRole
from src.giljo_mcp.orchestrator import ProjectOrchestrator
from src.giljo_mcp.models import Project, Agent
from src.giljo_mcp.database import get_db_manager


class TestMissionTemplateGenerator:
    """Unit tests for MissionTemplateGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create a MissionTemplateGenerator instance."""
        return MissionTemplateGenerator()
    
    @pytest.fixture
    def sample_context(self):
        """Create sample template context."""
        return TemplateContext(
            project_name="Test Project",
            project_mission="Build a test system",
            product_name="TestProduct",
            vision_summary="A comprehensive test product",
            project_type=ProjectType.FEATURE,
            custom_parameters={
                "priority": "high",
                "deadline": "2025-02-01"
            }
        )
    
    def test_orchestrator_template_generation(self, generator, sample_context):
        """Test orchestrator template generation with all required elements."""
        template = generator.generate_orchestrator_template(sample_context)
        
        # Verify all placeholders are replaced
        assert sample_context.project_name in template
        assert sample_context.project_mission in template
        assert sample_context.product_name in template
        
        # Verify key sections are present
        assert "DISCOVERY APPROACH" in template
        assert "VISION GUARDIAN" in template
        assert "SCOPE SHERIFF" in template
        assert "STRATEGIC ARCHITECT" in template
        assert "PROGRESS TRACKER" in template
        assert "BEHAVIORAL INSTRUCTIONS" in template
        
        # Verify vision chunking instructions
        assert "get_vision()" in template
        assert "total_parts" in template
        assert "Read ALL parts" in template
        
        # Verify Serena MCP integration
        assert "Serena MCP" in template
        
        # Verify no unresolved placeholders
        assert "{" not in template or "{{" in template  # Allow escaped braces
    
    def test_analyzer_template_generation(self, generator, sample_context):
        """Test analyzer agent template generation."""
        template = generator.generate_agent_template(AgentRole.ANALYZER, sample_context)
        
        # Verify role-specific content
        assert "analyzer" in template.lower()
        assert "requirements" in template.lower()
        assert "architecture" in template.lower()
        assert "design" in template.lower()
        
        # Verify project context
        assert sample_context.project_name in template
        assert sample_context.project_mission in template
    
    def test_implementer_template_generation(self, generator, sample_context):
        """Test implementer agent template generation."""
        template = generator.generate_agent_template(AgentRole.IMPLEMENTER, sample_context)
        
        # Verify role-specific content
        assert "implementer" in template.lower()
        assert "code" in template.lower()
        assert "implement" in template.lower()
        assert "standards" in template.lower()
        
        # Verify coding standards from CLAUDE.md
        assert "OS-neutral" in template or "pathlib" in template
        assert "coding standards" in template.lower()
    
    def test_tester_template_generation(self, generator, sample_context):
        """Test tester agent template generation."""
        template = generator.generate_agent_template(AgentRole.TESTER, sample_context)
        
        # Verify role-specific content
        assert "tester" in template.lower()
        assert "test" in template.lower()
        assert "validation" in template.lower() or "validate" in template.lower()
        assert "coverage" in template.lower() or "comprehensive" in template.lower()
        
        # Verify testing approaches
        assert "unit test" in template.lower() or "unit_test" in template.lower()
        assert "integration" in template.lower()
    
    def test_reviewer_template_generation(self, generator, sample_context):
        """Test reviewer agent template generation."""
        template = generator.generate_agent_template(AgentRole.REVIEWER, sample_context)
        
        # Verify role-specific content
        assert "reviewer" in template.lower()
        assert "review" in template.lower()
        assert "security" in template.lower()
        assert "quality" in template.lower()
    
    def test_project_type_customization(self, generator):
        """Test that different project types generate appropriate templates."""
        contexts = [
            TemplateContext(
                project_name="Feature Project",
                project_mission="Add new feature",
                product_name="Product",
                project_type=ProjectType.FEATURE
            ),
            TemplateContext(
                project_name="Bug Fix",
                project_mission="Fix critical bug",
                product_name="Product",
                project_type=ProjectType.BUGFIX
            ),
            TemplateContext(
                project_name="Refactor",
                project_mission="Refactor codebase",
                product_name="Product",
                project_type=ProjectType.REFACTOR
            ),
            TemplateContext(
                project_name="Testing",
                project_mission="Add tests",
                product_name="Product",
                project_type=ProjectType.TESTING
            )
        ]
        
        templates = [generator.generate_orchestrator_template(ctx) for ctx in contexts]
        
        # Each template should be unique
        assert len(set(templates)) == len(templates)
        
        # Feature template should emphasize design
        assert "design" in templates[0].lower()
        
        # Bugfix template should emphasize urgency
        assert "urgent" in templates[1].lower() or "critical" in templates[1].lower()
        
        # Refactor template should emphasize code quality
        assert "refactor" in templates[2].lower()
        
        # Testing template should emphasize coverage
        assert "coverage" in templates[3].lower() or "test" in templates[3].lower()
    
    def test_behavioral_instructions_inclusion(self, generator, sample_context):
        """Test that behavioral instructions are properly included."""
        template = generator.generate_orchestrator_template(sample_context)
        
        # Verify parallel vs sequential instructions
        assert "parallel" in template.lower() or "sequential" in template.lower()
        
        # Verify acknowledgment instructions
        assert "acknowledge" in template.lower()
        
        # Verify handoff instructions
        assert "handoff" in template.lower()
        
        # Verify status reporting
        assert "status" in template.lower()
        assert "report" in template.lower()
    
    def test_custom_parameters_injection(self, generator):
        """Test custom parameter injection into templates."""
        context = TemplateContext(
            project_name="Custom Project",
            project_mission="Custom mission",
            product_name="Product",
            custom_parameters={
                "tech_stack": "Python, FastAPI, Vue.js",
                "database": "PostgreSQL",
                "deployment": "Docker"
            }
        )
        
        template = generator.generate_agent_template(AgentRole.IMPLEMENTER, context)
        
        # Verify custom parameters are included
        assert "Python" in template
        assert "FastAPI" in template
        assert "PostgreSQL" in template
    
    def test_template_validation(self, generator):
        """Test template validation before use."""
        # Test with missing required fields
        invalid_context = TemplateContext(
            project_name="",  # Empty name
            project_mission="",  # Empty mission
            product_name=""  # Empty product
        )
        
        with pytest.raises(ValueError, match="required"):
            generator.generate_orchestrator_template(invalid_context)
    
    def test_template_caching(self, generator, sample_context):
        """Test that templates are cached for performance."""
        # Generate same template twice
        template1 = generator.generate_orchestrator_template(sample_context)
        template2 = generator.generate_orchestrator_template(sample_context)
        
        # Should be same instance (cached)
        assert template1 is template2
        
        # Modify context slightly
        sample_context.project_name = "Different Project"
        template3 = generator.generate_orchestrator_template(sample_context)
        
        # Should be different instance
        assert template1 is not template3


class TestOrchestratorIntegration:
    """Integration tests with ProjectOrchestrator."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create ProjectOrchestrator instance."""
        orchestrator = ProjectOrchestrator()
        await orchestrator.initialize()
        return orchestrator
    
    @pytest.fixture
    async def project(self, orchestrator):
        """Create a test project."""
        project = await orchestrator.create_project(
            name="Integration Test Project",
            mission="Test mission template integration",
            context_budget=150000
        )
        await orchestrator.activate_project(project.id)
        return project
    
    @pytest.mark.asyncio
    async def test_spawn_agent_with_template(self, orchestrator, project):
        """Test spawning agent uses mission templates."""
        with patch('src.giljo_mcp.orchestrator.MissionTemplateGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate_agent_template.return_value = "Custom template mission"
            
            agent = await orchestrator.spawn_agent(
                project_id=project.id,
                role=AgentRole.ANALYZER
            )
            
            # Verify generator was called
            mock_generator.generate_agent_template.assert_called_once()
            
            # Verify agent has custom mission
            assert agent.mission == "Custom template mission"
    
    @pytest.mark.asyncio
    async def test_spawn_agent_with_custom_mission(self, orchestrator, project):
        """Test custom mission overrides template."""
        custom_mission = "This is a custom mission"
        
        agent = await orchestrator.spawn_agent(
            project_id=project.id,
            role=AgentRole.IMPLEMENTER,
            custom_mission=custom_mission
        )
        
        assert agent.mission == custom_mission
    
    @pytest.mark.asyncio
    async def test_spawn_orchestrator_agent(self, orchestrator, project):
        """Test spawning orchestrator agent with comprehensive template."""
        with patch('src.giljo_mcp.orchestrator.MissionTemplateGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            orchestrator_template = "Comprehensive orchestrator template with vision guardian"
            mock_generator.generate_orchestrator_template.return_value = orchestrator_template
            
            agent = await orchestrator.spawn_agent(
                project_id=project.id,
                role=AgentRole.ORCHESTRATOR
            )
            
            # Verify orchestrator template was used
            mock_generator.generate_orchestrator_template.assert_called_once()
            assert agent.mission == orchestrator_template
    
    @pytest.mark.asyncio
    async def test_template_context_from_project(self, orchestrator, project):
        """Test that template context is properly built from project data."""
        with patch('src.giljo_mcp.orchestrator.MissionTemplateGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            
            await orchestrator.spawn_agent(
                project_id=project.id,
                role=AgentRole.TESTER
            )
            
            # Verify context was built with project data
            call_args = mock_generator.generate_agent_template.call_args
            context = call_args[0][1] if call_args else None
            
            if context:
                assert context.project_name == project.name
                assert context.project_mission == project.mission


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def generator(self):
        """Create a MissionTemplateGenerator instance."""
        return MissionTemplateGenerator()
    
    def test_empty_project_parameters(self, generator):
        """Test handling of empty/null project parameters."""
        context = TemplateContext(
            project_name=None,
            project_mission=None,
            product_name=None
        )
        
        with pytest.raises(ValueError):
            generator.generate_orchestrator_template(context)
    
    def test_very_long_vision_document(self, generator):
        """Test handling of very long vision documents."""
        # Create context with 100K character vision
        long_vision = "A" * 100000
        context = TemplateContext(
            project_name="Long Vision Project",
            project_mission="Test long vision",
            product_name="Product",
            vision_summary=long_vision
        )
        
        template = generator.generate_orchestrator_template(context)
        
        # Should handle gracefully with chunking instructions
        assert "chunk" in template.lower() or "part" in template.lower()
    
    def test_missing_configuration_values(self, generator):
        """Test handling of missing configuration values."""
        context = TemplateContext(
            project_name="Test",
            project_mission="Test",
            product_name="Product",
            custom_parameters={}  # Empty parameters
        )
        
        # Should not raise, should use defaults
        template = generator.generate_agent_template(AgentRole.ANALYZER, context)
        assert template  # Should generate something
    
    def test_concurrent_template_generation(self, generator):
        """Test concurrent template generation."""
        contexts = [
            TemplateContext(
                project_name=f"Project {i}",
                project_mission=f"Mission {i}",
                product_name="Product"
            )
            for i in range(10)
        ]
        
        async def generate_async(ctx):
            return generator.generate_orchestrator_template(ctx)
        
        # Generate templates concurrently
        loop = asyncio.new_event_loop()
        templates = loop.run_until_complete(
            asyncio.gather(*[generate_async(ctx) for ctx in contexts])
        )
        
        # All should be generated successfully
        assert len(templates) == 10
        assert all(templates)
    
    def test_memory_performance_large_templates(self, generator):
        """Test memory/performance with large templates."""
        import time
        import tracemalloc
        
        tracemalloc.start()
        start_time = time.time()
        
        # Generate 100 templates
        for i in range(100):
            context = TemplateContext(
                project_name=f"Project {i}",
                project_mission=f"Mission {i}" * 100,  # Long mission
                product_name="Product",
                vision_summary="Vision" * 1000  # Long vision
            )
            generator.generate_orchestrator_template(context)
        
        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should complete in reasonable time (< 5 seconds)
        assert end_time - start_time < 5
        
        # Memory usage should be reasonable (< 100MB)
        assert peak / 1024 / 1024 < 100


class TestBehavioralInstructions:
    """Test behavioral instructions implementation."""
    
    @pytest.fixture
    def generator(self):
        """Create a MissionTemplateGenerator instance."""
        return MissionTemplateGenerator()
    
    def test_parallel_execution_instructions(self, generator):
        """Test parallel execution instructions are included."""
        context = TemplateContext(
            project_name="Parallel Project",
            project_mission="Test parallel execution",
            product_name="Product",
            execution_mode="parallel"
        )
        
        template = generator.generate_orchestrator_template(context)
        
        assert "parallel" in template.lower()
        assert "agents should run in parallel" in template.lower() or similar_phrase in template
    
    def test_acknowledgment_behavior(self, generator):
        """Test message acknowledgment instructions."""
        context = TemplateContext(
            project_name="Test",
            project_mission="Test",
            product_name="Product"
        )
        
        template = generator.generate_agent_template(AgentRole.IMPLEMENTER, context)
        
        assert "acknowledge" in template.lower()
        assert "message" in template.lower()
    
    def test_handoff_protocol(self, generator):
        """Test handoff protocol instructions."""
        context = TemplateContext(
            project_name="Test",
            project_mission="Test",
            product_name="Product"
        )
        
        template = generator.generate_orchestrator_template(context)
        
        assert "handoff" in template.lower()
        assert "context limit" in template.lower()
    
    def test_status_reporting_instructions(self, generator):
        """Test status reporting instructions."""
        context = TemplateContext(
            project_name="Test",
            project_mission="Test",
            product_name="Product"
        )
        
        template = generator.generate_agent_template(AgentRole.TESTER, context)
        
        assert "report" in template.lower()
        assert "status" in template.lower()
        assert "orchestrator" in template.lower()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])