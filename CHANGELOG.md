# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-08-17

### Added
- `alfred_list_workflows` — list and search installed Alfred workflows by name, bundle ID, or keyword
- `alfred_get_workflow` — deep inspection of workflow metadata, nodes, script code, connections, and files
- `alfred_create_workflow` — create new Alfred 5 workflows from templates (`keyword_script`, `script_filter`, `hotkey_trigger`, `empty`)
- `alfred_update_workflow_info` — update workflow metadata (name, description, bundle ID, README, version, disabled state)
- `alfred_update_script_node` — update script code or keyword on a target script node
- `alfred_edit_file` — create or overwrite files inside a workflow folder (scripts, modules, config assets)
- `alfred_delete_workflow` — safely move a workflow folder to macOS Trash
- `alfred_export_workflow` — package a workflow into a distributable `.alfredworkflow` file
- `alfred_run_trigger` — fire Alfred External Triggers via AppleScript
- Automated installer (`install.sh`) for Claude Desktop, Cursor, and Antigravity IDE
- `uvx` / zero-clone install support via `pyproject.toml` entry point
