"""Development server with live reload."""

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from staticgen.config import ConfigManager


class DevelopmentServer:
    """Development server with auto-rebuild on file changes."""

    def __init__(
        self,
        base_dir: Path,
        config_manager: ConfigManager,
        verbose: bool = False,
    ):
        """Initialize development server.

        Args:
            base_dir: Base directory
            config_manager: Configuration manager
            verbose: Enable verbose output
        """
        self.base_dir = base_dir
        self.config_manager = config_manager
        self.site_config = config_manager.load()
        self.verbose = verbose
        self.rebuild_needed = False
        self.rebuild_lock = threading.Lock()

    def run(self, host: str = "localhost", port: int = 8000) -> None:
        """Run development server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        # Start file watcher
        observer = Observer()
        handler = RebuildHandler(self)
        content_dir = self.base_dir / self.site_config.content_dir
        templates_dir = self.base_dir / self.site_config.templates_dir
        static_dir = self.base_dir / self.site_config.static_dir

        # Watch content directory
        if content_dir.exists():
            observer.schedule(handler, str(content_dir), recursive=True)

        # Watch templates directory
        if templates_dir.exists():
            observer.schedule(handler, str(templates_dir), recursive=True)

        # Watch static directory
        if static_dir.exists():
            observer.schedule(handler, str(static_dir), recursive=True)

        # Watch config file
        if self.config_manager.config_path:
            config_dir = self.config_manager.config_path.parent
            observer.schedule(handler, str(config_dir), recursive=False)

        observer.start()

        try:
            # Start HTTP server
            output_dir = self.base_dir / self.site_config.output_dir
            os.chdir(output_dir)

            with socketserver.TCPServer((host, port), DevServerHandler) as httpd:
                print(f"\n✓ Development server running at http://{host}:{port}")
                print("Watching for changes...")
                print("Press Ctrl+C to stop\n")

                # Start rebuild thread
                rebuild_thread = threading.Thread(target=self._rebuild_loop, daemon=True)
                rebuild_thread.start()

                httpd.serve_forever()

        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            observer.stop()
            observer.join()

    def trigger_rebuild(self) -> None:
        """Trigger a site rebuild."""
        with self.rebuild_lock:
            self.rebuild_needed = True

    def _rebuild_loop(self) -> None:
        """Background thread for rebuilding site."""
        while True:
            time.sleep(0.5)

            with self.rebuild_lock:
                if self.rebuild_needed:
                    self._rebuild()
                    self.rebuild_needed = False

    def _rebuild(self) -> None:
        """Rebuild the site."""
        try:
            print("\n🔄 Rebuilding site...")

            from staticgen.generator import SiteGenerator

            generator = SiteGenerator(self.config_manager, verbose=self.verbose)
            generator.build()

            print("✓ Site rebuilt\n")

        except Exception as e:
            print(f"✗ Error rebuilding site: {e}\n")


class RebuildHandler(FileSystemEventHandler):
    """File system event handler for triggering rebuilds."""

    def __init__(self, server: DevelopmentServer):
        """Initialize rebuild handler.

        Args:
            server: Development server instance
        """
        self.server = server

    def on_modified(self, event) -> None:
        """Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Only rebuild for relevant file types
        filepath = Path(event.src_path)
        if filepath.suffix in [".md", ".html", ".yml", ".yaml", ".css", ".js"]:
            if self.server.verbose:
                print(f"📝 Changed: {filepath.name}")
            self.server.trigger_rebuild()


class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for development server."""

    def log_message(self, format: str, *args) -> None:
        """Log message (suppress default logging).

        Args:
            format: Message format
            *args: Format arguments
        """
        # Optional: log requests
        # print(f"  {self.address_string()} - {format % args}")
        pass
