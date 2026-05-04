#    Software: ai terminal for Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

"""Claude AI Agent interface for design modifications."""

import json
import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ClaudeAIAgent:
    """Base class for Claude AI agent integration."""

    # Revolution EDA JSON schema guidance for the AI
    REVEDA_SCHEMA_HINT = (
        "Revolution EDA design files are JSON arrays of shape/item objects. "
        "Each schematic item has a 'type' key (e.g. 'schInstance', 'schNet', 'schPin', "
        "'schText'). Instances have 'instanceName', 'libName', 'cellName', 'viewName', "
        "'loc' ([x,y]), 'angle', and 'labels' (list of label dicts with 'labelName' and "
        "'labelValue'). Nets have 'name', 'start' ([x,y]), 'end' ([x,y]). "
        "Layout items use types such as 'lRect', 'lPath', 'lPin', 'lLabel', 'lVia', "
        "'lInstance'. Connecting two terminals means adding a 'schNet' between their "
        "pin locations. Preserve all existing items unless explicitly asked to remove them."
    )

    def __init__(self, design_file: pathlib.Path, library_paths: list[pathlib.Path]):
        self.design_file = design_file
        self.library_paths = library_paths
        self.api_key = None

    def set_api_key(self, key: str):
        self.api_key = key

    def read_design(self) -> Dict[str, Any]:
        """Read current design JSON."""
        try:
            with open(self.design_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Design file not found: {self.design_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in design file: {e}")

    def write_design(self, data: Dict[str, Any]) -> bool:
        """Write modified design JSON, creating a timestamped backup first."""
        try:
            if not isinstance(data, (dict, list)):
                raise ValueError("Data must be a dict or list")

            if self.design_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.design_file.with_suffix(f".{timestamp}.bak")
                backup_file.write_text(
                    self.design_file.read_text(encoding="utf-8"), encoding="utf-8"
                )

            with open(self.design_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            logger.error("Error writing design: %s", e)
            return False

    def validate_paths(self, data: Dict[str, Any]) -> bool:
        """Ensure all explicit file references are within allowed library paths."""
        try:
            allowed = [lp.resolve() for lp in self.library_paths]
        except OSError as e:
            logger.error("Failed to resolve library paths: %s", e)
            return False

        def _check(obj) -> bool:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("lib", "library", "path", "file") and isinstance(value, str):
                        try:
                            candidate = pathlib.Path(value)
                            if candidate.is_absolute() or "/" in value or "\\" in value:
                                resolved = candidate.resolve()
                                if not any(
                                    str(resolved).startswith(str(lib)) for lib in allowed
                                ):
                                    logger.warning(
                                        "Path '%s' is outside allowed library paths", value
                                    )
                                    return False
                        except (OSError, ValueError) as e:
                            logger.error("Error resolving path '%s': %s", value, e)
                            return False
                    elif not _check(value):
                        return False
            elif isinstance(obj, list):
                return all(_check(item) for item in obj)
            return True

        try:
            return _check(data)
        except Exception as e:
            logger.error("Unexpected error during path validation: %s", e)
            return False

    def get_context(self, design_data: Optional[Dict[str, Any]] = None) -> str:
        """Build system context string for the AI model."""
        lines = [
            f"Design file: {self.design_file}",
            f"Library paths: {', '.join(str(p) for p in self.library_paths)}",
            "You may only modify items within the design file shown below.",
            "Return ONLY the complete modified JSON array — no explanations, no markdown, "
            "no code fences.",
            "If the user request requires no design change, reply with plain text only "
            "(no JSON).",
            self.REVEDA_SCHEMA_HINT,
        ]

        if design_data is not None:
            try:
                design_size = len(json.dumps(design_data))
                lines.append(f"Current design size: {design_size:,} characters")
                if design_size > 500_000:
                    lines.append(
                        "This is a large design — make only the minimal targeted changes "
                        "requested and preserve everything else exactly."
                    )
            except (TypeError, ValueError):
                pass

        return "\n".join(lines)

    def process_request(self, user_request: str) -> Tuple[bool, str]:
        """Process user request — must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process_request")


class ClaudeAgent(ClaudeAIAgent):
    """Claude AI agent implementation."""

    # Characters reserved for prompt overhead and response
    _DESIGN_CHAR_BUDGET = 700_000  # Claude's context is ~200K tokens ≈ ~800K chars

    def __init__(self, design_file: pathlib.Path, library_paths: list[pathlib.Path]):
        super().__init__(design_file, library_paths)
        self.model = "claude-haiku-4-5-20251001"

    def process_request(self, user_request: str) -> Tuple[bool, str]:
        """Process request using Claude API."""
        if not self.api_key:
            return False, "Claude API key not set. Use set_api_key() method."

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            design_data = self.read_design()
            design_json = json.dumps(design_data, indent=2)

            if len(design_json) > self._DESIGN_CHAR_BUDGET:
                return (
                    False,
                    f"Design is too large ({len(design_json):,} chars) for a single "
                    "request. Consider breaking the modification into smaller steps.",
                )

            system_prompt = (
                f"{self.get_context(design_data)}\n\n"
                f"Current design JSON:\n{design_json}\n\n"
                "Instructions:\n"
                "1. Read and understand the current design.\n"
                "2. Apply only the requested modifications.\n"
                "3. Return the COMPLETE modified JSON array — no partial output.\n"
                "4. Do NOT use markdown, code fences, or any formatting.\n"
                "5. Preserve the exact structure of unchanged items.\n"
                f"\nUser request: {user_request}"
            )

            with client.messages.stream(
                model=self.model,
                max_tokens=32_768,
                system=system_prompt,
                messages=[{"role": "user", "content": user_request}],
            ) as stream:
                message = stream.get_final_message()

            # Guard against empty or blocked responses
            if not message.content:
                return False, "Claude returned an empty response."

            # Check for truncation — end_turn is the only safe stop reason
            if message.stop_reason != "end_turn":
                return (
                    False,
                    f"Claude response incomplete. Stop reason: {message.stop_reason}",
                )

            response_text = message.content[0].text.strip()

            # Strip markdown code fences if the model ignored instructions
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                start = 1
                end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                response_text = "\n".join(lines[start:end]).strip()

            # Attempt to parse as JSON (design modification)
            try:
                modified_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Not JSON — treat as informational plain-text reply
                return True, response_text

            if not self.validate_paths(modified_data):
                return False, "Modified design contains paths outside allowed library paths."

            if self.write_design(modified_data):
                return True, "Design modified successfully."
            return False, "Failed to write modified design."

        except ImportError:
            return (
                False,
                "anthropic package not installed. Install with: pip install anthropic",
            )
        except (FileNotFoundError, ValueError) as e:
            return False, f"Design file error: {e}"
        except Exception as e:
            logger.exception("Unexpected error in ClaudeAgent.process_request")
            return False, f"Error processing request: {e}"


# Backward-compatible alias — aiTerminal.py instantiates ClaudeAgentClaude
ClaudeAgentClaude = ClaudeAgent
