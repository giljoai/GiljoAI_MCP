# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Template service response models."""

from pydantic import BaseModel, ConfigDict, Field


class TemplateListResult(BaseModel):
    """Template list result."""

    templates: list[dict] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TemplateDetail(BaseModel):
    """Single template detail for get_template response."""

    id: str
    name: str
    role: str | None = None
    content: str | None = None
    cli_tool: str | None = None
    background_color: str | None = None
    category: str | None = None
    tenant_key: str | None = None
    product_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TemplateGetResult(BaseModel):
    """Single template retrieval result."""

    template: TemplateDetail

    model_config = ConfigDict(from_attributes=True)


class TemplateCreateResult(BaseModel):
    """Template creation result."""

    template_id: str
    name: str
    tenant_key: str

    model_config = ConfigDict(from_attributes=True)


class TemplateUpdateResult(BaseModel):
    """Template update result."""

    template_id: str
    updated: bool = True

    model_config = ConfigDict(from_attributes=True)
