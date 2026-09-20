<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ishiji-git. All rights reserved. -->

# filecheckcopy

> 初版は GitHub Copilot Free を利用して生成しました。

filecheckcopy は Windows 向けの Python ツールで、ディレクトリ間で変更のあったファイルだけをコピーします。ファイルの内容とメタデータを比較し、dry-run、ログ出力、並列処理、進捗表示に対応し、空ディレクトリも保持します。

## 概要

このツールは、コピー元からコピー先へファイルを転送する際に、変更のない内容はスキップします。サイズ比較、必要に応じた時刻比較、ハッシュ比較を使ってコピーの要否を判定し、バックアップや同期で差分だけを効率的に転送できます。

主な用途:

- 大容量ファイルのバックアップ時に無駄なコピーを避ける
- NAS やリモートマウント先への書き込み負荷を軽減する
- 既存バックアップとの差分だけを更新する

## 仕様

- Windows 系 OS を前提とする
- Python 3 で動作する
- ファイルまたはディレクトリを対象にできる
- ディレクトリ指定時は再帰的に走査する
- 空ディレクトリも作成する
- ファイルの時刻が違っていても、内容が同じならコピーしない
- 内容の差分判定はハッシュ値で行う
- `--skip-same-mtime` で、同一時刻ならスキップ可能
- `--dry-run` で実際のコピーを行わずに動作確認可能
- `--exclude-dir` / `--exclude-file` で除外対象を明示的に指定可能
- デフォルトの除外ルールは設定しない; 除外はユーザーが明示的に指定した場合のみ有効
- `--log-file` でコピー結果をファイルに記録可能; 開始時刻・終了時刻・経過時間も記録される
- `--parallel` で並列処理数を指定可能
- `--progress` で処理中の進捗を表示可能

## 使い方

### 1. 基本

```bash
python filecheckcopy.py source_dir target_dir
```

### 2. 実際にコピーせず確認したい

```bash
python filecheckcopy.py source_dir target_dir --dry-run --verbose
```

### 3. 時刻が同じならスキップしたい

```bash
python filecheckcopy.py source_dir target_dir --skip-same-mtime
```

### 4. 除外したいものを明示的に指定する

```bash
python filecheckcopy.py source_dir target_dir --exclude-dir .git --exclude-dir .svn --exclude-file Thumbs.db
```

この除外は、オプションを明示した場合にのみ有効です。

### 5. ログをファイルに残したい

```bash
python filecheckcopy.py source_dir target_dir --log-file C:\logs\filecheckcopy.log
```

ログには開始時刻、各ファイルのコピー/スキップ状況、最終的な終了時刻と経過時間が見やすい形式で記録されます。

ログ例:

```text
Operation started: [2026-09-20 12:34:56] C:\backup-src -> C:\backup-dst
Copying: C:\backup-src\a.txt -> C:\backup-dst\a.txt
Skipped (unchanged): C:\backup-src\b.txt
Operation completed: [2026-09-20 12:34:57] Elapsed: 0.123s
Result: copied=1, skipped=1
```

### 6. 並列コピーを使いたい

```bash
python filecheckcopy.py source_dir target_dir --parallel 4 --verbose
```

### 7. 進捗表示を見たい

```bash
python filecheckcopy.py source_dir target_dir --progress --parallel 4
```

### 8. 単一ファイルコピー

```bash
python filecheckcopy.py C:\src\a.txt C:\dst\
```

## 判定ロジック

コピーの要否は次の順で判定します。

1. 対象ファイルが存在しない場合はコピー
2. サイズが異なる場合はコピー
3. `--skip-same-mtime` が有効で、時刻が同一ならスキップ
4. ハッシュ値を比較して異なればコピー
5. それ以外はスキップ

## 実行例

```bash
python filecheckcopy.py C:\backup-src C:\backup-dst --dry-run --verbose --log-file C:\logs\copy.log --parallel 2
```

出力例:

```text
Copying: C:\backup-src\a.txt -> C:\backup-dst\a.txt
Skipped (unchanged): C:\backup-src\b.txt
Files copied: 1
Files skipped: 1
```

ログファイルにも同じ内容が追記されます。

## 注意点

- ハッシュは `MD5` を使用しています
- 要件上、ハッシュ衝突を重視していないため、速度と簡便性を優先した実装です
- Windows ではファイル属性や更新時刻を可能な範囲で保持するようにしています
- `--parallel` はファイル単位の並列化であり、I/O がボトルネックになる環境では効果が大きいです

## 開発メモ

対象のテストは `tests/test_filecheckcopy.py` にあります。

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

テスト対象:

- 差分ファイルのみコピーされる
- `--skip-same-mtime` が動作する
- `--dry-run` が書き込みを行わない
- `--log-file` が出力される
- `--parallel` が安全に動作する
