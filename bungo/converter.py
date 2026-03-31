"""
Output converters for parsed 文豪mini documents.

Supported output formats:

* **txt** – Plain-text UTF-8 file.
* **docx** – Microsoft Word Open XML document (via *python-docx*).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

from .parser import BungoDocument

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# Plain text
# ---------------------------------------------------------------------------


def to_text(doc: BungoDocument, output_path: PathLike) -> None:
    """Write *doc* as a plain-text file encoded in UTF-8.

    Each paragraph is written on its own line; an extra blank line is inserted
    between paragraphs so the output is readable without further formatting.

    Args:
        doc: Parsed :class:`~bungo.parser.BungoDocument`.
        output_path: Destination file path (created or overwritten).
    """
    text = doc.full_text
    Path(output_path).write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Microsoft Word (.docx)
# ---------------------------------------------------------------------------


def to_docx(doc: BungoDocument, output_path: PathLike) -> None:
    """Write *doc* as a Microsoft Word (*.docx*) file.

    Each paragraph from the source document becomes a Word paragraph.  The
    document uses the default Normal style so that it can be opened and
    reformatted freely in Word.

    Args:
        doc: Parsed :class:`~bungo.parser.BungoDocument`.
        output_path: Destination file path (created or overwritten).

    Raises:
        ImportError: If *python-docx* is not installed.
    """
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "python-docx is required for Word output.  "
            "Install it with: pip install python-docx"
        ) from exc

    word_doc = Document()

    for para_text in doc.paragraphs:
        word_doc.add_paragraph(para_text)

    # Ensure parent directory exists.
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    word_doc.save(str(output_path))


# ---------------------------------------------------------------------------
# Convenience helper used by the CLI
# ---------------------------------------------------------------------------


def convert(doc: BungoDocument, output_path: PathLike, fmt: str) -> None:
    """Dispatch to the appropriate converter based on *fmt*.

    Args:
        doc: Parsed document.
        output_path: Destination path.
        fmt: ``"txt"`` or ``"docx"``.

    Raises:
        ValueError: If *fmt* is not a recognised format name.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt == "txt":
        to_text(doc, output_path)
    elif fmt == "docx":
        to_docx(doc, output_path)
    else:
        raise ValueError(f"Unsupported output format: {fmt!r}.  Choose 'txt' or 'docx'.")
