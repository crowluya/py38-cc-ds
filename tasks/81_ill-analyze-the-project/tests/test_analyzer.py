"""Tests for PylintAnalyzer."""

import pytest
import tempfile
import json
from pathlib import Path

from pylint_integrator.core.analyzer import PylintAnalyzer
from pylint_integrator.core.config import Configuration


class TestPylintAnalyzer:
    """Test PylintAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        config = Configuration(paths=["src/"])
        analyzer = PylintAnalyzer(config)
        assert analyzer.config == config

    def test_get_files_to_analyze(self):
        """Test getting list of files to analyze."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test Python files
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("print('hello')")

            config = Configuration(paths=[tmpdir], recursive=True)
            analyzer = PylintAnalyzer(config)

            files = analyzer.get_files_to_analyze()
            assert len(files) > 0
            assert any("test.py" in f for f in files)

    def test_ignore_patterns(self):
        """Test that ignore patterns work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "test.py").write_text("print('hello')")
            (Path(tmpdir) / "test.pyc").write_text("compiled")

            config = Configuration(
                paths=[tmpdir],
                ignore_patterns=["*.pyc"],
            )
            analyzer = PylintAnalyzer(config)

            files = analyzer.get_files_to_analyze()
            assert not any("test.pyc" in f for f in files)
            assert any("test.py" in f for f in files)

    def test_analyze_nonexistent_path(self):
        """Test analyzing non-existent path."""
        config = Configuration(paths=["nonexistent/path"])
        analyzer = PylintAnalyzer(config)
        result = analyzer.analyze()

        assert not result.success
        assert result.error_message is not None

    def test_analyze_simple_code(self):
        """Test analyzing simple Python code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file with issues
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""
def foo():
    x = 1
    return x
""")

            config = Configuration(paths=[tmpdir])
            analyzer = PylintAnalyzer(config)

            # This test requires pylint to be installed
            try:
                result = analyzer.analyze()
                assert result is not None
                assert result.pylint_version != ""
                assert isinstance(result.files_analyzed, int)
            except RuntimeError as e:
                if "pylint is not installed" in str(e):
                    pytest.skip("pylint not installed")
                else:
                    raise

    def test_score_threshold(self):
        """Test score threshold enforcement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("x = 1\n")

            config = Configuration(
                paths=[tmpdir],
                score_threshold=15.0,  # Impossible to achieve
            )
            analyzer = PylintAnalyzer(config)

            try:
                result = analyzer.analyze()
                # If score is below threshold, should fail
                if result.global_score and result.global_score < 15.0:
                    assert not result.success
            except RuntimeError as e:
                if "pylint is not installed" in str(e):
                    pytest.skip("pylint not installed")
                else:
                    raise


class TestPylintIntegration:
    """Integration tests with actual pylint."""

    @pytest.fixture
    def sample_code(self, tmpdir):
        """Create sample Python files for testing."""
        # Good file
        good_file = Path(tmpdir) / "good.py"
        good_file.write_text('''
"""This is a good module."""

def hello_world() -> str:
    """Return a greeting."""
    return "Hello, World!"

if __name__ == "__main__":
    print(hello_world())
''')

        # Bad file
        bad_file = Path(tmpdir) / "bad.py"
        bad_file.write_text('''
def bad():
    x=1
    return x
''')

        return tmpdir

    def test_analyze_good_code(self, sample_code):
        """Test analyzing code that follows conventions."""
        config = Configuration(paths=[str(sample_code)])
        analyzer = PylintAnalyzer(config)

        try:
            result = analyzer.analyze()
            assert result.success
            assert len(result.issues) >= 0
        except RuntimeError as e:
            if "pylint is not installed" in str(e):
                pytest.skip("pylint not installed")
            else:
                raise

    def test_analyze_with_json_output(self, sample_code):
        """Test analyzing with JSON output format."""
        config = Configuration(
            paths=[str(sample_code)],
            output_format="json",
        )
        analyzer = PylintAnalyzer(config)

        try:
            result = analyzer.analyze()
            # Should successfully parse JSON
            assert result is not None
        except RuntimeError as e:
            if "pylint is not installed" in str(e):
                pytest.skip("pylint not installed")
            else:
                raise

    @pytest.mark.slow
    def test_execution_time(self, sample_code):
        """Test that execution time is recorded."""
        config = Configuration(paths=[str(sample_code)])
        analyzer = PylintAnalyzer(config)

        try:
            result = analyzer.analyze()
            assert result.execution_time >= 0
        except RuntimeError as e:
            if "pylint is not installed" in str(e):
                pytest.skip("pylint not installed")
            else:
                raise
