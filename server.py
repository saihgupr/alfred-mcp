#!/usr/bin/env python3
import os
import sys
import glob
import uuid
import json
import shutil
import zipfile
import plistlib
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from send2trash import send2trash
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP(
    "alfred",
    instructions="MCP Server for creating, listing, inspecting, editing, deleting, and triggering macOS Alfred 5 Workflows."
)

def get_workflows_dir() -> str:
    """Find the active Alfred 5 workflows directory on macOS."""
    candidates = [
        os.path.expanduser("~/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows"),
        os.path.expanduser("~/Dropbox/Alfred/Alfred.alfredpreferences/workflows"),
        os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/Alfred/Alfred.alfredpreferences/workflows"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    
    # Check custom sync folder in Alfred prefs if existing
    prefs_json = os.path.expanduser("~/Library/Preferences/com.runningwithcrayons.Alfred-Preferences-3.plist")
    if os.path.exists(prefs_json):
        try:
            with open(prefs_json, "rb") as f:
                p = plistlib.load(f)
                sync_folder = p.get("current")
                if sync_folder:
                    sync_path = os.path.expanduser(os.path.join(sync_folder, "Alfred.alfredpreferences/workflows"))
                    if os.path.exists(sync_path):
                        return sync_path
        except Exception:
            pass
            
    # Default fallback
    default_dir = os.path.expanduser("~/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows")
    os.makedirs(default_dir, exist_ok=True)
    return default_dir

def resolve_workflow_path(identifier: str) -> Optional[str]:
    """Find workflow directory by folder name (user.workflow.UUID), bundle ID, or workflow name."""
    wf_dir = get_workflows_dir()
    
    # Direct folder match
    if identifier.startswith("user.workflow."):
        full_path = os.path.join(wf_dir, identifier)
        if os.path.exists(full_path):
            return full_path
            
    folders = glob.glob(os.path.join(wf_dir, "user.workflow.*"))
    
    # Match by exact folder basename
    for f in folders:
        if os.path.basename(f) == identifier:
            return f
            
    # Match by bundleid or name
    identifier_lower = identifier.lower()
    for f in folders:
        info_plist = os.path.join(f, "info.plist")
        if os.path.exists(info_plist):
            try:
                with open(info_plist, "rb") as fp:
                    p = plistlib.load(fp)
                    bid = p.get("bundleid", "")
                    name = p.get("name", "")
                    if bid and bid.lower() == identifier_lower:
                        return f
                    if name and name.lower() == identifier_lower:
                        return f
            except Exception:
                continue
                
    # Partial match by name
    for f in folders:
        info_plist = os.path.join(f, "info.plist")
        if os.path.exists(info_plist):
            try:
                with open(info_plist, "rb") as fp:
                    p = plistlib.load(fp)
                    name = p.get("name", "")
                    if name and identifier_lower in name.lower():
                        return f
            except Exception:
                continue
                
    return None

def extract_keywords_from_objects(objects: List[Dict[str, Any]]) -> List[str]:
    """Extract input keywords from workflow objects list."""
    keywords = []
    for obj in objects:
        config = obj.get("config", {})
        kw = config.get("keyword") or config.get("scriptfilterkeyword")
        if kw and kw not in keywords:
            keywords.append(str(kw))
    return keywords

@mcp.tool()
def alfred_list_workflows(query: str = "") -> str:
    """List all installed Alfred workflows with options to search by name, bundle ID, or keyword.
    
    Args:
        query: Optional search filter (matches against name, bundle ID, keywords, description).
    """
    wf_dir = get_workflows_dir()
    folders = sorted(glob.glob(os.path.join(wf_dir, "user.workflow.*")))
    
    results = []
    q = query.strip().lower()
    
    for f in folders:
        info_path = os.path.join(f, "info.plist")
        if not os.path.exists(info_path):
            continue
            
        try:
            with open(info_path, "rb") as fp:
                plist = plistlib.load(fp)
        except Exception as e:
            continue
            
        folder_id = os.path.basename(f)
        name = plist.get("name", "Untitled")
        bundleid = plist.get("bundleid", "")
        description = plist.get("description", "")
        createdby = plist.get("createdby", "")
        version = str(plist.get("version", ""))
        disabled = bool(plist.get("disabled", False))
        keywords = extract_keywords_from_objects(plist.get("objects", []))
        
        # Apply search filter if query is provided
        if q:
            match = (
                q in name.lower()
                or q in bundleid.lower()
                or q in description.lower()
                or q in folder_id.lower()
                or any(q in kw.lower() for kw in keywords)
            )
            if not match:
                continue
                
        results.append({
            "id": folder_id,
            "name": name,
            "bundleid": bundleid,
            "keywords": keywords,
            "description": description,
            "createdby": createdby,
            "version": version,
            "disabled": disabled,
            "folder_path": f
        })
        
    return json.dumps({
        "total": len(results),
        "workflows_directory": wf_dir,
        "workflows": results
    }, indent=2)

@mcp.tool()
def alfred_get_workflow(identifier: str) -> str:
    """Get comprehensive details of an Alfred workflow including metadata, object nodes, script code, connections, and files.
    
    Args:
        identifier: Folder name (user.workflow.UUID), bundle ID, or workflow name.
    """
    wf_path = resolve_workflow_path(identifier)
    if not wf_path:
        return json.dumps({"error": f"Workflow '{identifier}' not found."})
        
    info_path = os.path.join(wf_path, "info.plist")
    with open(info_path, "rb") as fp:
        plist = plistlib.load(fp)
        
    folder_id = os.path.basename(wf_path)
    
    # Process objects for readable summary
    objects_summary = []
    for obj in plist.get("objects", []):
        obj_type = obj.get("type", "unknown")
        uid = obj.get("uid", "")
        config = obj.get("config", {})
        
        node_info = {
            "uid": uid,
            "type": obj_type,
            "version": obj.get("version", 1),
        }
        
        # Extract title/keyword/script snippet depending on object type
        if "keyword" in config:
            node_info["keyword"] = config.get("keyword")
        if "title" in config or "scriptfiltertitle" in config:
            node_info["title"] = config.get("title") or config.get("scriptfiltertitle")
        if "script" in config:
            script_text = config.get("script", "")
            node_info["script_preview"] = script_text[:200] + ("..." if len(script_text) > 200 else "")
            node_info["script_full"] = script_text
            node_info["script_type"] = config.get("type", 0)  # 0=/bin/bash, 5=/bin/zsh, etc.
            
        objects_summary.append(node_info)
        
    # List files in workflow directory
    dir_files = []
    for root, _, filenames in os.walk(wf_path):
        rel_root = os.path.relpath(root, wf_path)
        for fn in filenames:
            rel_path = fn if rel_root == "." else os.path.join(rel_root, fn)
            dir_files.append(rel_path)
            
    summary = {
        "id": folder_id,
        "name": plist.get("name", ""),
        "bundleid": plist.get("bundleid", ""),
        "createdby": plist.get("createdby", ""),
        "description": plist.get("description", ""),
        "version": str(plist.get("version", "")),
        "disabled": bool(plist.get("disabled", False)),
        "readme": plist.get("readme", ""),
        "variables": plist.get("variables", {}),
        "folder_path": wf_path,
        "objects_count": len(objects_summary),
        "objects": objects_summary,
        "connections": plist.get("connections", {}),
        "files": sorted(dir_files)
    }
    
    return json.dumps(summary, indent=2)

@mcp.tool()
def alfred_create_workflow(
    name: str,
    description: str = "",
    bundleid: str = "",
    createdby: str = "",
    category: str = "Tools",
    template: str = "keyword_script",
    keyword: str = "mykw",
    script: str = 'echo "Hello from Alfred MCP!"',
    script_type: str = "/bin/zsh"
) -> str:
    """Create a new Alfred 5 workflow with proper info.plist formatting, objects, and connections.
    
    Args:
        name: Name of the workflow.
        description: Description of what the workflow does.
        bundleid: Reverse domain bundle ID (e.g. com.user.myworkflow).
        createdby: Author name.
        category: Workflow category (e.g. Tools, Productivity, Uncategorised).
        template: Template design ('keyword_script', 'script_filter', 'hotkey_trigger', 'empty').
        keyword: Trigger keyword for the workflow input node.
        script: Code/script to execute.
        script_type: Script interpreter (e.g. /bin/zsh, python3, /bin/bash, applescript).
    """
    wf_dir = get_workflows_dir()
    wf_uuid = str(uuid.uuid4()).upper()
    folder_name = f"user.workflow.{wf_uuid}"
    target_dir = os.path.join(wf_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Map script_type to Alfred's internal type integer
    # 0 = /bin/bash, 1 = /usr/bin/php, 2 = /usr/bin/python, 3 = /usr/bin/ruby, 4 = /usr/bin/perl, 5 = /bin/zsh, 8 = external script
    type_map = {
        "/bin/bash": 0,
        "bash": 0,
        "/bin/zsh": 5,
        "zsh": 5,
        "python": 2,
        "python3": 5, # run zsh with python3 or external script
        "applescript": 6
    }
    script_type_int = type_map.get(script_type.lower(), 5)
    
    if script_type in ["python3", "python"] and not script.startswith("#!"):
        if script_type == "python3":
            script = f"python3 -c '{script}'" if "\n" not in script else script
            
    objects = []
    connections = {}
    uidata = {}
    
    if template == "keyword_script":
        kw_uid = str(uuid.uuid4()).upper()
        script_uid = str(uuid.uuid4()).upper()
        notif_uid = str(uuid.uuid4()).upper()
        
        # Keyword Input Object
        objects.append({
            "config": {
                "argumenttype": 1, # optional argument
                "keyword": keyword,
                "subtext": description or "Run script",
                "text": name,
                "withspace": True
            },
            "type": "alfred.workflow.input.keyword",
            "uid": kw_uid,
            "version": 1
        })
        
        # Run Script Action Object
        objects.append({
            "config": {
                "concurrently": False,
                "escaping": 102,
                "script": script,
                "scriptargtype": 1, # pass as {query}
                "scriptfile": "",
                "type": script_type_int
            },
            "type": "alfred.workflow.action.script",
            "uid": script_uid,
            "version": 2
        })
        
        # Notification Output Object
        objects.append({
            "config": {
                "lastpathcomponent": False,
                "onlyshowifquerypopulated": False,
                "removeextension": False,
                "text": "{query}",
                "title": name
            },
            "type": "alfred.workflow.output.notification",
            "uid": notif_uid,
            "version": 1
        })
        
        # Connect Keyword -> Script -> Notification
        connections[kw_uid] = [{
            "destinationuid": script_uid,
            "modifiers": 0,
            "modifiersubtext": "",
            "vitoclose": False
        }]
        connections[script_uid] = [{
            "destinationuid": notif_uid,
            "modifiers": 0,
            "modifiersubtext": "",
            "vitoclose": False
        }]
        
        # Canvas coordinates layout
        uidata[kw_uid] = {"xpos": 50, "ypos": 50}
        uidata[script_uid] = {"xpos": 250, "ypos": 50}
        uidata[notif_uid] = {"xpos": 450, "ypos": 50}
        
    elif template == "script_filter":
        sf_uid = str(uuid.uuid4()).upper()
        objects.append({
            "config": {
                "alfredfiltersresults": False,
                "alfredfiltersresultsmatchmode": 0,
                "argumenttreatemptyqueryasnil": True,
                "argumenttrimmode": 0,
                "argumenttype": 1,
                "escaping": 102,
                "keyword": keyword,
                "queuedelaycustom": 3,
                "queuedelayimmediatelyinitially": True,
                "queuedelaymode": 0,
                "queuemode": 1,
                "runmodemode": 0,
                "script": script,
                "scriptargtype": 1,
                "scriptfile": "",
                "subtext": description or "Script Filter",
                "title": name,
                "type": script_type_int,
                "withspace": True
            },
            "type": "alfred.workflow.input.scriptfilter",
            "uid": sf_uid,
            "version": 3
        })
        uidata[sf_uid] = {"xpos": 50, "ypos": 50}
        
    plist_data = {
        "bundleid": bundleid,
        "category": category,
        "connections": connections,
        "createdby": createdby,
        "description": description,
        "disabled": False,
        "name": name,
        "objects": objects,
        "readme": f"Created via Alfred MCP Server on {name}",
        "uidata": uidata,
        "variablesdontexport": [],
        "version": "1.0.0"
    }
    
    info_plist_path = os.path.join(target_dir, "info.plist")
    with open(info_plist_path, "wb") as fp:
        plistlib.dump(plist_data, fp)
        
    return json.dumps({
        "status": "success",
        "message": f"Successfully created workflow '{name}'",
        "id": folder_name,
        "folder_path": target_dir,
        "info_plist": info_plist_path
    }, indent=2)

@mcp.tool()
def alfred_update_workflow_info(
    identifier: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    bundleid: Optional[str] = None,
    disabled: Optional[bool] = None,
    readme: Optional[str] = None,
    version: Optional[str] = None
) -> str:
    """Update metadata settings in an Alfred workflow's info.plist.
    
    Args:
        identifier: Workflow folder ID (user.workflow.UUID), bundle ID, or name.
        name: New workflow name.
        description: New description.
        bundleid: New bundle ID.
        disabled: True to disable workflow, False to enable.
        readme: Markdown README documentation.
        version: Version string (e.g. 1.1.0).
    """
    wf_path = resolve_workflow_path(identifier)
    if not wf_path:
        return json.dumps({"error": f"Workflow '{identifier}' not found."})
        
    info_path = os.path.join(wf_path, "info.plist")
    with open(info_path, "rb") as fp:
        plist = plistlib.load(fp)
        
    updated_fields = []
    if name is not None:
        plist["name"] = name
        updated_fields.append("name")
    if description is not None:
        plist["description"] = description
        updated_fields.append("description")
    if bundleid is not None:
        plist["bundleid"] = bundleid
        updated_fields.append("bundleid")
    if disabled is not None:
        plist["disabled"] = disabled
        updated_fields.append("disabled")
    if readme is not None:
        plist["readme"] = readme
        updated_fields.append("readme")
    if version is not None:
        plist["version"] = version
        updated_fields.append("version")
        
    with open(info_path, "wb") as fp:
        plistlib.dump(plist, fp)
        
    return json.dumps({
        "status": "success",
        "message": f"Updated workflow {os.path.basename(wf_path)}",
        "updated_fields": updated_fields
    }, indent=2)

@mcp.tool()
def alfred_update_script_node(
    identifier: str,
    script: str,
    object_uid: Optional[str] = None,
    keyword: Optional[str] = None
) -> str:
    """Update the script code or keyword of a script node (Run Script / Script Filter) inside an Alfred workflow.
    
    Args:
        identifier: Workflow folder ID, bundle ID, or name.
        script: New script source code.
        object_uid: Optional target node UID. If omitted, updates the first script object found.
        keyword: Optional new keyword for the node.
    """
    wf_path = resolve_workflow_path(identifier)
    if not wf_path:
        return json.dumps({"error": f"Workflow '{identifier}' not found."})
        
    info_path = os.path.join(wf_path, "info.plist")
    with open(info_path, "rb") as fp:
        plist = plistlib.load(fp)
        
    target_obj = None
    for obj in plist.get("objects", []):
        uid = obj.get("uid", "")
        obj_type = obj.get("type", "")
        if object_uid:
            if uid == object_uid:
                target_obj = obj
                break
        else:
            if "script" in obj_type or "script" in obj.get("config", {}):
                target_obj = obj
                break
                
    if not target_obj:
        return json.dumps({"error": "No matching script node object found in workflow."})
        
    config = target_obj.get("config", {})
    config["script"] = script
    if keyword is not None:
        if "keyword" in config:
            config["keyword"] = keyword
        elif "scriptfilterkeyword" in config:
            config["scriptfilterkeyword"] = keyword
            
    target_obj["config"] = config
    
    with open(info_path, "wb") as fp:
        plistlib.dump(plist, fp)
        
    return json.dumps({
        "status": "success",
        "message": f"Updated script object {target_obj.get('uid')} in workflow '{plist.get('name')}'",
        "object_uid": target_obj.get("uid")
    }, indent=2)

@mcp.tool()
def alfred_edit_file(
    identifier: str,
    filename: str,
    content: str
) -> str:
    """Create or overwrite a file (script file, python module, icon, config) inside an Alfred workflow folder.
    
    Args:
        identifier: Workflow folder ID, bundle ID, or name.
        filename: Relative filename inside the workflow folder (e.g. main.py, helper.sh).
        content: Text content of the file.
    """
    wf_path = resolve_workflow_path(identifier)
    if not wf_path:
        return json.dumps({"error": f"Workflow '{identifier}' not found."})
        
    file_path = os.path.join(wf_path, filename)
    
    # Ensure nested subdirectories if specified
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # Make executable if it's a script file
    if filename.endswith((".sh", ".py", ".rb", ".pl", ".zsh", ".bash")):
        os.chmod(file_path, 0o755)
        
    return json.dumps({
        "status": "success",
        "message": f"File '{filename}' saved in workflow folder.",
        "file_path": file_path
    }, indent=2)

@mcp.tool()
def alfred_delete_workflow(
    identifier: str,
    confirm: bool = True
) -> str:
    """Safely delete an Alfred workflow by moving its directory to macOS Trash.
    
    Args:
        identifier: Workflow folder ID (user.workflow.UUID), bundle ID, or name.
        confirm: Must be set to True to confirm deletion.
    """
    if not confirm:
        return json.dumps({"error": "Set confirm=True to move workflow to macOS Trash."})
        
    wf_path = resolve_workflow_path(identifier)
    if not wf_path:
        return json.dumps({"error": f"Workflow '{identifier}' not found."})
        
    folder_name = os.path.basename(wf_path)
    
    try:
        send2trash(wf_path)
        return json.dumps({
            "status": "success",
            "message": f"Moved workflow directory '{folder_name}' to macOS Trash.",
            "trashed_path": wf_path
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to trash workflow: {str(e)}"})

@mcp.tool()
def alfred_export_workflow(
    identifier: str,
    output_dir: Optional[str] = None
) -> str:
    """Package an Alfred workflow directory into an installable .alfredworkflow file.
    
    Args:
        identifier: Workflow folder ID, bundle ID, or name.
        output_dir: Target output folder path. Defaults to user Downloads directory.
    """
    wf_path = resolve_workflow_path(identifier)
    if not wf_path:
        return json.dumps({"error": f"Workflow '{identifier}' not found."})
        
    info_path = os.path.join(wf_path, "info.plist")
    with open(info_path, "rb") as fp:
        plist = plistlib.load(fp)
        
    wf_name = plist.get("name", "workflow").replace(" ", "_")
    output_dir = output_dir or os.path.expanduser("~/Downloads")
    os.makedirs(output_dir, exist_ok=True)
    
    export_path = os.path.join(output_dir, f"{wf_name}.alfredworkflow")
    
    with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(wf_path):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_file = os.path.relpath(abs_file, wf_path)
                zipf.write(abs_file, rel_file)
                
    return json.dumps({
        "status": "success",
        "message": f"Exported workflow to '{export_path}'",
        "file_path": export_path
    }, indent=2)

@mcp.tool()
def alfred_run_trigger(
    bundleid: str,
    trigger_id: str,
    argument: str = ""
) -> str:
    """Trigger an Alfred workflow's External Trigger using macOS AppleScript.
    
    Args:
        bundleid: Workflow bundle ID (e.g. com.user.myworkflow).
        trigger_id: External trigger ID defined in the workflow.
        argument: Optional argument string to pass to the trigger.
    """
    arg_escaped = argument.replace('"', '\\"')
    applescript = (
        f'tell application id "com.runningwithcrayons.Alfred" to '
        f'run trigger "{trigger_id}" in workflow "{bundleid}" with argument "{arg_escaped}"'
    )
    
    try:
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=True)
        return json.dumps({
            "status": "success",
            "message": f"Triggered '{trigger_id}' in workflow '{bundleid}'.",
            "output": res.stdout.strip()
        }, indent=2)
    except subprocess.CalledProcessError as e:
        return json.dumps({
            "error": f"Failed to execute AppleScript trigger: {e.stderr.strip()}"
        })

def install_mcp_config() -> None:
    """Automatically register alfred-mcp into Claude Desktop and Cursor config files."""
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    
    server_entry = {
        "command": python_path,
        "args": [script_path]
    }
    
    config_paths = [
        ("Antigravity IDE", os.path.expanduser("~/.gemini/antigravity-ide/mcp_config.json")),
        ("Antigravity Config", os.path.expanduser("~/.gemini/config/mcp_config.json")),
        ("Claude Desktop", os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")),
        ("Cursor", os.path.expanduser("~/.cursor/mcp.json")),
        ("Cursor Global", os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/mcp.json")),
    ]
    
    updated_count = 0
    print("🚀 Running alfred-mcp auto-installer...")
    
    for client_name, path in config_paths:
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name) and not os.path.exists(path):
            continue
            
        try:
            config = {}
            if os.path.exists(path):
                # Create backup
                backup_path = f"{path}.bak"
                shutil.copy2(path, backup_path)
                
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                os.makedirs(dir_name, exist_ok=True)
                
            if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
                config["mcpServers"] = {}
                
            config["mcpServers"]["alfred"] = server_entry
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
                
            print(f"✅ Registered alfred-mcp in {client_name} ({path})")
            updated_count += 1
        except Exception as e:
            print(f"⚠️ Could not update {client_name} config ({path}): {e}")
            
    if updated_count == 0:
        print("\nℹ️ No default MCP client paths found automatically.")
        print("Add the following block to your MCP client config manually:")
        print(json.dumps({"mcpServers": {"alfred": server_entry}}, indent=2))
    else:
        print("\n✨ Auto-installation complete! Restart your MCP client (Antigravity IDE / Claude Desktop / Cursor) to start using alfred-mcp.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["--install", "install"]:
        install_mcp_config()
    else:
        mcp.run()

if __name__ == "__main__":
    main()

