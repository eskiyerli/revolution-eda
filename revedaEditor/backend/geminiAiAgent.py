#    "Commons Clause" License Condition v1.0
#
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, "Sell" means practicing any or all of the rights
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

"""Gemini AI Agent interface for design modifications."""

import json
import pathlib


class GeminiAIAgent:
    """Base class for Gemini AI agent integration."""

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

    def get_context(self) -> str:
        """Build context string for AI agent."""
        context = f"Design file: {self.design_file}\n"
        context += f"Library paths: {', '.join(str(p) for p in self.library_paths)}\n"
        context += "You can only modify files within the design libraries.\n"
        context += "All changes must be valid JSON format if modifying the design.\n"
        context += "If not modifying the design, do not output any JSON.\n"
        context += "Return responses as plain text only. Do not use markdown, bold, italics, code blocks, lists, or any other formatting.\n"
        context += "Connecting two terminals mean that you should draw a net between them."
        return context


class GeminiAgent(GeminiAIAgent):
    """Gemini AI agent implementation."""

    def __init__(self, design_file: pathlib.Path, library_paths: list[pathlib.Path]):
        super().__init__(design_file, library_paths)
        self.model = "gemini-2.5-flash"

    def process_request(self, user_request: str) -> tuple[bool, str]:
        """Process request using Gemini API."""
        if not self.api_key:
            return False, "Gemini API key not set. Use set_api_key() method."

        try:
            # Import google.generativeai only when needed
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

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

User request: {user_request}
"""

            response = model.generate_content(system_prompt)

            # Check if response was blocked or empty
            if not response.candidates:
                return False, "Gemini response was blocked or empty"

            candidate = response.candidates[0]
            if candidate.finish_reason != 1:  # 1 = STOP (normal completion)
                return False, f"Gemini response incomplete. Finish reason: {candidate.finish_reason}"

            if not candidate.content or not candidate.content.parts:
                return False, "Gemini returned empty content"

            response_text = candidate.content.parts[0].text

            # Strip markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                if len(lines) > 2:
                    response_text = "\n".join(lines[1:-1])

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
            return False, "google-generativeai package not installed. Install with: pip install google-generativeai"
        except Exception as e:
            return False, f"Error processing request: {e}"
