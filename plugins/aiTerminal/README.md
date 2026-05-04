# aiTerminal Plugin for Revolution EDA

## Overview

The aiTerminal plugin provides an AI-powered terminal interface within Revolution EDA for modifying design JSON files using natural language commands. It integrates with various AI models (Claude, Gemini) to allow users to make changes to schematics, symbols, and layouts through conversational requests.

## Features

- **AI-Powered Design Modification**: Use natural language to request changes to your designs
- **Multiple AI Model Support**: Currently supports Claude and Gemini, with OpenAI planned
- **Secure API Key Management**: Encrypted storage of API keys
- **Backup and Undo**: Automatic backups before modifications with easy undo functionality
- **Integrated Terminal**: Seamlessly integrated into the Revolution EDA interface

## Installation

1. Ensure the aiTerminal plugin is in the `plugins/` directory of your Revolution EDA installation.
2. The plugin will be automatically discovered and loaded when Revolution EDA starts.

## Usage

### Setting Up API Keys

Before using the AI features, you need to set your API key:

1. Open the AI Terminal in your editor window (toggle via menu or shortcut)
2. Type `setkey` and press Enter
3. Enter your API key when prompted
4. The key will be encrypted and stored securely

### Basic Commands

- `help`: Display available commands
- `read`: Display the current design JSON
- `undo`: Revert the last AI modification
- `setkey`: Set or update the API key
- `ai:<request>`: Send a request to the AI agent

### Example Requests

- `ai:Add a 100fF capacitor between nodes A and B`
- `ai:Change the width of transistor M1 to 10um`
- `ai:Connect the output of inverter I1 to the input of NAND gate N1`

### Model Selection

You can switch between AI models using the dropdown in the terminal title bar:

- **Claude**: Anthropic's Claude model
- **Gemini**: Google's Gemini model
- **OpenAI**: (Not yet implemented)

## Architecture

The plugin consists of:

- `aiTerminal.py`: Main terminal UI and command processing
- `claudeAiAgent.py`: Claude AI agent implementation
- `geminiAiAgent.py`: Gemini AI agent implementation
- `config.json`: Plugin configuration

## Security

API keys are encrypted using Fernet symmetric encryption and stored in `~/.reveda/api_keys.enc`. The encryption key is stored separately in `~/.reveda/key.enc`.

## Dependencies

- PySide6
- cryptography
- anthropic (for Claude)
- google-generativeai (for Gemini)

## Contributing

Contributions are welcome. Please ensure all changes maintain backward compatibility and follow the existing code style.

## License

Mozilla Public License 2.0