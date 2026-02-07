"""
PathNormalizer utility for consistent cross-platform path handling.
Ensures all paths use forward slashes and handles edge cases.
"""

from contextlib import suppress
from pathlib import Path
from typing import Optional, Union


class PathNormalizer:
    """
    Utility class for consistent path handling across platforms.
    Ensures all paths use forward slashes for cross-platform compatibility.
    """

    @staticmethod
    def normalize(path: Union[str, Path]) -> str:
        """
        Normalize a path to use forward slashes.

        Args:
            path: Path string or Path object

        Returns:
            Normalized path string with forward slashes
        """
        if isinstance(path, str):
            # Preserve relative path prefixes
            original = path
            # Replace backslashes with forward slashes first
            path = path.replace("\\", "/")

            # Handle special relative path cases
            if original.startswith((".\\", "./")):
                # Preserve ./ prefix - strip each separately
                path = "./" + path.lstrip(".")
                path = path.lstrip("/")
            elif original.startswith(("..\\", "../")):
                # Preserve ../ prefix - strip each separately
                path = "../" + path.lstrip(".")
                path = path.lstrip("/")

            return path

        path_obj = Path(path)
        return path_obj.as_posix()

    @staticmethod
    def join(*parts: Union[str, Path]) -> str:
        """
        Join path parts and normalize the result.

        Args:
            *parts: Path components to join

        Returns:
            Joined and normalized path
        """
        if not parts:
            return ""

        # Start with first part
        result = Path(parts[0])

        # Join remaining parts
        for part in parts[1:]:
            result = result / part

        # Resolve .. and . components
        with suppress(OSError, RuntimeError):
            # If resolve fails (e.g., path doesn't exist), just normalize
            result = result.resolve()

        return result.as_posix()

    @staticmethod
    def resolve_relative(base: Union[str, Path], relative: Union[str, Path]) -> str:
        """
        Resolve a relative path against a base path.

        Args:
            base: Base path
            relative: Relative path to resolve

        Returns:
            Resolved absolute path with forward slashes
        """
        base_path = Path(base)
        rel_path = Path(relative)

        # If relative path starts with ./, preserve it
        relative_str = str(relative)
        if relative_str.startswith(("./", ".\\")):
            result = base_path / rel_path
            result_str = result.as_posix()
            # Ensure ./ prefix is preserved for relative paths
            if not result_str.startswith("/") and result_str[1:3] != ":/":
                result_str = "./" + result_str.lstrip("./")
            return result_str

        # Handle parent directory references
        if relative_str.startswith(("../", "..\\")):
            # Count how many parent levels
            parts = Path(relative_str).parts
            parent_count = sum(1 for p in parts if p == "..")

            # Go up parent_count levels from base
            result = base_path
            for _ in range(parent_count):
                result = result.parent

            # Add remaining parts
            remaining = [p for p in parts if p != ".."]
            for part in remaining:
                result = result / part

            return result.as_posix()

        # Normal join
        result = base_path / rel_path
        return result.as_posix()

    @staticmethod
    def to_url_path(path: Union[str, Path]) -> str:
        """
        Convert a file path to a URL-safe path.

        Args:
            path: File system path

        Returns:
            URL-safe path with forward slashes
        """
        normalized = PathNormalizer.normalize(path)
        # Ensure no backslashes in URL
        return normalized.replace("\\", "/")

    @staticmethod
    def get_relative(path: Union[str, Path], base: Optional[Union[str, Path]] = None) -> str:
        """
        Get relative path from base to path.

        Args:
            path: Target path
            base: Base path (defaults to current directory)

        Returns:
            Relative path with forward slashes
        """
        path_obj = Path(path)
        base_obj = Path(base) if base else Path.cwd()

        try:
            relative = path_obj.relative_to(base_obj)
            return relative.as_posix()
        except ValueError:
            # Paths don't have common base
            return path_obj.as_posix()

    @staticmethod
    def ensure_absolute(path: Union[str, Path], base: Optional[Union[str, Path]] = None) -> str:
        """
        Ensure a path is absolute.

        Args:
            path: Path that might be relative
            base: Base path for relative paths (defaults to cwd)

        Returns:
            Absolute path with forward slashes
        """
        path_obj = Path(path)

        if not path_obj.is_absolute():
            base_obj = Path(base) if base else Path.cwd()
            path_obj = base_obj / path_obj

        return path_obj.as_posix()


# Convenience functions
def normalize_path(path: Union[str, Path]) -> str:
    """Convenience function for PathNormalizer.normalize()"""
    return PathNormalizer.normalize(path)


def join_paths(*parts: Union[str, Path]) -> str:
    """Convenience function for PathNormalizer.join()"""
    return PathNormalizer.join(*parts)


def resolve_relative_path(base: Union[str, Path], relative: Union[str, Path]) -> str:
    """Convenience function for PathNormalizer.resolve_relative()"""
    return PathNormalizer.resolve_relative(base, relative)
