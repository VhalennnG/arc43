"""
Tests for DOCX formatting preservation.
Covers review finding #10: p.text / cell.text destroys run formatting.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.writers.docx_writer import replace_text_preserving_format, replace_cell_text_preserving_format


class MockRun:
    def __init__(self, text, bold=None, italic=None, font_name=None):
        self.text = text
        self.bold = bold
        self.italic = italic
        self.font_name = font_name


class MockParagraph:
    def __init__(self, runs=None):
        self.runs = runs or []
        self._added = []

    def add_run(self, text):
        r = MockRun(text)
        self.runs.append(r)
        self._added.append(r)
        return r


class MockCell:
    def __init__(self, paragraphs=None):
        self.paragraphs = paragraphs or []
        self._text = ""

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, val):
        self._text = val


class TestFormatPreservation:

    def test_replaces_first_run_keeps_bold(self):
        r1 = MockRun("Hello ", bold=True)
        r2 = MockRun("World", italic=True)
        p = MockParagraph([r1, r2])

        replace_text_preserving_format(p, "Replaced")

        assert r1.text == "Replaced"
        assert r1.bold is True  # formatting preserved
        assert r2.text == ""    # subsequent runs cleared
        assert r2.italic is True  # original formatting object untouched

    def test_empty_paragraph_adds_run(self):
        p = MockParagraph([])

        replace_text_preserving_format(p, "New text")

        assert len(p.runs) == 1
        assert p.runs[0].text == "New text"

    def test_cell_text_preserves_format(self):
        r1 = MockRun("Original", bold=True)
        p = MockParagraph([r1])
        cell = MockCell([p])

        replace_cell_text_preserving_format(cell, "Updated")

        assert r1.text == "Updated"
        assert r1.bold is True

    def test_cell_fallback_when_no_paragraphs(self):
        cell = MockCell([])

        replace_cell_text_preserving_format(cell, "Fallback")

        assert cell.text == "Fallback"
