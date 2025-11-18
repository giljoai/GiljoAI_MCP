"""
Token estimation service for depth configuration (Handover 0314).

Provides estimated token usage based on user depth configuration settings.
Used by Context Management v2.0 to show users predicted token impact.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DepthTokenEstimator:
    """Estimates token usage based on depth configuration."""

    # Token estimates per depth setting (based on production data)
    # These are empirical values from actual orchestrator runs
    TOKEN_ESTIMATES: Dict[str, Dict[Any, int]] = {
        "vision_chunking": {
            "none": 0,
            "light": 10000,
            "moderate": 17500,
            "heavy": 30000
        },
        "memory_last_n_projects": {
            1: 500,
            3: 1500,
            5: 2500,
            10: 5000
        },
        "git_commits": {
            10: 500,
            25: 1250,
            50: 2500,
            100: 5000
        },
        "agent_template_detail": {
            "minimal": 400,
            "standard": 800,
            "full": 2400
        },
        "tech_stack_sections": {
            "required": 200,
            "all": 400
        },
        "architecture_depth": {
            "overview": 300,
            "detailed": 1500
        }
    }

    @classmethod
    def estimate_total(cls, depth_config: Dict[str, Any]) -> int:
        """
        Calculate total estimated tokens for given depth config.

        Args:
            depth_config: User's depth configuration dict

        Returns:
            Total estimated token count

        Example:
            >>> config = {"vision_chunking": "moderate", "git_commits": 25}
            >>> DepthTokenEstimator.estimate_total(config)
            18750
        """
        total = 0
        for key, value in depth_config.items():
            if key in cls.TOKEN_ESTIMATES:
                total += cls.TOKEN_ESTIMATES[key].get(value, 0)

        logger.info(
            f"Token estimate calculated: {total} tokens for config: {depth_config}"
        )
        return total

    @classmethod
    def estimate_per_source(cls, depth_config: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate per-source token estimates.

        Args:
            depth_config: User's depth configuration dict

        Returns:
            Dictionary mapping source keys to token estimates

        Example:
            >>> config = {"vision_chunking": "moderate", "git_commits": 25}
            >>> DepthTokenEstimator.estimate_per_source(config)
            {"vision_chunking": 17500, "git_commits": 1250}
        """
        estimates = {}
        for key, value in depth_config.items():
            if key in cls.TOKEN_ESTIMATES:
                estimates[key] = cls.TOKEN_ESTIMATES[key].get(value, 0)

        return estimates
