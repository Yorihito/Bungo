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
        "inputs",
        metavar="INPUT",
        nargs="+",
        help="変換する文豪miniの文書ファイル (ワイルドカード等で複数指定可能)",
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
        help="出力ファイルパスまたはディレクトリ (複数ファイル時はディレクトリとして扱われます)",
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
    path = Path(input_path)
    return str(path.with_suffix(f".{fmt}"))


def main(argv: list[str] | None = None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)

    inputs: list[str] = args.inputs
    fmt: str = args.fmt
    output_arg: str | None = args.output
    header_size: int | None = args.header_size

    success_count = 0
    error_count = 0

    for input_path in inputs:
        # Determine output path
        if output_arg:
            out_p = Path(output_arg)
            if out_p.is_dir() or len(inputs) > 1:
                # If it's a directory or we have multiple files, treat output_arg as base dir
                actual_output = str(out_p / Path(input_path).with_suffix(f".{fmt}").name)
                # Create directory if it doesn't exist
                out_p.mkdir(parents=True, exist_ok=True)
            else:
                actual_output = output_arg
        else:
            actual_output = _default_output(input_path, fmt)

        # ── Parse ────────────────────────────────────────────────────────────
        try:
            parser = BungoParser(input_path, header_size=header_size)
            doc = parser.parse()
            # ── Convert ──────────────────────────────────────────────────────
            convert(doc, actual_output, fmt)
            print(f"変換完了: {input_path} -> {actual_output}")
            success_count += 1
        except Exception as exc:  # noqa: BLE001
            print(f"エラー ({input_path}): {exc}", file=sys.stderr)
            error_count += 1

    if len(inputs) > 1:
        print(f"\n全{len(inputs)}件中 {success_count}件成功, {error_count}件失敗")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
