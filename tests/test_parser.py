"""
Tests for bungo.parser.BungoParser.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from bungo.parser import BungoParser, BungoDocument, HEADER_SIZE_MINI5
from tests.fixtures import make_bungo_doc


# ---------------------------------------------------------------------------
# BungoParser — basic round-trip
# ---------------------------------------------------------------------------


class TestBungoParser:
    def test_parse_returns_bungo_document(self, tmp_path):
        raw = make_bungo_doc(["Hello World"])
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        assert isinstance(doc, BungoDocument)

    def test_single_ascii_paragraph(self, tmp_path):
        raw = make_bungo_doc(["Hello World"])
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        assert "Hello World" in doc.full_text

    def test_multiple_paragraphs(self, tmp_path):
        paragraphs = ["First paragraph", "Second paragraph", "Third paragraph"]
        raw = make_bungo_doc(paragraphs)
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        for para in paragraphs:
            assert para in doc.full_text

    def test_japanese_text(self, tmp_path):
        paragraphs = ["日本語のテキストです。", "文豪miniのドキュメント。"]
        raw = make_bungo_doc(paragraphs)
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        assert "日本語のテキストです。" in doc.full_text
        assert "文豪miniのドキュメント。" in doc.full_text

    def test_paragraphs_list_matches_content(self, tmp_path):
        paragraphs = ["One", "Two", "Three"]
        raw = make_bungo_doc(paragraphs)
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        for para in paragraphs:
            assert any(para in p for p in doc.paragraphs)

    def test_explicit_header_size(self, tmp_path):
        custom_header_size = 256
        raw = make_bungo_doc(["Explicit header"], header_size=custom_header_size)
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p), header_size=custom_header_size).parse()

        assert "Explicit header" in doc.full_text

    def test_page_break_produces_blank_line(self, tmp_path):
        # Build a document with a form-feed (0x0C) manually
        header = b"\x00" * HEADER_SIZE_MINI5
        body = b"Page1\x0cPage2\x1a"
        p = tmp_path / "doc.bin"
        p.write_bytes(header + body)

        doc = BungoParser(str(p)).parse()
        text = doc.full_text

        assert "Page1" in text
        assert "Page2" in text

    def test_control_codes_skipped(self, tmp_path):
        # Embed some non-text control bytes between printable content
        header = b"\x00" * HEADER_SIZE_MINI5
        body = b"Before\x01\x02\x03After\x1a"
        p = tmp_path / "doc.bin"
        p.write_bytes(header + body)

        doc = BungoParser(str(p)).parse()

        assert "Before" in doc.full_text
        assert "After" in doc.full_text

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            BungoParser("/nonexistent/path/to/document.doc").parse()

    def test_empty_document(self, tmp_path):
        raw = make_bungo_doc([])
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        assert isinstance(doc, BungoDocument)

    def test_full_text_property(self, tmp_path):
        paragraphs = ["Line A", "Line B"]
        raw = make_bungo_doc(paragraphs)
        p = tmp_path / "doc.bin"
        p.write_bytes(raw)

        doc = BungoParser(str(p)).parse()

        assert doc.full_text == "\n".join(doc.paragraphs)

    def test_null_terminated_document(self, tmp_path):
        header = b"\x00" * HEADER_SIZE_MINI5
        # Text followed by a long run of nulls (simulates null-padded storage)
        body = "Hello\r\n".encode("shift_jis") + b"\x00" * 20
        p = tmp_path / "doc.bin"
        p.write_bytes(header + body)

        doc = BungoParser(str(p)).parse()

        assert "Hello" in doc.full_text

    def test_half_width_kana(self, tmp_path):
        header = b"\x00" * HEADER_SIZE_MINI5
        # ｱｲｳ in Shift-JIS half-width kana (0xB1, 0xB2, 0xB3)
        body = b"\xb1\xb2\xb3\x0d\x0a\x1a"
        p = tmp_path / "doc.bin"
        p.write_bytes(header + body)

        doc = BungoParser(str(p)).parse()

        assert "ｱｲｳ" in doc.full_text
