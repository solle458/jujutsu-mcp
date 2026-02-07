# Jujutsu MCP Server

MCP (Model Context Protocol) server for Jujutsu (jj) version control system. This server provides AI agents with structured access to Jujutsu's powerful version control capabilities through a set of well-defined tools.

## Features

- **Structured Revision Access**: Get revision logs and details as JSON structures
- **Smart Operations**: Perform rebases, squashes, and other operations using revsets
- **Conflict Detection**: Identify and analyze conflicts programmatically
- **Safe Undo**: Undo operations with full operation history tracking
- **Status Monitoring**: Get current repository status including conflicts and uncommitted changes

## Installation

### Prerequisites

- Python 3.11 or higher
- [Jujutsu](https://github.com/martinvonz/jj) (jj) installed and available in PATH
- [Nix](https://nixos.org/) (optional, for reproducible development environment)
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### Using Nix (Recommended)

1. Enter the development shell:
   ```bash
   nix develop
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

### Manual Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

## Usage

### Running the MCP Server

```bash
python -m jujutsu_mcp
```

Or using uv:

```bash
uv run python -m jujutsu_mcp
```

### MCP Tools

The server provides the following tools:

#### `get_log`
Get the revision log as a structured graph.

**Parameters:**
- `limit` (optional): Maximum number of revisions to return

**Returns:** Revision graph with revisions and current revision

#### `describe_revision`
Get detailed information about a specific revision.

**Parameters:**
- `revision_id`: The revision ID (can be a revset like `@`, `@-`, `main`)

**Returns:** Revision information including description, author, parents, and conflict status

#### `smart_rebase`
Perform a rebase operation using revsets.

**Parameters:**
- `source`: Source revision (revset)
- `destination`: Destination revision (revset)

**Returns:** Success message

#### `undo_last_op`
Undo the last operation safely.

**Returns:** Information about the undone operation

#### `new_change`
Create a new change (equivalent to `jj new`).

**Parameters:**
- `parent` (optional): Parent revision (revset). Defaults to current working copy.

**Returns:** New revision ID

#### `squash_changes`
Squash changes from one revision into another.

**Parameters:**
- `revision`: Revision to squash (revset)
- `into`: Target revision (revset)

**Returns:** Success message

#### `get_status`
Get the current repository status.

**Returns:** Current revision, uncommitted changes status, and conflicts

#### `resolve_conflicts`
Detect and analyze conflicts in a revision.

**Parameters:**
- `revision` (optional): Revision to check (revset, defaults to `@`)

**Returns:** List of conflict information

## Configuration

### Cursor MCP Server Setup (Automatic Startup)

To use this MCP server in Cursor with automatic startup, you need to configure it in Cursor's settings.

#### Option 1: Project-Level Configuration (Recommended)

Create a file at `~/.cursor/mcp.json` (or in your project root) with the following content:

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

**Important**: 
- Replace `/path/to/jujutsu-mcp` with the actual absolute path to this project directory.
- Make sure dependencies are installed by running `uv sync` in the jujutsu-mcp directory first.
- If `.venv` doesn't exist, run `uv sync` to create it and install dependencies.

**Alternative using `uv run`** (if the above doesn't work):

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
        "PYTHONPATH": "/path/to/jujutsu-mcp/src"
      }
    }
  }
}
```

#### Option 2: Global Configuration

For macOS, edit or create:
```
~/Library/Application Support/Code/User/globalStorage/tencent-cloud.coding-copilot/settings/Craft_mcp_settings.json
```

For Windows:
```
%APPDATA%\Code\User\globalStorage\tencent-cloud.coding-copilot\settings\Craft_mcp_settings.json
```

For Linux:
```
~/.config/Code/User/globalStorage/tencent-cloud.coding-copilot/settings/Craft_mcp_settings.json
```

Add the same configuration as shown in Option 1.

#### Using Nix Environment

If you're using Nix, you can configure it to use the Nix environment:

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

**Note**: Once configured, Cursor will automatically start the MCP server when it launches. You don't need to manually start it each time.

### Git Authentication Setup

For detailed instructions on setting up Git authentication for GitHub push operations, see [Git Authentication Setup Guide](docs/GIT_AUTHENTICATION_SETUP.md).

The guide covers:
- SSH key authentication (recommended)
- Personal Access Token (PAT) setup for HTTPS
- Troubleshooting authentication issues
- Best practices for secure authentication

### Cursor Rules

The project includes Cursor Rules (`.cursor/rules/jujutsu-policy.mdc`) that guide AI agents on best practices when working with Jujutsu:

- Always use `jj` commands instead of `git` directly
- Create isolated work units with `jj new`
- Commit frequently with meaningful descriptions
- Understand revision graphs before making changes
- Use `jj evolog` to understand conflict history

## Development

### Project Structure

```
jujutsu-mcp/
├── flake.nix                 # Nix environment definition
├── flake.lock                # Nix lock file
├── pyproject.toml            # Python dependencies
├── uv.lock                   # uv lock file
├── src/
│   └── jujutsu_mcp/
│       ├── __init__.py
│       ├── __main__.py       # Entry point
│       ├── server.py         # MCP server implementation
│       ├── jj_commands.py    # jj command execution logic
│       └── models.py          # Data models
├── tests/                    # Test files
└── .cursor/
    └── rules/
        └── jujutsu-policy.mdc # Cursor Rules
```

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run ruff check .
uv run ruff format .
```

## Architecture

The project follows a 4-layer architecture:

1. **Infrastructure Layer (Nix)**: Reproducible development environment
2. **Logic Layer (MCP Server)**: Structured JSON access to jj commands
3. **Policy Layer (.mdc Rules)**: Agent behavior guidelines
4. **Execution Layer**: Advanced workflows (conflict resolution, time travel)

## License

Apache License 2.0

## Contributing

This project uses Jujutsu for version control and GitHub for collaboration. When contributing:

1. **Start new work**: Create a new change with `jj new -m "Feature: description"`
2. **Make your changes**: Edit files as needed
3. **Commit frequently**: Use `jj describe -m "Clear commit message"` to add meaningful commit messages
4. **Sync with remote**: Fetch latest changes with `jj git fetch` and rebase if needed
5. **Push to GitHub**: Use `jj git push --change @-` to push your changes
6. **Integrate changes**: Use `jj squash` to integrate related changes before pushing

### Development Workflow

```bash
# Start a new feature
jj new -m "Feature: add new functionality"

# Make changes and commit frequently
jj describe -m "Implement core logic"
jj describe -m "Add error handling"

# Sync with remote before pushing
jj git fetch
jj rebase -o main@origin

# Push to GitHub
jj git push --change @-
```

### GitHub Synchronization

- **Push changes**: `jj git push --change @-` (pushes current change)
- **Push bookmark**: `jj git push --bookmark <name>` (pushes specific bookmark)
- **Fetch updates**: `jj git fetch` (fetches from remote)
- **Sync workflow**: `jj git fetch && jj rebase -o main@origin` (fetch and rebase)

See `.cursor/rules/jujutsu-policy.mdc` for detailed guidelines and best practices.
