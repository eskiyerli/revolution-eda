# Installation

Revolution EDA can be used on Windows, Mac, and Linux systems. There are several
installation methods depending on your preference and experience.

## Prerequisites

- Python 3.12 or 3.13
- [Poetry](https://python-poetry.org/docs/#installation) dependency management tool (if
  installing from source)

## From PyPI (Recommended)

The easiest way to install Revolution EDA is from PyPI:

```bash
pip install revolution-eda
```

After installation, start the program with:

```bash
reveda
```

## From Source

For development or the latest features:

```bash
# Clone the repository
git clone https://github.com/eskiyerli/revolution-eda.git
cd revolution-eda

# Install dependencies
poetry install

# Run the application
poetry run reveda
```

## Binary Releases

Pre-compiled binaries are available for Windows and Linux, created
using [Nuitka](https://nuitka.net). These standalone executables run without requiring a
separate Python installation.

Download
from [Revolution EDA Releases](https://github.com/eskiyerli/revolution-eda/releases):

- **Windows**: `reveda.exe`
- **Linux**: `reveda.bin` (make executable with `chmod +x reveda.bin`)

In the [Main Window](./revedaMainWindow.md) section, we will discuss how to easily setup example libraries, PDKs and plugins for Revolution EDA.