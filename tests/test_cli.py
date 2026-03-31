"""
Integration tests for the bungo_converter CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the repo root is on the path so we can import bungo_converter
sys.path.insert(0, str(Path(__file__).parent.parent))

from bungo_converter import main
from tests.fixtures import make_bungo_doc


def _write_doc(tmp_path: Path, paragraphs: list[str], name: str = "doc.bin") -> Path:
    raw = make_bungo_doc(paragraphs)
    p = tmp_path / name
    p.write_bytes(raw)
    return p


class TestCLI:
    def test_default_txt_output(self, tmp_path):
        src = _write_doc(tmp_path, ["Hello", "World"])
        ret = main([str(src)])
        assert ret == 0
        out = tmp_path / "doc.txt"
        assert out.exists()
        assert "Hello" in out.read_text(encoding="utf-8")

    def test_explicit_txt_format(self, tmp_path):
        src = _write_doc(tmp_path, ["テスト"])
        ret = main([str(src), "-f", "txt"])
        assert ret == 0
        out = tmp_path / "doc.txt"
        assert out.exists()

    def test_docx_format(self, tmp_path):
        src = _write_doc(tmp_path, ["テスト"])
        ret = main([str(src), "-f", "docx"])
        assert ret == 0
        out = tmp_path / "doc.docx"
        assert out.exists()

    def test_explicit_output_path(self, tmp_path):
        src = _write_doc(tmp_path, ["Custom output"])
        out = tmp_path / "my_output.txt"
        ret = main([str(src), "-o", str(out)])
        assert ret == 0
        assert out.exists()
        assert "Custom output" in out.read_text(encoding="utf-8")

    def test_nonexistent_input_returns_error(self, tmp_path):
        ret = main([str(tmp_path / "nonexistent.doc")])
        assert ret == 1

    def test_explicit_header_size(self, tmp_path):
        raw = make_bungo_doc(["Header size test"], header_size=256)
        src = tmp_path / "doc.bin"
        src.write_bytes(raw)
        ret = main([str(src), "--header-size", "256"])
        assert ret == 0
        out = tmp_path / "doc.txt"
        assert "Header size test" in out.read_text(encoding="utf-8")
