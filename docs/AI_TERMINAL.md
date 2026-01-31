# AI Terminal for Revolution EDA

## Overview

The AI Terminal provides an interface to interact with AI agents (like Claude) to modify
design files through natural language commands. The AI agent can read, understand, and
modify JSON design files while ensuring all changes remain within the design library
boundaries.

## Features

- **Safe Modifications**: Automatic backup before any AI-driven changes
- **Undo Support**: Revert to previous version if changes are unsatisfactory
- **Library Boundary Enforcement**: AI can only access files within design libraries
- **JSON Validation**: Ensures all modifications produce valid JSON

## Usage

### Opening the AI Terminal

1. Open any design (schematic, symbol, or layout) in Revolution EDA
2. Go to **Tools → AI Terminal** menu
3. The AI Terminal window will appear

### Commands

- `help` - Display available commands
- `read` - Show current design JSON
- `setkey` - Set your Claude API key (required for AI features)
- `ai:<request>` - Send a request to the AI agent
- `undo` - Revert to backup and reload design
- `clear` - Clear terminal output

### Example Workflow

```
> setkey
[Enter your Claude API key in the dialog]

> read
[View current design JSON]

> ai:Add a 100fF capacitor named C1 between nodes VDD and GND

> undo
[If you want to revert the changes]
```

## AI Request Examples

- `ai:Add a resistor with value 1k between nodes A and B`
- `ai:Change the width of transistor M1 to 2um`
- `ai:Add a label "VDD" at position (100, 200)`
- `ai:Rename instance I1 to I_buffer`
- `ai:Move all components 50 units to the right`

## Setup

### Prerequisites

1. Python 3.12 or 3.13
2. Install the Anthropic package:
   ```bash
   pip install anthropic
   ```

3. Obtain a Claude API key from [Anthropic](https://www.anthropic.com/)

### Configuration

The AI agent is automatically configured with:

- Current design file path
- Library paths from the current design
- Restrictions to prevent modifications outside library boundaries

## Security & Safety

- **Backup System**: Every AI modification creates a backup (.json.bak)
- **Path Validation**: AI cannot access files outside design libraries
- **JSON Validation**: All modifications are validated before saving
- **Undo Support**: Easy rollback to previous version
- **API Key Security**: Keys are stored in memory only (not persisted)

## Limitations

- AI agent can only modify the current design file
- Changes are limited to valid JSON structure
- File references must be within library paths
- Requires active internet connection for AI API calls
- API usage may incur costs based on your Anthropic plan

## Troubleshooting

**"API key not set"**

- Use the `setkey` command to configure your Claude API key

**"anthropic package not installed"**

- Install with: `pip install anthropic`

**"Modified design contains invalid paths"**

- The AI tried to reference files outside library boundaries
- Try rephrasing your request to work within the current library

**Changes not appearing**

- The design should auto-reload after successful modifications
- If not, use **File → Update Design** menu

## Future Enhancements

- Support for multiple AI providers (OpenAI, local models)
- Persistent API key storage (encrypted)
- Multi-file modifications
- AI-assisted debugging and validation
- Design optimization suggestions
- Batch operations across multiple designs

## Technical Details

### Architecture

```
editorWindow
    ↓
aiTerminal (GUI)
    ↓
aiAgent (Backend)
    ↓
Claude API
```

### File Locations

- Terminal GUI: `revedaEditor/gui/aiTerminal.py`
- AI Agent Backend: `revedaEditor/backend/aiAgent.py`
- Integration: `revedaEditor/gui/editorWindow.py`

### Backup Files

Backups are created as `<design_file>.json.bak` in the same directory as the original file.
They are automatically deleted after successful undo operations.
