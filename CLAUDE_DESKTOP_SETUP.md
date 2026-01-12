# Claude Desktop Configuration Guide

## Step 1: Install Dependencies

First, make sure you have the required Python packages installed:

```bash
pip install -r requirements.txt
```

## Step 2: Find Your Python Executable Path

You need to find the full path to your Python executable. You can do this by:

1. Open PowerShell or Command Prompt
2. Run: `where python` or `where python3`
3. Or run: `python -c "import sys; print(sys.executable)"`

Common locations on Windows:
- `C:\Users\YourUsername\AppData\Local\Programs\Python\Python3XX\python.exe`
- `C:\Python3XX\python.exe`
- Or wherever you installed Python

## Step 3: Configure Claude Desktop

1. **Locate the configuration file:**
   - On Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Full path example: `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`

2. **Create or edit the file** with the following content:

```json
{
  "mcpServers": {
    "minyan-finder": {
      "command": "C:\\Users\\ezrar\\AppData\\Local\\Programs\\Python\\Python3XX\\python.exe",
      "args": [
        "C:\\Users\\ezrar\\mcp-server-deployment-ERosenbaum2\\server.py"
      ]
    }
  },
  "preferences": {
    "menuBarEnabled": true,
    "legacyQuickEntryEnabled": false
  }
}
```

**IMPORTANT:** Replace these paths with your actual paths:
- `"command"`: The full path to your Python executable (use double backslashes `\\` or forward slashes `/`)
- `"args"`: The full path to `server.py` in this project directory

**Example with your actual workspace:**
```json
{
  "mcpServers": {
    "minyan-finder": {
      "command": "C:\\Users\\ezrar\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": [
        "C:\\Users\\ezrar\\mcp-server-deployment-ERosenbaum2\\server.py"
      ]
    }
  },
  "preferences": {
    "menuBarEnabled": true,
    "legacyQuickEntryEnabled": false
  }
}
```

## Step 4: Restart Claude Desktop

After saving the configuration file, completely close and restart Claude Desktop for the changes to take effect.

## Step 5: Test the Integration

Once Claude Desktop restarts, you should be able to use the MCP tools:
- `health_check` - Check API health
- `get_nearby_broadcasts` - Find nearby minyan broadcasts
- `create_broadcast` - Create a new broadcast
- `update_broadcast` - Update an existing broadcast
- `delete_broadcast` - Delete a broadcast

## Troubleshooting

- **Python not found**: Make sure the path to `python.exe` is correct
- **Module not found**: Run `pip install -r requirements.txt` in your project directory
- **Server not appearing**: Check that the paths use double backslashes (`\\`) in JSON
- **Still not working**: Check Claude Desktop's logs or console for error messages

