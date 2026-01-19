"""Static asset management and copying."""

import shutil
from pathlib import Path

from staticgen.config import ConfigManager


class AssetCopier:
    """Copy static assets to output directory."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize asset copier.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.site_config = config_manager.load()
        self.base_dir = config_manager.base_dir

    def copy_assets(self) -> int:
        """Copy all static assets to output directory.

        Returns:
            Number of files copied
        """
        files_copied = 0

        # Copy static directory
        static_dir = self.base_dir / self.site_config.static_dir
        if static_dir.exists():
            files_copied += self._copy_directory(static_dir)

        # Copy theme assets
        theme_assets = self._get_theme_assets_dir()
        if theme_assets and theme_assets.exists():
            files_copied += self._copy_directory(theme_assets)

        return files_copied

    def _copy_directory(self, source_dir: Path) -> int:
        """Copy directory contents to output.

        Args:
            source_dir: Source directory

        Returns:
            Number of files copied
        """
        output_dir = self.base_dir / self.site_config.output_dir
        files_copied = 0

        for item in source_dir.rglob("*"):
            if item.is_file():
                # Calculate relative path
                relative_path = item.relative_to(source_dir)
                dest_path = output_dir / relative_path

                # Copy file
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)
                files_copied += 1

        return files_copied

    def _get_theme_assets_dir(self) -> Path:
        """Get theme assets directory.

        Returns:
            Path to theme assets directory
        """
        theme_name = self.site_config.theme

        if theme_name == "default":
            # Built-in default theme
            return (
                Path(__file__).parent.parent.parent / "templates" / "default" / "assets"
            )
        else:
            # User theme
            return self.base_dir / "themes" / theme_name / "assets"

    def process_css(self) -> None:
        """Process CSS files (minification, etc.)."""
        # This could integrate with CSS minifiers
        # For now, just copy files as-is
        pass

    def process_js(self) -> None:
        """Process JavaScript files (minification, etc.)."""
        # This could integrate with JS minifiers
        # For now, just copy files as-is
        pass

    def optimize_images(self) -> None:
        """Optimize images (compression, resizing, etc.)."""
        # This could integrate with image optimization tools
        # For now, just copy files as-is
        pass
