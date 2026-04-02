"""
Parser for NEC 文豪mini word processor binary document format.

The 文豪mini (Bungo mini) is a Japanese word processor by NEC from the
1980s/1990s. Documents are stored in a proprietary binary format with:

- A header section (~512 bytes) containing document metadata
- Text content encoded in Shift-JIS
- Control codes embedded in the text for formatting

File format structure:
- Offset 0x000: File header (magic bytes, metadata)
- Offset 0x200: Text content area (Shift-JIS encoded)
  - 0x0D (CR): Line break
  - 0x0A (LF): Line break
  - 0x0C (FF): Page break
  - 0x1A (EOF): End of document
  - 0x00: Null / padding
  - Other bytes < 0x20: Control/formatting codes (skipped)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# Known header sizes for 文豪mini series
HEADER_SIZE_MINI5 = 0x200  # 512 bytes — 文豪mini5 series
HEADER_SIZE_BUNGO_DOC = 0x2000  # 8192 bytes — Bungo DOC format
HEADER_SIZE_DEFAULT = 0x200

# Minimum fraction of "printable" bytes to consider a region as text
_MIN_TEXT_FRACTION = 0.25

# How many consecutive null bytes signal end-of-document
_NULL_TERMINATOR_LENGTH = 10


@dataclass
class BungoSegment:
    """A segment of text that can be normal or ruby/annotation."""
    text: str
    is_ruby: bool = False


@dataclass
class BungoDocument:
    """Parsed content of a 文豪mini document."""

    paragraphs: list[list[BungoSegment]] = field(default_factory=list)
    """Each element is a list of segments forming one paragraph."""

    @property
    def full_text(self) -> str:
        """The entire document as a single string (including Ruby)."""
        lines = []
        for para in self.paragraphs:
            lines.append("".join(s.text for s in para))
        return "\n".join(lines)


class BungoParser:
    """Parse NEC 文豪mini binary document files.

    Usage::

        parser = BungoParser("document.doc")
        doc = parser.parse()
        print(doc.full_text)
    """

    def __init__(self, filepath: str, header_size: Optional[int] = None) -> None:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        self.filepath = filepath
        self._header_size = header_size
        self._data: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> BungoDocument:
        """Load and parse the document, returning a :class:`BungoDocument`."""
        self._load()
        offset = self._detect_text_start()
        segments = self._extract_segments(offset)
        paragraphs = self._split_paragraphs(segments)
        return BungoDocument(paragraphs=paragraphs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        with open(self.filepath, "rb") as fh:
            self._data = fh.read()

    def _detect_text_start(self) -> int:
        """Heuristically locate where the text content begins."""
        data = self._data

        if self._header_size is not None:
            # Caller specified the header size explicitly — trust it.
            return min(self._header_size, len(data))

        # Try the DOC header size first.
        if len(data) > HEADER_SIZE_BUNGO_DOC:
            # Check for the characteristic 4-byte JIS pattern at 0x2000
            chunk = data[HEADER_SIZE_BUNGO_DOC : HEADER_SIZE_BUNGO_DOC + 128]
            if self._is_4byte_jis(chunk):
                return HEADER_SIZE_BUNGO_DOC

        # Try the canonical 文豪mini5 header size.
        candidate = HEADER_SIZE_MINI5
        if len(data) > candidate and self._text_fraction(data[candidate:candidate + 128]) >= _MIN_TEXT_FRACTION:
            return candidate

        # Fallback: scan forward until we find a region that looks like text.
        for start in range(0, min(len(data), HEADER_SIZE_DEFAULT + 1), 16):
            chunk = data[start: start + 128]
            if self._text_fraction(chunk) >= _MIN_TEXT_FRACTION:
                return start

        # Last resort: start from the very beginning.
        return 0

    @staticmethod
    def _is_4byte_jis(data: bytes) -> bool:
        """Check if *data* looks like 4-byte JIS encoded text."""
        if len(data) < 4:
            return False
        # Count blocks that start with 00 00 or 00 0F
        count = 0
        for i in range(0, (len(data) // 4) * 4, 4):
            if data[i] == 0x00 and (data[i + 1] == 0x00 or data[i + 1] == 0x0F):
                count += 1
        return count >= (len(data) // 16)

    @staticmethod
    def _text_fraction(data: bytes) -> float:
        """Return the fraction of bytes in *data* that appear to be text."""
        if not data:
            return 0.0
        printable = 0
        i = 0
        while i < len(data):
            b = data[i]
            if 0x20 <= b <= 0x7E:          # ASCII printable
                printable += 1
                i += 1
            elif 0xA1 <= b <= 0xDF:        # Half-width kana (Shift-JIS single byte)
                printable += 1
                i += 1
            elif b in (0x0A, 0x0D, 0x0C):  # Line / page break — definitely text
                printable += 1
                i += 1
            elif (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC) and i + 1 < len(data):
                b2 = data[i + 1]
                if 0x40 <= b2 <= 0xFC and b2 != 0x7F:
                    printable += 2          # Valid 2-byte Shift-JIS character
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        return printable / len(data)

    def _extract_segments(self, offset: int) -> list[BungoSegment]:
        """Extract text segments from *self._data* starting at *offset*."""
        data = self._data
        if not data:
            return []

        # Determine if we are in 4-byte JIS mode
        sample = data[offset : offset + 128]
        if self._is_4byte_jis(sample):
            return self._extract_segments_4byte(offset)

        return self._extract_segments_legacy(offset)

    def _extract_segments_legacy(self, offset: int) -> list[BungoSegment]:
        """Legacy Shift-JIS segment extraction."""
        data = self._data
        res: list[BungoSegment] = []
        i = offset
        while i < len(data):
            b = data[i]

            # ── End-of-document markers ──────────────────────────────
            if b == 0x1A:          # Ctrl+Z (CP/M EOF)
                break

            if b == 0x00:
                # Count consecutive nulls; a long run means end-of-text.
                run = 0
                j = i
                while j < len(data) and data[j] == 0x00:
                    run += 1
                    j += 1
                if run >= _NULL_TERMINATOR_LENGTH:
                    break
                # Short null run — might just be padding, skip and continue.
                i = j
                continue

            # ── Line/page breaks ─────────────────────────────────────
            if b == 0x0D:
                if i + 1 < len(data) and data[i + 1] == 0x0A:
                    res.append(BungoSegment("\n"))
                    i += 2
                else:
                    res.append(BungoSegment("\n"))
                    i += 1
                continue

            if b == 0x0A:
                res.append(BungoSegment("\n"))
                i += 1
                continue

            if b == 0x0C:          # Form feed → paragraph break
                res.append(BungoSegment("\n\n"))
                i += 1
                continue

            # ── Other control characters ─────────────────────────────
            if b < 0x20:
                i += 1             # Skip formatting/control codes
                continue

            # ── ASCII printable ──────────────────────────────────────
            if 0x20 <= b <= 0x7E:
                res.append(BungoSegment(chr(b)))
                i += 1
                continue

            # ── Half-width kana (single byte Shift-JIS) ──────────────
            if 0xA1 <= b <= 0xDF:
                try:
                    res.append(BungoSegment(bytes([b]).decode("shift_jis")))
                except (UnicodeDecodeError, ValueError):
                    pass
                i += 1
                continue

            # ── Double-byte Shift-JIS character ─────────────────────
            if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC) and i + 1 < len(data):
                b2 = data[i + 1]
                if 0x40 <= b2 <= 0xFC and b2 != 0x7F:
                    try:
                        res.append(BungoSegment(bytes([b, b2]).decode("shift_jis")))
                    except (UnicodeDecodeError, ValueError):
                        pass
                    i += 2
                    continue

            # ── Unrecognised byte — skip ─────────────────────────────
            i += 1

        return res

    def _extract_segments_4byte(self, offset: int) -> list[BungoSegment]:
        """Extract text from 4-byte JIS encoded data."""
        data = self._data
        res: list[BungoSegment] = []
        i = offset

        while i + 3 < len(data):
            unit = data[i : i + 4]
            b0, b1, b2, b3 = unit

            # Line break / Special control
            if b0 == 0x40 and b1 == 0x20:
                res.append(BungoSegment("\n"))
                i += 4
                continue

            if b0 == 0x40 and b1 == 0x7F:
                # End of document marker
                break

            if b1 == 0x00:
                # Full-width JIS X 0208
                if b2 == 0x00 and b3 == 0x00:
                    pass  # Padding
                elif 0x21 <= b2 <= 0x7E and 0x21 <= b3 <= 0x7E:
                    try:
                        # Convert JIS to EUC-JP for decoding
                        char = bytes([b2 + 0x80, b3 + 0x80]).decode("euc-jp")
                        res.append(BungoSegment(char))
                    except (UnicodeDecodeError, ValueError):
                        pass
            elif b1 == 0x0F:
                # Half-width kana (JIS X 0201) / Ruby
                # 0xA1 (｡) is often used as a redundant filler prefix in 4-byte units.
                if b2 == 0xA1 and b3 != 0xA1:
                    # Single character in b3 (common case)
                    try:
                        char = bytes([b3]).decode("cp932")
                        res.append(BungoSegment(char, is_ruby=True))
                    except (UnicodeDecodeError, ValueError):
                        pass
                else:
                    # Two characters in b2 and b3 (or something else)
                    for sb in (b2, b3):
                        if 0xA1 <= sb <= 0xDF:
                            try:
                                char = bytes([sb]).decode("cp932")
                                res.append(BungoSegment(char, is_ruby=True))
                            except (UnicodeDecodeError, ValueError):
                                pass
                        elif 0x20 <= sb <= 0x7E:
                            res.append(BungoSegment(chr(sb), is_ruby=True))

            i += 4

        return res

    @staticmethod
    def _split_paragraphs(segments: list[BungoSegment]) -> list[list[BungoSegment]]:
        """Split a list of segments into paragraphs by line breaks."""
        paragraphs: list[list[BungoSegment]] = []
        current_para: list[BungoSegment] = []

        for s in segments:
            if s.text == "\n":
                paragraphs.append(current_para)
                current_para = []
            elif s.text == "\n\n":
                paragraphs.append(current_para)
                paragraphs.append([])  # Blank line
                current_para = []
            else:
                current_para.append(s)

        if current_para:
            paragraphs.append(current_para)

        # Drop trailing empty paragraphs
        while paragraphs and not paragraphs[-1]:
            paragraphs.pop()

        return paragraphs if paragraphs else [[]]
