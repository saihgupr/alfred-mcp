<h1>
  Alfred MCP Server
  <img src="assets/icon.png" width="80" align="right" />
</h1>

Alfred MCP Server connects AI assistants directly to macOS Alfred 5. It allows AI models to search, create, modify, execute, and package Alfred workflows using natural language.

---

## Features

- **List & Search Workflows**: Instantly scan installed Alfred workflows by name, bundle ID, or keyword.
- **Deep Inspection**: Read workflow configurations, node objects, script code, plist data, and included files.
- **Create Workflows**: Generate new Alfred 5 workflows from templates (`keyword_script`, `script_filter`, `hotkey_trigger`, `empty`) complete with UUIDs, nodes, and canvas positioning.
- **Edit & Update**: Modify metadata (name, description, bundle ID, README) and update script contents or keywords in real-time.
- **File Management**: Create or update embedded scripts, Python modules, shell files, or config assets directly inside workflow folders.
- **Trigger Actions**: Fire Alfred External Triggers programmatically via macOS AppleScript.
- **Export & Package**: Package workflows into standard `.alfredworkflow` files for distribution.
- **Safe Deletion**: Safely trash workflows by moving them to macOS Trash via `send2trash`.

---

## Prerequisites

- **macOS** 12.0 or later.
- **Alfred 5** with an active Powerpack license.
- **Python** 3.10 or higher.

---

## Quick Setup & Onboarding

Choose your preferred installation method:

### Option A: 1-Click Automated Setup (Recommended)

Run the automated installer script to create the environment, install dependencies, and automatically register `alfred-mcp` into **Claude Desktop**, **Cursor**, and **Antigravity IDE**:

```bash
git clone https://github.com/saihgupr/alfred-mcp.git
cd alfred-mcp
./install.sh
```

### Option B: Zero-Install Execution (`uvx` / `pipx`)

If you use [`uv`](https://github.com/astral-sh/uv), you can run `alfred-mcp` directly without cloning or managing virtual environments manually. Add the following entry to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "alfred": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/saihgupr/alfred-mcp.git", "alfred-mcp"]
    }
  }
}
```

### Option C: Manual Setup

1. Clone & setup environment:
   ```bash
   git clone https://github.com/saihgupr/alfred-mcp.git
   cd alfred-mcp
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run auto-installer command:
   ```bash
   python server.py --install
   ```
   *or manually add the block below to `~/Library/Application Support/Claude/claude_desktop_config.json`*:
   ```json
   {
     "mcpServers": {
       "alfred": {
         "command": "/path/to/alfred-mcp/.venv/bin/python",
         "args": ["/path/to/alfred-mcp/server.py"]
       }
     }
   }
   ```

---

## Available MCP Tools

| Tool Name | Description |
| :--- | :--- |
| `alfred_list_workflows` | List all installed Alfred workflows with optional search query filtering (matches name, bundle ID, keyword). |
| `alfred_get_workflow` | Retrieve comprehensive workflow details including metadata, node objects, script code, connections, and files. |
| `alfred_create_workflow` | Create a new Alfred 5 workflow with proper `info.plist` structure, objects, and canvas connections. |
| `alfred_update_workflow_info` | Update metadata settings in a workflow's `info.plist` (name, description, bundle ID, README, disabled state, version). |
| `alfred_update_script_node` | Update the script code or keyword of a target script node inside a workflow. |
| `alfred_edit_file` | Create or overwrite files (e.g. `main.py`, `script.sh`, `config.json`) inside a workflow folder. |
| `alfred_delete_workflow` | Safely delete an Alfred workflow by moving its folder to macOS Trash. |
| `alfred_export_workflow` | Package a workflow directory into an installable `.alfredworkflow` file in Downloads or a specified folder. |
| `alfred_run_trigger` | Trigger an Alfred workflow's External Trigger using macOS AppleScript (`osascript`). |

---

## Troubleshooting & Debugging

If you encounter any issues while using `alfred-mcp`:

### 1. Log Locations
- **Claude Desktop Logs**: Check `~/Library/Logs/Claude/mcp.log` and `~/Library/Logs/Claude/mcp-server-alfred.log` for execution errors.
- **Antigravity IDE Logs**: Inspect `~/.gemini/antigravity-ide/mcp_config.json` and agent session logs.
- **Cursor Logs**: Open the `Output` panel in Cursor and select `MCP Server Log`.

### 2. macOS Automation Permissions
- `alfred_run_trigger` uses AppleScript (`osascript`) to talk to Alfred 5.
- Ensure your MCP client (Antigravity IDE / Claude Desktop / Cursor / Terminal) has permission under:  
  **System Settings > Privacy & Security > Automation > [Your Client] > Alfred 5**.

### 3. Alfred Preferences Sync Folder
- `alfred-mcp` automatically scans default locations (`~/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows`, Dropbox, and iCloud Sync paths).
- If your workflows are stored in a custom folder, verify that Alfred 5 preferences plist (`com.runningwithcrayons.Alfred-Preferences-3.plist`) points to your current sync folder.

### 4. Interactive MCP Inspector
Test server tools locally with the MCP Inspector tool:
```bash
npx @modelcontextprotocol/inspector .venv/bin/python server.py
```

## Contributing

Contributions are welcome! Please submit all Pull Requests to the **develop** branch.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes and push to your fork
4. Open a Pull Request to **develop**

---

## Support & Feedback

If you encounter any issues, bugs, or have feature requests, please [open an issue on GitHub](https://github.com/saihgupr/alfred-mcp/issues).

Alfred MCP Server is open-source and free. If you find it useful, consider giving it a star ⭐ or making a donation to support development!

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/saihgupr)


