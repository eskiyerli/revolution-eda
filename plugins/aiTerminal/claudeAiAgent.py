#    Software: ai terminal for Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

"""AI Agent interface for design modifications."""

import json
import pathlib


class ClaudeAIAgent:
    """Base class for AI agent integration."""

    def __init__(self, design_file: pathlib.Path, library_paths: list[pathlib.Path]):
        self.design_file = design_file
        self.library_paths = library_paths
        self.api_key = None

    def set_api_key(self, key: str):
        """Set API key for AI service."""
        self.api_key = key

    def read_design(self) -> dict:
        """Read current design JSON."""
        with open(self.design_file, "r") as f:
            return json.load(f)

    def write_design(self, data: dict) -> bool:
        """Write modified design JSON."""
        try:
            with open(self.design_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error writing design: {e}")
            return False

    def validate_paths(self, data: dict) -> bool:
        """Ensure all file references are within library paths."""
        # Implement validation logic
        return True

    def process_request(self, user_request: str) -> tuple[bool, str]:
        """
        Process user request through AI agent.
        Returns (success, message)
        """
        if not self.api_key:
            return False, "API key not configured"

        # Read current design
        try:
            design_data = self.read_design()
        except Exception as e:
            return False, f"Failed to read design: {e}"

        # Here you would call the AI API (Claude, etc.)
        # For now, return a placeholder
        return (
            False,
            "AI integration not yet implemented. Configure API key and implement AI call.",
        )

    def read_library_files(self) -> dict:
        """Read all JSON files from library paths."""
        library_files = {}
        for lib_path in self.library_paths:
            if lib_path.exists():
                for json_file in lib_path.rglob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            library_files[str(json_file)] = json.load(f)
                    except Exception:
                        continue  # Skip invalid files
        return library_files

    def get_context(self) -> str:
        """Build context string for AI agent."""
        context = f"Design file: {self.design_file}\n"
        context += f"Library paths: {', '.join(str(p) for p in self.library_paths)}\n"
        context += "You can only modify files within the design libraries.\n"
        context += "All changes must be valid JSON format.\n"
        context += "When returning a response either return a valid JSON response or text only.\n"

        # Add library files context
        library_files = self.read_library_files()
        if library_files:
            context += "\nAvailable library files:\n"
            for file_path, file_data in library_files.items():
                context += f"File: {file_path}\n{json.dumps(file_data, indent=2)}\n\n"

        return context


class ClaudeAgentClaude(ClaudeAIAgent):
    """Claude AI agent implementation."""

    def __init__(self, design_file: pathlib.Path, library_paths: list[pathlib.Path]):
        super().__init__(design_file, library_paths)
        self.model = "claude-haiku-4-5-20251001"

    def process_request(self, user_request: str) -> tuple[bool, str]:
        """Process request using Claude API."""
        if not self.api_key:
            return False, "Claude API key not set. Use set_api_key() method."

        try:
            # Import anthropic only when needed
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            design_data = self.read_design()

            system_prompt = f"""{self.get_context()}
Current design JSON:
{json.dumps(design_data, indent=2)}

Instructions:
1. Read and understand the current design
2. Make the requested modifications
3. Return ONLY the modified JSON, no explanations
4. Ensure all changes are valid and within library paths
5. Do not use any markdown formatting in your JSON response.
"""

            message = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_request}],
            )

            response_text = message.content[0].text

            # Strip markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                if len(lines) > 2:
                    response_text = "\n".join(
                        lines[1:-1]
                    )  # Remove first and last lines

            # Try to parse response as JSON
            try:
                modified_data = json.loads(response_text)
                if self.validate_paths(modified_data):
                    if self.write_design(modified_data):
                        return True, "Design modified successfully"
                    else:
                        return False, "Failed to write modified design"
                else:
                    return False, "Modified design contains invalid paths"
            except json.JSONDecodeError:
                return False, f"AI response was not valid JSON:\n{response_text}"

        except ImportError:
            return (
                False,
                "anthropic package not installed. Install with: pip install anthropic",
            )
        except Exception as e:
            return False, f"Error processing request: {e}"
