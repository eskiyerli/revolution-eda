
#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

import json
import pathlib
import shutil
import os
from cryptography.fernet import Fernet
from PySide6.QtCore import Signal, QThreadPool
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit,
                               QPushButton, QHBoxLayout, QLabel, QInputDialog, QComboBox)
from PySide6.QtGui import (QTextCursor, QFont)
import revedaEditor.backend.claudeAiAgent as aia
import revedaEditor.backend.geminiAiAgent as gaia
from revedaEditor.backend.startThread import startThread


class aiTerminal(QWidget):
    """AI Agent Terminal for modifying design JSON files."""

    reloadRequested = Signal()

    def __init__(self, editorWindow, parent=None):
        super().__init__(parent)
        self.editorWindow = editorWindow
        self.backupFile = None
        self.aiAgent = None
        self.threadpool = QThreadPool()
        self.initUI()
        self.setupAIAgent()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Title bar with model selection
        titleLayout = QHBoxLayout()
        titleLayout.addWidget(QLabel("Revolution EDA AI Agent Terminal"))
        titleLayout.addStretch()
        titleLayout.addWidget(QLabel("Model:"))
        self.modelCombo = QComboBox()
        self.modelCombo.addItems(["Claude", "OpenAI", "Gemini"])
        self.modelCombo.currentTextChanged.connect(self.onModelChanged)
        titleLayout.addWidget(self.modelCombo)
        layout.addLayout(titleLayout)

        # Output display
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Monospace", 9))
        layout.addWidget(self.output)

        # Input line
        inputLayout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter AI command...")
        self.input.returnPressed.connect(self.processCommand)
        inputLayout.addWidget(self.input)

        self.sendBtn = QPushButton("Send")
        self.sendBtn.clicked.connect(self.processCommand)
        inputLayout.addWidget(self.sendBtn)

        layout.addLayout(inputLayout)

        # Control buttons
        btnLayout = QHBoxLayout()
        self.undoBtn = QPushButton("Undo Changes")
        self.undoBtn.clicked.connect(self.undoChanges)
        self.undoBtn.setEnabled(False)
        btnLayout.addWidget(self.undoBtn)

        self.clearBtn = QPushButton("Clear")
        self.clearBtn.clicked.connect(self.output.clear)
        btnLayout.addWidget(self.clearBtn)

        layout.addLayout(btnLayout)

        self.appendOutput(
            f"AI Terminal initialized for: {self.editorWindow.file}")
        self.appendOutput(
            "Available commands: read, undo, help, setkey, ai:<request>")

    def _get_config_dir(self):
        config_dir = pathlib.Path.home() / ".reveda"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _get_encryption_key(self):
        """Get or create encryption key."""
        key_file = self._get_config_dir() / "key.enc"
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            return key

    def _save_api_key(self, provider, key):
        """Save encrypted API key."""
        try:
            config_dir = self._get_config_dir()
            encryption_key = self._get_encryption_key()
            cipher = Fernet(encryption_key)

            # Load existing keys
            keys_file = config_dir / "api_keys.enc"
            keys = {}
            if keys_file.exists():
                try:
                    with open(keys_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted_data = cipher.decrypt(encrypted_data)
                    keys = json.loads(decrypted_data.decode())
                except Exception:
                    pass  # Start fresh if corrupted

            # Add new key
            keys[provider] = key

            # Encrypt and save
            json_data = json.dumps(keys).encode()
            encrypted_data = cipher.encrypt(json_data)
            with open(keys_file, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(keys_file, 0o600)  # Restrict permissions

        except Exception as e:
            self.appendOutput(f"Failed to save API key: {e}")

    def _load_api_key(self, provider):
        """Load and decrypt API key."""
        try:
            config_dir = self._get_config_dir()
            keys_file = config_dir / "api_keys.enc"

            if not keys_file.exists():
                return None

            encryption_key = self._get_encryption_key()
            cipher = Fernet(encryption_key)

            with open(keys_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher.decrypt(encrypted_data)
            keys = json.loads(decrypted_data.decode())
            return keys.get(provider)

        except Exception:
            return None  # Return None if decryption fails

    def appendOutput(self, text):
        self.output.append(text)
        self.output.moveCursor(QTextCursor.End)

    def setupAIAgent(self):
        """Initialize AI agent with library paths."""
        lib_paths = [pathlib.Path(self.editorWindow.libItem.libraryPath)]
        self.createAIAgent("Claude")

    def createAIAgent(self, model_name):
        """Create AI agent based on selected model."""
        lib_paths = [pathlib.Path(self.editorWindow.libItem.libraryPath)]

        if model_name == "Claude":
            self.aiAgent = aia.ClaudeAgentClaude(self.editorWindow.file, lib_paths)
            provider_key = "claude"
        elif model_name == "OpenAI":
            # TODO: Import and create OpenAI agent
            self.appendOutput("OpenAI backend not implemented yet")
            return
        elif model_name == "Gemini":
            self.aiAgent = gaia.GeminiAgent(self.editorWindow.file, lib_paths)
            provider_key = "gemini"
        else:
            self.appendOutput(f"Unknown model: {model_name}")
            return

        saved_key = self._load_api_key(provider_key)
        if saved_key:
            self.aiAgent.set_api_key(saved_key)
            self.appendOutput(f"Loaded saved {model_name} API key.")

    def onModelChanged(self, model_name):
        """Handle model selection change."""
        self.appendOutput(f"Switching to {model_name} model...")
        self.createAIAgent(model_name)

    def processCommand(self):
        cmd = self.input.text().strip()
        if not cmd:
            return

        self.appendOutput(f"\n> {cmd}")
        self.input.clear()

        if cmd == "help":
            self.showHelp()
        elif cmd == "read":
            self.readDesignFile()
        elif cmd == "undo":
            self.undoChanges()
        elif cmd == "setkey":
            self.setAPIKey()
        elif cmd.startswith("ai:"):
            request = cmd[3:].strip()
            if request:
                self.processAIRequest(request)
            else:
                self.appendOutput("Usage: ai:<your request>")
        else:
            self.appendOutput(f"Unknown command: {cmd}")

    def showHelp(self):
        help_text = """
Commands:
  read - Display current design JSON
  undo - Revert to backup and reload
  setkey - Set and save Claude API key
  ai:<request> - Send request to AI agent
  help - Show this help
  
Example:
  ai:Add a 100fF capacitor between nodes A and B
"""
        self.appendOutput(help_text)

    def setAPIKey(self):
        """Prompt user for API key."""
        current_model = self.modelCombo.currentText()
        provider_map = {"Claude": "claude", "OpenAI": "openai", "Gemini": "gemini"}
        provider_key = provider_map.get(current_model, "claude")

        key, ok = QInputDialog.getText(self, "API Key",
                                       f"Enter {current_model} API key:",
                                       QLineEdit.Password)
        if ok and key:
            if hasattr(self.aiAgent, 'set_api_key'):
                self.aiAgent.set_api_key(key)
            self._save_api_key(provider_key, key)
            self.appendOutput(f"{current_model} API key set and saved successfully")
        else:
            self.appendOutput("API key not set")

    def processAIRequest(self, request: str):
        """Process AI request."""
        if not self.aiAgent.api_key:
            self.appendOutput(
                "Error: API key not set. Use 'setkey' command first.")
            return

        # Create backup before modification
        if not self.backupDesign():
            return

        self.appendOutput("Processing AI request...")
        self.sendBtn.setEnabled(False)

        # Create worker thread
        worker = startThread(self.aiAgent.process_request, request)
        worker.signals.result.connect(self.onAIRequestComplete)
        worker.signals.error.connect(self.onAIRequestError)
        worker.signals.finished.connect(lambda: self.sendBtn.setEnabled(True))

        # Execute in thread pool
        self.threadpool.start(worker)

    def onAIRequestComplete(self, result):
        """Handle AI request completion."""
        success, message = result
        self.appendOutput(message)

        if success:
            self.appendOutput("Reloading design...")
            self.reloadRequested.emit()

    def onAIRequestError(self, error):
        """Handle AI request error."""
        error_type, error_args, error_str = error
        self.appendOutput(f"AI request failed: {error_str}")

    def readDesignFile(self):
        try:
            with open(self.editorWindow.file, 'r') as f:
                data = json.load(f)
            self.appendOutput(json.dumps(data, indent=2))
        except Exception as e:
            self.appendOutput(f"Error reading file: {e}")

    def backupDesign(self):
        """Create backup before AI modifications."""
        try:
            self.backupFile = self.editorWindow.file.with_suffix('.json.bak')
            shutil.copy2(self.editorWindow.file, self.backupFile)
            self.undoBtn.setEnabled(True)
            return True
        except Exception as e:
            self.appendOutput(f"Backup failed: {e}")
            return False

    def undoChanges(self):
        """Restore from backup and reload."""
        if not self.backupFile or not self.backupFile.exists():
            self.appendOutput("No backup available")
            return

        try:
            shutil.copy2(self.backupFile, self.editorWindow.file)
            self.appendOutput("Restored from backup")
            self.reloadRequested.emit()
            if self.backupFile.exists():
                self.backupFile.unlink()
            self.backupFile = None
            self.undoBtn.setEnabled(False)
        except Exception as e:
            self.appendOutput(f"Undo failed: {e}")
