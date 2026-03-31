#!/usr/bin/env python3
"""
bungo_converter.py — Command-line tool to convert NEC 文豪mini documents.

Usage:
    python bungo_converter.py <input_file> [-f txt|docx] [-o <output_file>]

Examples:
    python bungo_converter.py document.doc
    python bungo_converter.py document.doc -f docx
    python bungo_converter.py document.doc -f txt -o output.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bungo.converter import convert
from bungo.parser import BungoParser


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="bungo_converter",
        description="文豪miniのフォーマットのドキュメントをテキストかワードに変換します。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s document.doc
  %(prog)s document.doc -f docx
  %(prog)s document.doc -f txt -o output.txt
  %(prog)s document.doc --header-size 512
""",
    )
    ap.add_argument(
        "input",
        metavar="INPUT",
        help="変換する文豪miniの文書ファイル",
    )
    ap.add_argument(
        "-f", "--format",
        dest="fmt",
        metavar="FORMAT",
        choices=("txt", "docx"),
        default="txt",
        help="出力フォーマット: txt (デフォルト) または docx",
    )
    ap.add_argument(
        "-o", "--output",
        metavar="OUTPUT",
        default=None,
        help="出力ファイルパス (省略時は入力ファイルと同じディレクトリに出力)",
    )
    ap.add_argument(
        "--header-size",
        metavar="BYTES",
        type=int,
        default=None,
        help=(
            "ヘッダのバイト数を明示的に指定します (デフォルト: 自動検出)。"
            " 文豪mini5の場合は 512 (0x200) が一般的です。"
        ),
    )
    return ap


def _default_output(input_path: str, fmt: str) -> str:
    stem = Path(input_path).stem
    parent = Path(input_path).parent
    return str(parent / f"{stem}.{fmt}")


def main(argv: list[str] | None = None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)

    input_path: str = args.input
    fmt: str = args.fmt
    output_path: str = args.output or _default_output(input_path, fmt)
    header_size: int | None = args.header_size

    # ── Parse ────────────────────────────────────────────────────────────
    try:
        parser = BungoParser(input_path, header_size=header_size)
        doc = parser.parse()
    except FileNotFoundError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"解析エラー: {exc}", file=sys.stderr)
        return 1

    # ── Convert ──────────────────────────────────────────────────────────
    try:
        convert(doc, output_path, fmt)
    except Exception as exc:  # noqa: BLE001
        print(f"変換エラー: {exc}", file=sys.stderr)
        return 1

    print(f"変換完了: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
