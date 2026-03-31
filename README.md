# Bungo

**文豪miniのフォーマットのドキュメントをテキストかワードに変換するコマンドラインツール。**

NEC 文豪mini シリーズのワープロ専用機で作成した文書ファイルをプレーンテキスト (`.txt`) または Microsoft Word (`.docx`) に変換します。

---

## 動作環境

- Python 3.9 以降
- python-docx (`.docx` 出力時に必要)

## インストール

```bash
pip install -r requirements.txt
```

## 使い方

```bash
python bungo_converter.py <入力ファイル> [-f txt|docx] [-o <出力ファイル>]
```

### 引数

| 引数 | 説明 |
|------|------|
| `INPUT` | 変換する文豪miniの文書ファイル |
| `-f`, `--format` | 出力フォーマット: `txt` (デフォルト) または `docx` |
| `-o`, `--output` | 出力ファイルパス (省略時は入力と同じディレクトリに出力) |
| `--header-size` | ヘッダのバイト数を明示的に指定 (デフォルト: 自動検出、文豪mini5は 512) |

### 使用例

```bash
# テキストに変換 (デフォルト)
python bungo_converter.py document.doc

# Wordファイルに変換
python bungo_converter.py document.doc -f docx

# 出力先を指定してテキストに変換
python bungo_converter.py document.doc -f txt -o ~/Documents/output.txt

# ヘッダサイズを明示指定 (文豪mini5)
python bungo_converter.py document.doc --header-size 512
```

## ファイルフォーマットについて

文豪mini の文書ファイルはプロプライエタリなバイナリ形式で保存されています。

- **ヘッダ部** (先頭約 512 バイト): 文書のメタデータや属性情報
- **本文部** (ヘッダ以降): Shift-JIS でエンコードされたテキスト
  - `0x0D` / `0x0A` — 改行
  - `0x0C` — 改ページ
  - `0x1A` — 文書終端 (CP/M EOF)
  - その他の制御コード — スキップ

本ツールはヘッダ部を自動検出してスキップし、本文部のテキストを抽出します。
変換できるのはテキストと罫線情報のみです。レイアウト・画像などは抽出対象外です。

## テスト

```bash
python -m pytest tests/ -v
```
