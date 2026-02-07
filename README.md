# Jujutsu MCP Server

Jujutsu (jj) バージョン管理システム用のMCP (Model Context Protocol) サーバー。このサーバーは、AIエージェントがJujutsuの強力なバージョン管理機能に構造化されたアクセスを提供する、明確に定義されたツールセットを提供します。

## 機能

- **構造化されたリビジョンアクセス**: リビジョンログと詳細をJSON構造として取得
- **スマート操作**: revsetを使用してリベース、スカッシュ、その他の操作を実行
- **コンフリクト検出**: プログラム的にコンフリクトを識別・分析
- **安全なアンドゥ**: 完全な操作履歴追跡で操作をアンドゥ
- **ステータス監視**: コンフリクトと未コミットの変更を含む現在のリポジトリステータスを取得

## インストール

### 前提条件

- Python 3.11以上
- [Jujutsu](https://github.com/martinvonz/jj) (jj) がインストールされ、PATHで利用可能
- [Nix](https://nixos.org/) (オプション、再現可能な開発環境用)
- [uv](https://github.com/astral-sh/uv) (Pythonパッケージマネージャー)

### Nixを使用する場合（推奨）

1. 開発シェルに入る:
   ```bash
   nix develop
   ```

2. 依存関係をインストール:
   ```bash
   uv sync
   ```

### 手動インストール

1. 依存関係をインストール:
   ```bash
   uv sync
   ```

2. 仮想環境をアクティベート:
   ```bash
   source .venv/bin/activate
   ```

## 使用方法

### MCPサーバーの実行

```bash
python -m jujutsu_mcp
```

または、uvを使用:

```bash
uv run python -m jujutsu_mcp
```

### MCPツール

サーバーは以下のツールを提供します:

#### `get_log`
リビジョンログを構造化されたグラフとして取得します。

**パラメータ:**
- `limit` (オプション): 返すリビジョンの最大数

**戻り値:** リビジョンと現在のリビジョンを含むリビジョングラフ

#### `describe_revision`
特定のリビジョンの詳細情報を取得します。

**パラメータ:**
- `revision_id`: リビジョンID (`@`, `@-`, `main` などのrevsetも可)

**戻り値:** 説明、作成者、親、コンフリクトステータスを含むリビジョン情報

#### `smart_rebase`
revsetを使用してリベース操作を実行します。

**パラメータ:**
- `source`: ソースリビジョン (revset)
- `destination`: 宛先リビジョン (revset)

**戻り値:** 成功メッセージ

#### `undo_last_op`
最後の操作を安全にアンドゥします。

**戻り値:** アンドゥされた操作に関する情報

#### `new_change`
新しい変更を作成します (`jj new` と同等)。

**パラメータ:**
- `parent` (オプション): 親リビジョン (revset)。デフォルトは現在の作業コピー。

**戻り値:** 新しいリビジョンID

#### `squash_changes`
あるリビジョンの変更を別のリビジョンにスカッシュします。

**パラメータ:**
- `revision`: スカッシュするリビジョン (revset)
- `into`: ターゲットリビジョン (revset)

**戻り値:** 成功メッセージ

#### `get_status`
現在のリポジトリステータスを取得します。

**戻り値:** 現在のリビジョン、未コミットの変更ステータス、コンフリクト

#### `resolve_conflicts`
リビジョン内のコンフリクトを検出・分析します。

**パラメータ:**
- `revision` (オプション): チェックするリビジョン (revset、デフォルトは `@`)

**戻り値:** コンフリクト情報のリスト

## 設定

### Cursor MCPサーバーセットアップ（自動起動）

CursorでこのMCPサーバーを自動起動で使用するには、Cursorの設定で設定する必要があります。

#### オプション1: プロジェクトレベル設定（推奨）

`~/.cursor/mcp.json` (またはプロジェクトルート) に以下の内容でファイルを作成:

```json
{
  "mcpServers": {
    "jujutsu-mcp": {
      "command": "/path/to/jujutsu-mcp/.venv/bin/python",
      "args": [
        "-m",
        "jujutsu_mcp"
      ],
      "cwd": "/path/to/jujutsu-mcp",
      "env": {
        "PYTHONPATH": "/path/to/jujutsu-mcp/src"
      }
    }
  }
}
```

**重要**: 
- `/path/to/jujutsu-mcp` をこのプロジェクトディレクトリの実際の絶対パスに置き換えてください。
- まず、jujutsu-mcpディレクトリで `uv sync` を実行して依存関係がインストールされていることを確認してください。
- `.venv` が存在しない場合は、`uv sync` を実行して作成し、依存関係をインストールしてください。

**ワークスペースパス検出について**: MCPサーバーは複数の方法を使用してjjリポジトリルートを自動検出します:
1. 環境変数 (`CURSOR_WORKSPACE_PATH`, `WORKSPACE_PATH`, `PWD`)
2. FastMCPコンテキストメタデータ (利用可能な場合)
3. 現在のディレクトリからの `jj root` コマンド
4. `.jj` ディレクトリの再帰的親ディレクトリ検索

別のリポジトリからMCPサーバーを使用していて `Error: There is no jj repo in "."` エラーが発生する場合は、`env` セクションに追加してワークスペースパスを明示的に設定できます:

```json
{
  "mcpServers": {
    "jujutsu-mcp": {
      "command": "/path/to/jujutsu-mcp/.venv/bin/python",
      "args": [
        "-m",
        "jujutsu_mcp"
      ],
      "cwd": "/path/to/jujutsu-mcp",
      "env": {
        "PYTHONPATH": "/path/to/jujutsu-mcp/src",
        "CURSOR_WORKSPACE_PATH": "${workspaceFolder}"
      }
    }
  }
}
```

注意: `${workspaceFolder}` はプレースホルダーです。Cursorが自動的に展開する場合もありますが、動作しない場合は、実際のパスを手動で設定するか、自動検出メカニズムに依存する必要があります。

**`uv run` を使用する代替方法** (上記が動作しない場合):

```json
{
  "mcpServers": {
    "jujutsu-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/jujutsu-mcp",
        "python",
        "-m",
        "jujutsu_mcp"
      ],
      "cwd": "/path/to/jujutsu-mcp",
      "env": {
        "PYTHONPATH": "/path/to/jujutsu-mcp/src",
        "CURSOR_WORKSPACE_PATH": "${workspaceFolder}"
      }
    }
  }
}
```

#### オプション2: グローバル設定

macOSの場合、編集または作成:
```
~/Library/Application Support/Code/User/globalStorage/tencent-cloud.coding-copilot/settings/Craft_mcp_settings.json
```

Windowsの場合:
```
%APPDATA%\Code\User\globalStorage\tencent-cloud.coding-copilot\settings\Craft_mcp_settings.json
```

Linuxの場合:
```
~/.config/Code/User/globalStorage/tencent-cloud.coding-copilot/settings/Craft_mcp_settings.json
```

オプション1と同じ設定を追加してください。

#### Nix環境を使用する場合

Nixを使用している場合、Nix環境を使用するように設定できます:

```json
{
  "mcpServers": {
    "jujutsu-mcp": {
      "command": "nix",
      "args": [
        "develop",
        "--command",
        "uv",
        "run",
        "python",
        "-m",
        "jujutsu_mcp"
      ],
      "cwd": "/path/to/jujutsu-mcp"
    }
  }
}
```

**注意**: 設定後、Cursorは起動時に自動的にMCPサーバーを起動します。毎回手動で起動する必要はありません。

### トラブルシューティング

#### エラー: "There is no jj repo in \".\""

このエラーは、MCPサーバーがjjリポジトリルートを検出できない場合に発生します。サーバーは複数の検出方法を使用します:

1. **環境変数**: `CURSOR_WORKSPACE_PATH`, `WORKSPACE_PATH`, `PWD` をチェック
2. **FastMCPコンテキスト**: MCPリクエストコンテキストからワークスペースパスを抽出しようと試みる
3. **jj rootコマンド**: 現在のディレクトリから `jj root` を実行
4. **再帰的検索**: 親ディレクトリで `.jj` ディレクトリを検索（最大20階層）

**解決方法**:

1. **MCP設定で環境変数を設定**: MCP設定の `env` セクションに `CURSOR_WORKSPACE_PATH` を追加（上記のオプション1を参照）

2. **jjリポジトリにいることを確認**: MCPサーバーは `.jj` ディレクトリを見つける必要があります。使用しているワークスペースが `jj init` で初期化されたjjリポジトリであることを確認してください

3. **MCPサーバーログを確認**: どの検出方法が試行されているかを確認するためにデバッグログを有効化:
   ```json
   {
     "mcpServers": {
       "jujutsu-mcp": {
         "command": "/path/to/jujutsu-mcp/.venv/bin/python",
         "args": ["-m", "jujutsu_mcp"],
         "env": {
           "PYTHONPATH": "/path/to/jujutsu-mcp/src",
           "PYTHONUNBUFFERED": "1"
         }
       }
     }
   }
   ```

4. **手動でワークスペースパスを設定**: 自動検出が失敗した場合、MCP設定の環境変数にワークスペースパスを手動で追加できます

### Git認証設定

GitHubへのプッシュ操作のためのGit認証設定の詳細な手順については、[Git認証設定ガイド](docs/GIT_AUTHENTICATION_SETUP.md)を参照してください。

ガイドには以下が含まれます:
- SSHキー認証（推奨）
- HTTPS用のPersonal Access Token (PAT) 設定
- 認証問題のトラブルシューティング
- 安全な認証のベストプラクティス

### Cursor Rules

このプロジェクトには、Jujutsuで作業する際のAIエージェントのベストプラクティスをガイドするCursor Rules (`.cursor/rules/jujutsu-policy.mdc`) が含まれています:

- 常に `git` を直接使用する代わりに `jj` コマンドを使用
- `jj new` で分離された作業単位を作成
- 意味のある説明で頻繁にコミット
- 変更を行う前にリビジョングラフを理解
- `jj evolog` を使用してコンフリクト履歴を理解

## 開発

### プロジェクト構造

```
jujutsu-mcp/
├── flake.nix                 # Nix環境定義
├── flake.lock                # Nixロックファイル
├── pyproject.toml            # Python依存関係
├── uv.lock                   # uvロックファイル
├── src/
│   └── jujutsu_mcp/
│       ├── __init__.py
│       ├── __main__.py       # エントリーポイント
│       ├── server.py         # MCPサーバー実装
│       ├── jj_commands.py    # jjコマンド実行ロジック
│       └── models.py          # データモデル
├── tests/                    # テストファイル
└── .cursor/
    └── rules/
        └── jujutsu-policy.mdc # Cursor Rules
```

### テストの実行

```bash
uv run pytest
```

### コードフォーマット

```bash
uv run ruff check .
uv run ruff format .
```

## アーキテクチャ

このプロジェクトは4層アーキテクチャに従います:

1. **インフラストラクチャ層 (Nix)**: 再現可能な開発環境
2. **ロジック層 (MCPサーバー)**: jjコマンドへの構造化されたJSONアクセス
3. **ポリシー層 (.mdc Rules)**: エージェントの動作ガイドライン
4. **実行層**: 高度なワークフロー（コンフリクト解決、タイムトラベル）

## ライセンス

Apache License 2.0

## コントリビューション

このプロジェクトはバージョン管理にJujutsuを使用し、コラボレーションにGitHubを使用しています。コントリビューションする際は:

1. **新しい作業を開始**: `jj new -m "Feature: description"` で新しい変更を作成
2. **変更を行う**: 必要に応じてファイルを編集
3. **頻繁にコミット**: `jj describe -m "明確なコミットメッセージ"` を使用して意味のあるコミットメッセージを追加
4. **リモートと同期**: `jj git fetch` で最新の変更を取得し、必要に応じてリベース
5. **GitHubにプッシュ**: `jj git push --change @-` を使用して変更をプッシュ
6. **変更を統合**: プッシュ前に `jj squash` を使用して関連する変更を統合

### 開発ワークフロー

```bash
# 新しい機能を開始
jj new -m "Feature: add new functionality"

# 変更を行い、頻繁にコミット
jj describe -m "Implement core logic"
jj describe -m "Add error handling"

# プッシュ前にリモートと同期
jj git fetch
jj rebase -o main@origin

# GitHubにプッシュ
jj git push --change @-
```

### GitHub同期

- **変更をプッシュ**: `jj git push --change @-` (現在の変更をプッシュ)
- **ブックマークをプッシュ**: `jj git push --bookmark <name>` (特定のブックマークをプッシュ)
- **更新を取得**: `jj git fetch` (リモートから取得)
- **同期ワークフロー**: `jj git fetch && jj rebase -o main@origin` (取得してリベース)

詳細なガイドラインとベストプラクティスについては、`.cursor/rules/jujutsu-policy.mdc` を参照してください。
