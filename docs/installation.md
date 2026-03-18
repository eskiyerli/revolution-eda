# Installation

This guide shows the supported ways to install Revolution EDA and get to a working first
launch quickly. If you only want to try the application, install from PyPI or use a binary
release. If you want the latest source tree or plan to contribute, install from source.

## Quick Orientation

- Revolution EDA supports **Windows**, **Linux**, and **macOS**.
- The Python package currently supports **Python 3.12 through 3.14**.
- The recommended command-line entry point is `reveda`.
- Source installs use **Poetry**.
- Prebuilt binaries are also published through the project's release page.

## Prerequisites

Depending on how you install Revolution EDA, you may need:

- Python `>=3.12,<3.15`
- `pip` for PyPI installation
- [Poetry](https://python-poetry.org/docs/#installation) for source installation

## Installation Paths

Choose the option that best matches your workflow.

### Install from PyPI (Recommended for Most Users)

This is the simplest way to install Revolution EDA if you already have a supported Python
version.

```bash
pip install revolution-eda
```

Start the application with:

```bash
reveda
```

### Install from Source (Recommended for Development)

Use this path if you want the latest checked-out source tree or plan to modify the code.

```bash
git clone https://github.com/eskiyerli/revolution-eda.git
cd revolution-eda
poetry install
poetry run reveda
```

### Use a Binary Release

Standalone binaries are published through the project's GitHub releases page. These are built
with [Nuitka](https://nuitka.net) and do not require a separate Python installation.

Downloads are available from:

- [Revolution EDA Releases](https://github.com/eskiyerli/revolution-eda/releases)

Common binary names include:

- **Windows**: `reveda.exe`
- **Linux**: `reveda.bin`

On Linux, you may need to mark the binary executable first:

```bash
chmod +x reveda.bin
./reveda.bin
```

## First Launch Checklist

After installation, the next practical steps are:

1. Start Revolution EDA.
2. Open the Library Browser from the main window.
3. Set up your libraries, PDK, and plugins as needed.
4. Open or create a schematic, symbol, or layout view.

## Which Installation Method Should You Choose?

| Goal | Recommended Method | Why |
| --- | --- | --- |
| Try the application quickly | PyPI | Simplest setup if Python is already installed |
| Run without managing Python | Binary release | Self-contained application package |
| Develop or contribute | Source + Poetry | Matches the project's development workflow |

## Troubleshooting

### `reveda` command not found

- Make sure the Python environment where you installed Revolution EDA is active.
- If you used Poetry, start the app with `poetry run reveda`.

### Unsupported Python version

- Check that you are using Python 3.12, 3.13, or 3.14.

### Application starts but no libraries or PDK appear

- Installation may be correct, but runtime setup may still be incomplete.
- Continue with the main-window setup guide to configure libraries, PDK paths, and plugins.

## Next Steps

After installation, continue with:

- [Main Window](./revedaMainWindow.md) for application setup and library/PDK/plugin access
- [Schematic Editor Tutorial](./schematicTutorial.md)
- [Symbol Editor Tutorial](./symbolTutorial.md)
- [Layout Editor Tutorial](./layoutTutorial.md)

## Final Notes

- For most users, the PyPI path is the fastest way to get started.
- For contributors or users tracking the latest source tree, the Poetry-based source install is
  the best fit.
- Installation is only the first step; a usable Revolution EDA environment also needs
  libraries, a PDK, and optionally plugins.

