# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for TemplateService.get_template error handling (Handover 0123 - Phase 2)

Split from test_template_service.py.

Updated BE-8000j: the create/update/list tenant-isolation + error-handling mock
tests were removed together with the never-production-called create_template /
update_template / list_templates service methods. Tenant isolation of the live
create/update WRITE path is now covered against a real DB in
tests/services/test_inf6049c_cli_tool_persistence.py (tenant-isolated create +
update) and tests/services/test_be6026_template_404_not_403.py (cross-tenant 404).
"""

from unittest.mock import AsyncMock, Mock

import pytest

from giljo_mcp.services.template_service import TemplateService
from tests.unit.conftest import make_mock_db_manager, make_mock_session


class TestTemplateServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_get_template_database_exception(self):
        """Test database exception handling in get"""
        from giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        session = make_mock_session()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        db_manager = make_mock_db_manager(session)

        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = TemplateService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern (Handover 0730)
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.get_template(template_id="test-id")

        assert "Connection lost" in str(exc_info.value)
