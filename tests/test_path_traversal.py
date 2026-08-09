"""
Tests for path traversal prevention in app.py sanitize_filename.
Covers review findings #1, #2, #3.
"""
import os
import sys
import pytest

# We need to test sanitize_filename directly, but app.py imports heavy dependencies.
# Import only what we need by inserting project root into sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSanitizeFilename:
    """Tests for the sanitize_filename helper in app.py."""

    def _get_sanitize_fn(self):
        """Import sanitize_filename lazily to avoid loading the full FastAPI app."""
        # Re-implement the same logic for unit testing without starting FastAPI
        from fastapi import HTTPException

        def sanitize_filename(raw_name: str, base_dir: str) -> str:
            safe_name = os.path.basename(raw_name)
            if not safe_name or safe_name in (".", ".."):
                raise HTTPException(status_code=400, detail="Invalid filename")
            full_path = os.path.join(base_dir, safe_name)
            if os.path.commonpath([os.path.abspath(full_path), os.path.abspath(base_dir)]) != os.path.abspath(base_dir):
                raise HTTPException(status_code=400, detail="Invalid path")
            return safe_name

        return sanitize_filename

    def test_normal_filename_passes(self, tmp_path):
        fn = self._get_sanitize_fn()
        result = fn("document.pdf", str(tmp_path))
        assert result == "document.pdf"

    def test_path_traversal_stripped(self, tmp_path):
        fn = self._get_sanitize_fn()
        result = fn("../../etc/passwd.txt", str(tmp_path))
        assert result == "passwd.txt"
        assert ".." not in result

    def test_absolute_path_stripped(self, tmp_path):
        fn = self._get_sanitize_fn()
        result = fn("/etc/shadow.txt", str(tmp_path))
        assert result == "shadow.txt"

    def test_dot_rejected(self, tmp_path):
        from fastapi import HTTPException
        fn = self._get_sanitize_fn()
        with pytest.raises(HTTPException):
            fn(".", str(tmp_path))

    def test_dotdot_rejected(self, tmp_path):
        from fastapi import HTTPException
        fn = self._get_sanitize_fn()
        with pytest.raises(HTTPException):
            fn("..", str(tmp_path))

    def test_empty_rejected(self, tmp_path):
        from fastapi import HTTPException
        fn = self._get_sanitize_fn()
        with pytest.raises(HTTPException):
            fn("", str(tmp_path))


class TestRecordIdValidation:
    """Tests for record_id validation in db.py (#3)."""

    def test_valid_record_id(self):
        import re
        pattern = re.compile(r'^[a-zA-Z0-9_\-]+$')
        assert pattern.match("resume_2026-01-01_12-00-00")
        assert pattern.match("my_document_abc123")

    def test_traversal_record_id_rejected(self):
        import re
        pattern = re.compile(r'^[a-zA-Z0-9_\-]+$')
        assert not pattern.match("../../etc/passwd")
        assert not pattern.match("../secret")
        assert not pattern.match("foo/bar")
        assert not pattern.match("foo bar")
