# Installation

Revolution EDA can be used on Windows, Mac, and Linux systems. There are several installation methods depending on your preference and experience.

## Prerequisites

- Python 3.12 or 3.13
- [Poetry](https://python-poetry.org/docs/#installation) dependency management tool (if installing from source)

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

Pre-compiled binaries are available for Windows and Linux, created using [Nuitka](https://nuitka.net). These executables run without requiring a separate Python installation.

Download from [Revolution EDA Releases](https://github.com/eskiyerli/revolution-eda/releases):
- Windows: `reveda.exe`
- Linux: `reveda.bin` (make executable with `chmod +x reveda.bin`)

## PDK Installation

To use the preliminary IHP PDK:

```bash
git clone https://github.com/eskiyerli/ihp_pdk.git
```

Set the `REVEDA_PDK_PATH` environment variable in your `.env` file depending on where you installed it.
For example if it is installed in `/home/UserName/ihp_pdk`, you would need to set it to 

```
REVEDA_PDK_PATH=/home/UserName/ihp_pdk
```

Alternatively, you could use *Revolution EDA Options* dialog by choosing *Options* menu
from *Revolution EDA* main window and selecting the directory where the PDK installed. 

![](/home/eskiyerli/onedrive_reveda/Projects/design_software/revolution-eda/docs/assets/revedaOptionsDialogue.png)

IHP PDK installation directory also has schematic symbols under sg132_pr directory that can be used with There is also a preliminary GF_180 pdk

## Example Libraries

For example components and IHP sg13g2_pr library:

```bash
git clone https://github.com/eskiyerli/exampleLibraries.git
```

Use the Library Path Editor in Revolution EDA to add library paths to the browser.
