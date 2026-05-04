#
#    Software: ai terminal for Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

"""Mistral AI Agent interface for design modifications."""

import json
import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MistralAIAgent:
    """Base class for Mistral AI agent integration."""

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
        allowed = [lp.resolve() for lp in self.library_paths]

        def _check(obj) -> bool:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("lib", "library", "path", "file") and isinstance(value, str):
                        candidate = pathlib.Path(value)
                        if candidate.is_absolute() or "/" in value or "\\" in value:
                            resolved = candidate.resolve()
                            if not any(
                                str(resolved).startswith(str(lib)) for lib in allowed
                            ):
                                return False
                    elif not _check(value):
                        return False
            elif isinstance(obj, list):
                return all(_check(item) for item in obj)
            return True

        return _check(data)

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


class MistralAgent(MistralAIAgent):
    """Mistral Large AI agent implementation."""

    # Mistral Large context window is 128K tokens ≈ ~500K chars
    _DESIGN_CHAR_BUDGET = 400_000

    def __init__(self, design_file: pathlib.Path, library_paths: list[pathlib.Path]):
        super().__init__(design_file, library_paths)
        self.model = "mistral-large-latest"

    def process_request(self, user_request: str) -> Tuple[bool, str]:
        """Process request using Mistral API with JSON mode enforced."""
        if not self.api_key:
            return False, "Mistral API key not set. Use set_api_key() method."

        try:
            from mistralai import Mistral
            from mistralai.models import SDKError

            client = Mistral(api_key=self.api_key)

            design_data = self.read_design()
            design_json = json.dumps(design_data, indent=2)

            if len(design_json) > self._DESIGN_CHAR_BUDGET:
                return (
                    False,
                    f"Design is too large ({len(design_json):,} chars) for a single "
                    "request. Consider breaking the modification into smaller steps.",
                )

            system_content = (
                f"{self.get_context(design_data)}\n\n"
                f"Current design JSON:\n{design_json}\n\n"
                "Instructions:\n"
                "1. Read and understand the current design.\n"
                "2. Apply only the requested modifications.\n"
                "3. Return the COMPLETE modified JSON array — no partial output.\n"
                "4. Do NOT use markdown, code fences, or any formatting.\n"
                "5. Preserve the exact structure of unchanged items.\n"
                "6. If no design change is needed, reply with plain text only."
            )

            # Use streaming to avoid timeout on large designs
            response_chunks = []
            finish_reason = None

            with client.messages.stream(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_request},
                ],
                max_tokens=32_768,
                temperature=0.1,
                # Mistral JSON mode — forces valid JSON output when modifying designs
                response_format={"type": "json_object"},
            ) as stream:
                for chunk in stream:
                    delta = chunk.data.choices[0].delta
                    if delta.content:
                        response_chunks.append(delta.content)
                    finish_reason = chunk.data.choices[0].finish_reason

            if finish_reason == "length":
                return (
                    False,
                    "Mistral response was truncated (max_tokens reached). "
                    "The design was not modified.",
                )
            if finish_reason not in ("stop", "eos_token"):
                return False, f"Mistral response incomplete. Finish reason: {finish_reason}"

            response_text = "".join(response_chunks).strip()

            if not response_text:
                return False, "Mistral returned an empty response."

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
                "mistralai package not installed. Install with: poetry add mistralai",
            )
        except (FileNotFoundError, ValueError) as e:
            return False, f"Design file error: {e}"
        except Exception as e:
            logger.exception("Unexpected error in MistralAgent.process_request")
            return False, f"Error processing request: {e}"
