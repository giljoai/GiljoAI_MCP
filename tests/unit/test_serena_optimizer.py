"""
Unit tests for SerenaOptimizer system.
Tests optimization rules, token tracking, and template augmentation generation.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.optimization.serena_optimizer import (
    OperationType,
    OptimizationRule,
    SerenaOptimizer,
    TokenUsageTracker,
)
from tests.fixtures.base_fixtures import TestData
from tests.fixtures.base_test import BaseAsyncTest


class TestOperationType:
    """Test OperationType enum"""

    def test_operation_types_defined(self):
        """Test all required operation types are defined"""
        assert OperationType.FILE_READ.value == "file_read"
        assert OperationType.SYMBOL_SEARCH.value == "symbol_search"
        assert OperationType.SYMBOL_REPLACE.value == "symbol_replace"
        assert OperationType.PATTERN_SEARCH.value == "pattern_search"
        assert OperationType.DIRECTORY_LIST.value == "directory_list"

    def test_operation_type_values(self):
        """Test operation type string values"""
        operation_types = [op.value for op in OperationType]
        assert "file_read" in operation_types
        assert "symbol_search" in operation_types
        assert len(operation_types) == 5


class TestOptimizationRule:
    """Test OptimizationRule dataclass"""

    def test_create_rule_basic(self):
        """Test creating basic optimization rule"""
        rule = OptimizationRule(
            operation_type=OperationType.FILE_READ,
            max_answer_chars=2000,
            prefer_symbolic=True,
            guidance="Use symbolic operations first",
        )

        assert rule.operation_type == OperationType.FILE_READ
        assert rule.max_answer_chars == 2000
        assert rule.prefer_symbolic is True
        assert "symbolic" in rule.guidance
        assert rule.context_filter is None

    def test_create_rule_with_context_filter(self):
        """Test creating rule with context filter"""
        rule = OptimizationRule(
            operation_type=OperationType.SYMBOL_SEARCH,
            max_answer_chars=5000,
            prefer_symbolic=True,
            guidance="Search guidance",
            context_filter="large_codebase",
        )

        assert rule.context_filter == "large_codebase"

    def test_rule_defaults(self):
        """Test rule default values"""
        rule = OptimizationRule(
            operation_type=OperationType.PATTERN_SEARCH, max_answer_chars=3000, prefer_symbolic=False, guidance="Test"
        )

        assert rule.context_filter is None


class TestTokenUsageTracker:
    """Test TokenUsageTracker functionality"""

    def setup_method(self, method):
        """Setup test method"""
        self.tracker = TokenUsageTracker()

    def test_estimate_tokens_basic(self):
        """Test basic token estimation (4 chars = 1 token)"""
        text = "a" * 400  # 400 characters
        tokens = self.tracker.estimate_tokens(text)
        assert tokens == 100  # 400 / 4

    def test_estimate_tokens_empty(self):
        """Test token estimation with empty string"""
        tokens = self.tracker.estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_real_text(self):
        """Test token estimation with realistic text"""
        text = "This is a test message with multiple words and characters."
        tokens = self.tracker.estimate_tokens(text)
        # 59 chars / 4 = 14 tokens (integer division)
        assert tokens == 14

    def test_estimate_tokens_unoptimized_file_read(self):
        """Test unoptimized token estimation for file_read"""
        result_size = 1000  # Actual result size
        estimated = self.tracker.estimate_tokens_unoptimized(OperationType.FILE_READ, 0, result_size)

        # file_read without optimization: 10x actual size
        assert estimated == result_size * 10

    def test_estimate_tokens_unoptimized_symbol_search(self):
        """Test unoptimized token estimation for symbol_search"""
        result_size = 2000
        estimated = self.tracker.estimate_tokens_unoptimized(OperationType.SYMBOL_SEARCH, 0, result_size)

        # symbol_search without optimization: 5x actual size
        assert estimated == result_size * 5

    def test_estimate_tokens_unoptimized_pattern_search(self):
        """Test unoptimized token estimation for pattern_search"""
        result_size = 1500
        estimated = self.tracker.estimate_tokens_unoptimized(OperationType.PATTERN_SEARCH, 0, result_size)

        # pattern_search without optimization: 8x actual size
        assert estimated == result_size * 8

    def test_calculate_savings_basic(self):
        """Test savings calculation"""
        optimized = 100
        unoptimized = 1000
        savings = self.tracker.calculate_savings(optimized, unoptimized)

        assert savings == 900  # 1000 - 100
        assert savings > 0

    def test_calculate_savings_percentage(self):
        """Test savings percentage calculation"""
        optimized = 100
        unoptimized = 1000
        percentage = self.tracker.calculate_savings_percentage(optimized, unoptimized)

        assert percentage == 90.0  # (1000-100)/1000 * 100

    def test_calculate_savings_percentage_no_unoptimized(self):
        """Test savings percentage with zero unoptimized"""
        percentage = self.tracker.calculate_savings_percentage(100, 0)
        assert percentage == 0.0


class TestSerenaOptimizer(BaseAsyncTest):
    """Test SerenaOptimizer main class"""

    def setup_method(self, method):
        """Setup test method"""
        super().setup_method(method)
        self.mock_db_manager = Mock()
        self.tenant_key = TestData.generate_tenant_key()
        self.optimizer = SerenaOptimizer(self.mock_db_manager, self.tenant_key)

    # ==================== Initialization Tests ====================

    def test_optimizer_initialization(self):
        """Test SerenaOptimizer initialization"""
        assert self.optimizer.db_manager == self.mock_db_manager
        assert self.optimizer.tenant_key == self.tenant_key
        assert isinstance(self.optimizer.token_tracker, TokenUsageTracker)
        assert self.optimizer.default_rules is not None

    def test_default_rules_loaded(self):
        """Test default rules are loaded on initialization"""
        rules = self.optimizer.default_rules

        assert OperationType.FILE_READ in rules
        assert OperationType.SYMBOL_SEARCH in rules
        assert OperationType.PATTERN_SEARCH in rules
        assert len(rules) >= 5

    def test_default_rule_file_read(self):
        """Test default file_read rule configuration"""
        rule = self.optimizer.default_rules[OperationType.FILE_READ]

        assert rule.max_answer_chars == 2000
        assert rule.prefer_symbolic is True
        assert "NEVER read entire files" in rule.guidance
        assert "find_symbol()" in rule.guidance or "get_symbols_overview()" in rule.guidance

    def test_default_rule_symbol_search(self):
        """Test default symbol_search rule configuration"""
        rule = self.optimizer.default_rules[OperationType.SYMBOL_SEARCH]

        assert rule.max_answer_chars == 5000
        assert rule.prefer_symbolic is True
        assert "depth=0" in rule.guidance or "depth" in rule.guidance.lower()

    # ==================== Rule Loading Tests ====================

    @pytest.mark.asyncio
    async def test_get_optimization_rules_default_fallback(self):
        """Test rule loading falls back to defaults on DB failure"""
        # Mock database failure
        mock_session = self.create_async_mock("session")
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        rules = await self.optimizer.get_optimization_rules()

        # Should return default rules
        assert rules is not None
        assert OperationType.FILE_READ in rules
        assert len(rules) >= 5

    @pytest.mark.asyncio
    async def test_get_optimization_rules_with_db_rules(self):
        """Test loading rules from database"""
        from src.giljo_mcp.models import OptimizationRule as OptimizationRuleModel

        # Mock database session with custom rules
        mock_rule = OptimizationRuleModel(
            id=str(uuid.uuid4()),
            tenant_key=self.tenant_key,
            operation_type="file_read",
            max_answer_chars=1500,
            prefer_symbolic=True,
            guidance="Custom guidance",
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_rule]

        mock_session = self.create_async_mock("session")
        mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        rules = await self.optimizer.get_optimization_rules()

        # Should have custom rule
        assert OperationType.FILE_READ in rules
        assert rules[OperationType.FILE_READ].max_answer_chars == 1500
        assert rules[OperationType.FILE_READ].guidance == "Custom guidance"

    @pytest.mark.asyncio
    async def test_get_optimization_rules_merges_with_defaults(self):
        """Test DB rules merge with defaults"""
        from src.giljo_mcp.models import OptimizationRule as OptimizationRuleModel

        # Mock partial DB rules (only file_read)
        mock_rule = OptimizationRuleModel(
            id=str(uuid.uuid4()),
            tenant_key=self.tenant_key,
            operation_type="file_read",
            max_answer_chars=1500,
            prefer_symbolic=True,
            guidance="Custom guidance",
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_rule]

        mock_session = self.create_async_mock("session")
        mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        rules = await self.optimizer.get_optimization_rules()

        # Should have custom file_read + default symbol_search
        assert OperationType.FILE_READ in rules
        assert rules[OperationType.FILE_READ].max_answer_chars == 1500

        assert OperationType.SYMBOL_SEARCH in rules
        assert rules[OperationType.SYMBOL_SEARCH].max_answer_chars == 5000  # default

    # ==================== Context Adjustment Tests ====================

    def test_adjust_rules_for_context_large_codebase(self):
        """Test rule adjustment for large codebase"""
        context_data = {"codebase_size": "large", "file_count": 5000}

        adjusted = self.optimizer.adjust_rules_for_context(self.optimizer.default_rules.copy(), context_data)

        # Large codebase should have reduced char limits (50%)
        file_read_rule = adjusted[OperationType.FILE_READ]
        assert file_read_rule.max_answer_chars <= 1000  # 50% of 2000

    def test_adjust_rules_for_context_small_codebase(self):
        """Test rule adjustment for small codebase"""
        context_data = {"codebase_size": "small", "file_count": 50}

        adjusted = self.optimizer.adjust_rules_for_context(self.optimizer.default_rules.copy(), context_data)

        # Small codebase should have increased char limits (150%)
        file_read_rule = adjusted[OperationType.FILE_READ]
        assert file_read_rule.max_answer_chars >= 3000  # 150% of 2000

    def test_adjust_rules_for_context_python_language(self):
        """Test rule adjustment for Python projects"""
        context_data = {"primary_language": "python"}

        adjusted = self.optimizer.adjust_rules_for_context(self.optimizer.default_rules.copy(), context_data)

        # Should have Python-specific guidance
        file_read_rule = adjusted[OperationType.FILE_READ]
        # Guidance should mention Python-specific tools or patterns
        assert "python" in file_read_rule.guidance.lower() or "symbolic" in file_read_rule.guidance.lower()

    def test_adjust_rules_for_context_no_changes(self):
        """Test no adjustment when context is empty"""
        context_data = {}

        adjusted = self.optimizer.adjust_rules_for_context(self.optimizer.default_rules.copy(), context_data)

        # Should remain unchanged
        assert adjusted[OperationType.FILE_READ].max_answer_chars == 2000

    # ==================== Augmentation Generation Tests ====================

    @pytest.mark.asyncio
    async def test_create_optimization_augmentation_basic(self):
        """Test creating basic optimization augmentation"""
        role = "implementer"
        context_data = {}

        augmentation = await self.optimizer.create_optimization_augmentation(role, context_data)

        assert augmentation is not None
        assert augmentation["type"] == "inject"
        assert "target" in augmentation
        assert "content" in augmentation
        assert augmentation["priority"] == 100

    @pytest.mark.asyncio
    async def test_create_optimization_augmentation_content(self):
        """Test augmentation content format"""
        role = "implementer"
        context_data = {}

        augmentation = await self.optimizer.create_optimization_augmentation(role, context_data)

        content = augmentation["content"]

        # Should contain key sections
        assert "SERENA MCP OPTIMIZATION RULES" in content
        assert "CRITICAL" in content or "MANDATORY" in content
        assert "Symbolic Operations" in content or "symbolic" in content.lower()
        assert "max_answer_chars" in content or "char" in content.lower()

    @pytest.mark.asyncio
    async def test_create_optimization_augmentation_target_role_specific(self):
        """Test augmentation targets correct section for role"""
        # Implementer should target discovery workflow
        aug_impl = await self.optimizer.create_optimization_augmentation("implementer", {})
        assert "DISCOVERY WORKFLOW" in aug_impl["target"] or "workflow" in aug_impl["target"].lower()

        # Orchestrator might have different target
        aug_orch = await self.optimizer.create_optimization_augmentation("orchestrator", {})
        assert "target" in aug_orch

    @pytest.mark.asyncio
    async def test_create_optimization_augmentation_error_handling(self):
        """Test augmentation generation handles errors gracefully"""
        # Mock rule loading failure
        self.optimizer.get_optimization_rules = AsyncMock(side_effect=Exception("Rule loading failed"))

        # Should not raise, return empty/default augmentation
        augmentation = await self.optimizer.create_optimization_augmentation("implementer", {})

        assert augmentation is not None
        # Should be safe fallback
        assert "type" in augmentation

    @pytest.mark.asyncio
    async def test_create_optimization_augmentation_with_context(self):
        """Test augmentation incorporates context data"""
        context_data = {"codebase_size": "large", "primary_language": "python", "critical_feature": True}

        augmentation = await self.optimizer.create_optimization_augmentation("implementer", context_data)

        content = augmentation["content"]

        # Should reference context adjustments
        # Large codebase should have stricter limits mentioned
        assert content is not None
        assert len(content) > 0

    # ==================== Token Tracking Tests ====================

    @pytest.mark.asyncio
    async def test_record_operation_success(self):
        """Test recording optimization operation"""
        from src.giljo_mcp.models import OptimizationMetric

        agent_id = str(uuid.uuid4())

        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        await self.optimizer.record_operation(
            agent_id=agent_id,
            operation_type=OperationType.FILE_READ,
            params_size=100,
            result_size=500,
            optimized=True,
        )

        # Should add metric to database
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

        # Check the metric that was added
        added_metric = mock_session.add.call_args[0][0]
        assert isinstance(added_metric, OptimizationMetric)
        assert added_metric.agent_id == agent_id
        assert added_metric.operation_type == OperationType.FILE_READ.value
        assert added_metric.optimized is True

    @pytest.mark.asyncio
    async def test_record_operation_calculates_savings(self):
        """Test operation recording calculates token savings"""

        agent_id = str(uuid.uuid4())

        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        await self.optimizer.record_operation(
            agent_id=agent_id,
            operation_type=OperationType.FILE_READ,
            params_size=100,
            result_size=500,  # 125 tokens
            optimized=True,
        )

        added_metric = mock_session.add.call_args[0][0]

        # Should calculate tokens_saved
        # file_read unoptimized = 500 * 10 = 5000
        # optimized = 500 / 4 = 125
        # savings = 5000 - 125 = 4875
        assert added_metric.tokens_saved > 0
        assert added_metric.tokens_saved >= 1000  # Should save significant tokens

    @pytest.mark.asyncio
    async def test_record_operation_error_handling(self):
        """Test operation recording handles database errors"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock(side_effect=Exception("DB error"))
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        # Should not raise exception (fail silently with logging)
        try:
            await self.optimizer.record_operation(
                agent_id=str(uuid.uuid4()),
                operation_type=OperationType.FILE_READ,
                params_size=100,
                result_size=500,
                optimized=True,
            )
        except Exception:
            pytest.fail("record_operation should not raise on DB error")

    # ==================== Savings Report Tests ====================

    @pytest.mark.asyncio
    async def test_generate_savings_report(self):
        """Test generating savings report"""
        from src.giljo_mcp.models import OptimizationMetric

        agent_id = str(uuid.uuid4())

        # Mock metrics from database
        metrics = [
            OptimizationMetric(
                id=str(uuid.uuid4()),
                tenant_key=self.tenant_key,
                agent_id=agent_id,
                operation_type="file_read",
                params_size=100,
                result_size=500,
                tokens_saved=4875,
                optimized=True,
            ),
            OptimizationMetric(
                id=str(uuid.uuid4()),
                tenant_key=self.tenant_key,
                agent_id=agent_id,
                operation_type="symbol_search",
                params_size=50,
                result_size=300,
                tokens_saved=225,
                optimized=True,
            ),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = metrics

        mock_session = self.create_async_mock("session")
        mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        report = await self.optimizer.generate_savings_report(agent_id)

        assert report is not None
        assert "total_operations" in report
        assert report["total_operations"] == 2
        assert "total_tokens_saved" in report
        assert report["total_tokens_saved"] == 5100  # 4875 + 225

    @pytest.mark.asyncio
    async def test_generate_savings_report_by_operation_type(self):
        """Test savings report breaks down by operation type"""
        from src.giljo_mcp.models import OptimizationMetric

        agent_id = str(uuid.uuid4())

        metrics = [
            OptimizationMetric(
                id=str(uuid.uuid4()),
                tenant_key=self.tenant_key,
                agent_id=agent_id,
                operation_type="file_read",
                params_size=100,
                result_size=500,
                tokens_saved=4875,
                optimized=True,
            ),
            OptimizationMetric(
                id=str(uuid.uuid4()),
                tenant_key=self.tenant_key,
                agent_id=agent_id,
                operation_type="file_read",
                params_size=100,
                result_size=300,
                tokens_saved=2925,
                optimized=True,
            ),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = metrics

        mock_session = self.create_async_mock("session")
        mock_session.execute = AsyncMock(return_value=mock_result)
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        report = await self.optimizer.generate_savings_report(agent_id)

        # Should have breakdown by operation type
        assert "by_operation_type" in report
        assert "file_read" in report["by_operation_type"]
        assert report["by_operation_type"]["file_read"]["count"] == 2
        assert report["by_operation_type"]["file_read"]["tokens_saved"] == 7800

    @pytest.mark.asyncio
    async def test_estimate_token_savings(self):
        """Test estimating token savings for an operation"""
        result_size = 1000  # characters

        savings = self.optimizer.estimate_token_savings(OperationType.FILE_READ, result_size)

        # file_read: unoptimized = 1000 * 10 = 10000 chars
        # optimized = 1000 / 4 = 250 tokens
        # unoptimized tokens = 10000 / 4 = 2500 tokens
        # savings = 2500 - 250 = 2250 tokens
        assert savings > 0
        assert savings >= 2000  # Should be significant

    # ==================== Integration Tests ====================

    @pytest.mark.asyncio
    async def test_end_to_end_optimization_flow(self):
        """Test complete optimization workflow"""
        # 1. Create optimizer
        optimizer = SerenaOptimizer(self.mock_db_manager, self.tenant_key)

        # 2. Load rules (with DB fallback)
        mock_session = self.create_async_mock("session")
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        self.mock_db_manager.get_session_async = Mock(return_value=self.create_context_manager(mock_session))

        rules = await optimizer.get_optimization_rules()
        assert len(rules) >= 5

        # 3. Adjust for context
        context_data = {"codebase_size": "large"}
        adjusted_rules = optimizer.adjust_rules_for_context(rules, context_data)
        assert adjusted_rules[OperationType.FILE_READ].max_answer_chars <= 1000

        # 4. Create augmentation
        augmentation = await optimizer.create_optimization_augmentation("implementer", context_data)
        assert augmentation["type"] == "inject"
        assert len(augmentation["content"]) > 0

        # 5. Verify augmentation structure
        assert augmentation["priority"] == 100
        assert "SERENA MCP OPTIMIZATION" in augmentation["content"]
