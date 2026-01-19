"""Command-line interface for static site generator."""

import os
import sys
from pathlib import Path

import click

from staticgen.config import ConfigManager, ConfigError


@click.group()
@click.version_option(version="0.1.0", prog_name="static-gen")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "-C",
    "--directory",
    type=click.Path(exists=True, path_type=Path),
    help="Change to directory before running",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, directory: Path) -> None:
    """Static-gen: A CLI static site generator.

    Transform Markdown files into fast, SEO-optimized HTML websites
    with built-in sitemap generation, RSS feeds, and custom theme support.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Change to specified directory
    if directory:
        os.chdir(directory)
        ctx.obj["base_dir"] = directory
    else:
        ctx.obj["base_dir"] = Path.cwd()

    if verbose:
        click.echo(f"Working directory: {ctx.obj['base_dir']}")


@cli.command()
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Initialize even if directory is not empty",
)
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Initialize a new static site project."""
    base_dir = ctx.obj["base_dir"]

    # Check if directory is empty
    if not force and any(base_dir.iterdir()):
        click.echo("Error: Directory is not empty. Use --force to override.", err=True)
        sys.exit(1)

    click.echo("Initializing new static site...")

    # Create directory structure
    dirs = [
        "content",
        "content/posts",
        "static",
        "static/css",
        "static/js",
        "static/images",
        "templates",
        "themes",
    ]

    for dir_name in dirs:
        dir_path = base_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        if ctx.obj["verbose"]:
            click.echo(f"Created: {dir_name}/")

    # Create default config file
    config_path = base_dir / "staticgen.yml"
    if not config_path.exists():
        config_content = """# Site Configuration
title: My Site
description: A static site built with static-gen
author: Your Name
email: your@email.com
url: https://example.com
base_url: ""

# Content
language: en
timezone: UTC
posts_per_page: 10

# Theme
theme: default

# Output
generate_sitemap: true
generate_feeds: true
feed_format: rss
feed_items: 20

# Markdown
markdown_extensions:
  - markdown.extensions.extra
  - markdown.extensions.codehilite
  - markdown.extensions.toc
  - markdown.extensions.meta

# Files to ignore
ignore_files:
  - README.md
  - .gitignore
"""
        config_path.write_text(config_content, encoding="utf-8")
        click.echo(f"Created: {config_path.name}")

    # Create sample post
    posts_dir = base_dir / "content" / "posts"
    sample_post = posts_dir / "welcome.md"
    if not sample_post.exists():
        post_content = """---
title: Welcome to Static-gen
date: 2024-01-01
tags: [welcome, first-post]
categories: [general]
description: Your first post with static-gen
---

# Welcome to Static-gen!

This is your first blog post. You can edit or delete it, then start writing!

## Features

- **Fast**: Generates static HTML in seconds
- **SEO-optimized**: Built-in meta tags and sitemaps
- **Flexible**: Custom themes with Jinja2 templates
- **Easy**: Write in Markdown, publish HTML

## Getting Started

1. Edit the configuration in `staticgen.yml`
2. Add your posts in `content/posts/`
3. Run `static-gen build`
4. Deploy the `output/` directory

Happy blogging!
"""
        sample_post.write_text(post_content, encoding="utf-8")
        click.echo("Created: content/posts/welcome.md")

    click.echo("\n✓ Site initialized successfully!")
    click.echo("\nNext steps:")
    click.echo("  1. Edit staticgen.yml to configure your site")
    click.echo("  2. Add content to content/posts/")
    click.echo("  3. Run 'static-gen build' to generate your site")
    click.echo("  4. Run 'static-gen serve' to preview locally")


@cli.command()
@click.option(
    "-i",
    "--input",
    type=click.Path(exists=True, path_type=Path),
    help="Input directory with content",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output directory for generated site",
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path",
)
@click.option(
    "--drafts",
    is_flag=True,
    help="Include draft posts",
)
@click.pass_context
def build(
    ctx: click.Context,
    input: Path,
    output: Path,
    config: Path,
    drafts: bool,
) -> None:
    """Build the static site."""
    base_dir = ctx.obj["base_dir"]
    verbose = ctx.obj["verbose"]

    try:
        # Load configuration
        click.echo("Loading configuration...")
        config_manager = ConfigManager(config_path=config, base_dir=base_dir)
        site_config = config_manager.load()

        # Override with command-line options
        if input:
            site_config.content_dir = str(input)
        if output:
            site_config.output_dir = str(output)
        if drafts:
            site_config.include_drafts = True

        if verbose:
            click.echo(f"Site title: {site_config.title}")
            click.echo(f"Content directory: {site_config.content_dir}")
            click.echo(f"Output directory: {site_config.output_dir}")

        # Import here to avoid circular imports
        from staticgen.generator import SiteGenerator

        # Build the site
        click.echo("Building site...")
        generator = SiteGenerator(config_manager, verbose=verbose)
        generator.build()

        click.echo("\n✓ Site built successfully!")
        click.echo(f"\nOutput: {base_dir / site_config.output_dir}")

    except ConfigError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if verbose:
            import traceback

            traceback.print_exc()
        click.echo(f"Error building site: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "-p",
    "--port",
    default=8000,
    type=int,
    help="Port to serve on",
)
@click.option(
    "-h",
    "--host",
    default="localhost",
    help="Host to bind to",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Watch for changes and rebuild",
)
@click.pass_context
def serve(ctx: click.Context, port: int, host: str, watch: bool) -> None:
    """Serve the site locally."""
    base_dir = ctx.obj["base_dir"]
    verbose = ctx.obj["verbose"]

    try:
        # Load config to get output directory
        config_manager = ConfigManager(base_dir=base_dir)
        site_config = config_manager.load()
        output_dir = base_dir / site_config.output_dir

        if not output_dir.exists():
            click.echo(
                f"Output directory does not exist: {output_dir}\n"
                f"Run 'static-gen build' first.",
                err=True,
            )
            sys.exit(1)

        if watch:
            click.echo(f"Serving at http://{host}:{port} with auto-rebuild...")
            from staticgen.server import DevelopmentServer

            server = DevelopmentServer(base_dir, config_manager, verbose=verbose)
            server.run(host=host, port=port)
        else:
            # Simple HTTP server
            import http.server
            import socketserver

            os.chdir(output_dir)
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer((host, port), handler) as httpd:
                click.echo(f"Serving at http://{host}:{port}")
                click.echo("Press Ctrl+C to stop")
                httpd.serve_forever()

    except KeyboardInterrupt:
        click.echo("\nServer stopped")
    except Exception as e:
        if verbose:
            import traceback

            traceback.print_exc()
        click.echo(f"Error serving site: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("title")
@click.option(
    "-t",
    "--type",
    type=click.Choice(["post", "page"]),
    default="post",
    help="Content type",
)
@click.option(
    "-d",
    "--draft",
    is_flag=True,
    help="Create as draft",
)
@click.pass_context
def new(ctx: click.Context, title: str, type: str, draft: bool) -> None:
    """Create new content (post or page)."""
    base_dir = ctx.obj["base_dir"]

    try:
        from staticgen.utils import slugify, get_current_date

        # Load config
        config_manager = ConfigManager(base_dir=base_dir)
        site_config = config_manager.load()

        # Generate slug and filename
        slug = slugify(title)
        current_date = get_current_date()

        if type == "post":
            content_dir = base_dir / site_config.content_dir / "posts"
            filename = f"{current_date}-{slug}.md"
        else:
            content_dir = base_dir / site_config.content_dir
            filename = f"{slug}.md"

        # Create directory if needed
        content_dir.mkdir(parents=True, exist_ok=True)
        filepath = content_dir / filename

        # Generate frontmatter
        frontmatter = f"""---
title: {title}
date: {current_date}
draft: {str(draft).lower()}
tags: []
categories: []
description:
---

# {title}

Write your content here.
"""

        filepath.write_text(frontmatter, encoding="utf-8")
        click.echo(f"Created: {filepath}")
        click.echo(f"  Type: {type}")
        click.echo(f"  Slug: {slug}")

    except Exception as e:
        click.echo(f"Error creating content: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli(obj={})
