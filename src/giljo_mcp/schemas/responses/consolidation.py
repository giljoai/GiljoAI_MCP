# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Consolidation/vision summarization service response models."""

from pydantic import BaseModel, ConfigDict, Field


class SummaryLevel(BaseModel):
    """Single summary level (light or medium) within a consolidation result."""

    summary: str = ""
    tokens: int = 0

    model_config = ConfigDict(from_attributes=True)


class ConsolidationResult(BaseModel):
    """Vision document consolidation result.

    Fields match ConsolidatedVisionService.consolidate_vision_documents() output.
    """

    light: SummaryLevel = Field(default_factory=SummaryLevel)
    medium: SummaryLevel = Field(default_factory=SummaryLevel)
    hash: str = ""
    source_docs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SummarizeSingleResult(BaseModel):
    """Single-document summarization result.

    Fields match VisionDocumentSummarizer.summarize() output.
    """

    summary: str = ""
    original_tokens: int = 0
    summary_tokens: int = 0
    compression_ratio: float = 0.0
    processing_time_ms: int = 0

    model_config = ConfigDict(from_attributes=True)


class MultiLevelSummaryLevel(BaseModel):
    """Single level within a multi-level summarization result."""

    summary: str = ""
    tokens: int = 0
    sentences: int = 0

    model_config = ConfigDict(from_attributes=True)


class SummarizeMultiLevelResult(BaseModel):
    """Multi-level summarization result.

    Fields match VisionDocumentSummarizer.summarize_multi_level() output.
    """

    light: MultiLevelSummaryLevel = Field(default_factory=MultiLevelSummaryLevel)
    medium: MultiLevelSummaryLevel = Field(default_factory=MultiLevelSummaryLevel)
    original_tokens: int = 0
    processing_time_ms: int = 0

    model_config = ConfigDict(from_attributes=True)
