# This software is proprietary and confidential.
# Unauthorized copying, modification, distribution, or use of this software,
# via any medium, is strictly prohibited.
#
# This software is provided as an add-on to Revolution EDA distributed under the
# Mozilla Public License, version 2.0. The source code for this add-on software
# is not made available and all rights are reserved.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# (C) 2024 Revolution Semiconductor


__author__ = "Revolution Semiconductor"
__copyright__ = "Copyright 2026 Revolution Semiconductor"
__license__ = "Proprietary"
__version__ = "0.8.8"
__status__ = "Development"
__date__ = "2026-01-20"
__all__ = []


def __getattr__(name):
    if name == "aiTerminal":
        from . import aiTerminal
        return aiTerminal
    elif name == "toggleAITerminal":
        from .aiTerminal import toggleAITerminal
        return toggleAITerminal
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
