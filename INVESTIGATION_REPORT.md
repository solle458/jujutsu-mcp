# Jujutsu MCP 実装調査レポート

## 調査日
2026年2月7日

## 調査範囲
- プロジェクトコードの実装確認
- Jujutsu公式ドキュメントの確認
- 実際のコマンド実行による動作確認
- Web/SNSでの最新情報の調査

## 発見された問題点

### 1. ❌ `jj log --template json` が存在しない

**問題:**
- `src/jujutsu_mcp/jj_commands.py`の84行目で`--template json`を使用しているが、Jujutsuには`json`というテンプレートキーワードは存在しない
- 実際の実行結果: `Error: Failed to parse template: Keyword 'json' doesn't exist`

**正しい実装方法:**
Jujutsuのテンプレート言語を使ってJSON形式を手動で構築する必要がある。例:
```python
template = '"{' ++ '"commit_id": "' ++ commit_id ++ '", "description": "' ++ description ++ '", "author": "' ++ author.name() ++ '", "timestamp": "' ++ timestamp() ++ '", "parents": [' ++ parents.map(x => x.commit_id()).join(", ") ++ ']}"'
```

または、複数の`jj log`コマンドを実行して個別のフィールドを取得し、Python側でJSONを構築する方法もある。

**影響範囲:**
- `get_log()`関数 (84行目)
- `describe_revision()`関数 (131行目)
- `undo_last_op()`関数 (181行目)

### 2. ❌ `jj diff --conflicts` オプションが存在しない

**問題:**
- `src/jujutsu_mcp/jj_commands.py`の142行目と253行目で`jj diff --conflicts`を使用しているが、このオプションは存在しない
- 実際の実行結果: `error: unexpected argument '--conflicts' found`

**正しい実装方法:**
`jj resolve --list`を使用してconflictを検出する:
```python
stdout, _ = run_jj_command(["resolve", "--list", "-r", revision_id])
has_conflicts = bool(stdout.strip())
```

または、`jj show`や`jj log`でconflictフラグを確認する方法もある。

**影響範囲:**
- `describe_revision()`関数 (142行目)
- `get_status()`関数 (253行目)
- `resolve_conflicts()`関数 (288行目)

### 3. ⚠️ `jj new -p` オプションの使い方

**問題:**
- `src/jujutsu_mcp/jj_commands.py`の212行目で`-p`オプションを使用しているが、`jj new`には`-p`オプションは存在しない
- 親は引数として直接指定する必要がある

**正しい実装方法:**
```python
args = ["new"]
if parent:
    args.append(parent)  # -pではなく直接引数として指定
```

**影響範囲:**
- `new_change()`関数 (212行目)

### 4. ⚠️ `jj op log --template json` が存在しない

**問題:**
- `src/jujutsu_mcp/jj_commands.py`の181行目で`--template json`を使用しているが、`json`キーワードは存在しない

**正しい実装方法:**
テンプレート言語を使ってJSON形式を構築するか、個別のフィールドを取得してPython側でJSONを構築する。

**影響範囲:**
- `undo_last_op()`関数 (181行目)

### 5. ⚠️ Conflict検出の実装が不完全

**問題:**
- `resolve_conflicts()`関数は実際にはconflictを解決していない（検出のみ）
- 関数名と実装が一致していない

**推奨事項:**
- 関数名を`detect_conflicts()`に変更するか、実際にconflictを解決する機能を追加する

### 6. ⚠️ `get_status()`の実装が不正確

**問題:**
- `jj status`コマンドの出力を単純に`bool(stdout.strip())`で判定しているが、これは正確ではない
- `jj status`は常に何らかの出力を返す可能性がある

**推奨事項:**
`jj status --porcelain`を使用して機械可読形式で取得するか、`jj log -r @`でworking copyの状態を確認する。

## 確認された正しい実装

### ✅ `jj rebase -s -o` の使い方
- `smart_rebase()`関数の実装は正しい（169行目）

### ✅ `jj squash --from --into` の使い方
- `squash_changes()`関数の実装は正しい（231行目）

## 修正が必要な箇所の詳細

### 修正1: JSONテンプレートの構築

**現在のコード (84行目):**
```python
args = ["log", "--template", "json"]
```

**修正案:**
```python
# 方法1: テンプレート言語でJSONを構築
template = (
    '"{' ++
    '"commit_id": "' ++ commit_id ++ '", ' ++
    '"description": ' ++ if(description == "", "null", '"' ++ description ++ '"') ++ ', ' ++
    '"author": {' ++ '"name": "' ++ author.name() ++ '", "email": "' ++ author.email() ++ '"}, ' ++
    '"timestamp": "' ++ timestamp() ++ '", ' ++
    '"parents": [' ++ parents.map(x => '"' ++ x.commit_id() ++ '"').join(", ") ++ ']' ++
    '}"'
)
args = ["log", "--template", template]

# 方法2: 個別のフィールドを取得してPython側でJSONを構築（推奨）
# より柔軟で保守しやすい
```

### 修正2: Conflict検出の修正

**現在のコード (142行目):**
```python
conflict_stdout, _ = run_jj_command(["diff", "-r", revision_id, "--conflicts"])
has_conflicts = bool(conflict_stdout.strip())
```

**修正案:**
```python
try:
    conflict_stdout, _ = run_jj_command(["resolve", "--list", "-r", revision_id])
    has_conflicts = bool(conflict_stdout.strip())
except JujutsuCommandError:
    has_conflicts = False
```

### 修正3: `jj new`の親指定の修正

**現在のコード (212行目):**
```python
if parent:
    args.extend(["-p", parent])
```

**修正案:**
```python
if parent:
    args.append(parent)  # -pオプションではなく直接引数として指定
```

## 推奨される修正手順

1. **優先度: 高** - `jj diff --conflicts`の修正（動作しない）
2. **優先度: 高** - `jj log --template json`の修正（動作しない）
3. **優先度: 中** - `jj new -p`の修正（動作するが正しくない）
4. **優先度: 中** - `jj op log --template json`の修正（動作しない）
5. **優先度: 低** - 関数名の見直しとドキュメントの更新

## 参考資料

- [Jujutsu公式ドキュメント](https://docs.jj-vcs.dev/latest/)
- [Jujutsu CLI Reference](https://docs.jj-vcs.dev/latest/cli-reference/)
- [Jujutsu Templates](https://docs.jj-vcs.dev/latest/templates/)
- [Jujutsu Conflicts](https://docs.jj-vcs.dev/latest/conflicts/)

## 結論

このMCPサーバーは基本的な構造は正しいが、いくつかの重要な実装エラーがあり、実際には動作しない部分がある。特にJSONテンプレートとconflict検出の実装を修正する必要がある。
