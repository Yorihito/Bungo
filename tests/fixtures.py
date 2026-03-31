"""
Helpers for building synthetic 文豪mini binary test fixtures.
"""

from __future__ import annotations


def make_bungo_doc(
    paragraphs: list[str],
    header_size: int = 0x200,
    encoding: str = "shift_jis",
) -> bytes:
    """
    Build a minimal synthetic 文豪mini binary document.

    The returned bytes mimic the on-disk format:

    * A *header_size*-byte header padded with zeros (offset 0).
    * Text content starting at *header_size*, paragraphs separated by CR+LF
      (``\\r\\n``), terminated by Ctrl+Z (``0x1A``).

    Args:
        paragraphs: List of paragraph strings to embed.
        header_size: Size of the (dummy) header in bytes.
        encoding: Character encoding for the text section (default Shift-JIS).

    Returns:
        Raw bytes of the synthetic document.
    """
    header = b"\x00" * header_size

    text_parts: list[bytes] = []
    for para in paragraphs:
        text_parts.append(para.encode(encoding))
        text_parts.append(b"\r\n")

    # CP/M end-of-file marker
    text_parts.append(b"\x1a")

    return header + b"".join(text_parts)
