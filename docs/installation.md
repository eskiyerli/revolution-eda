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

Pre-compiled binaries are available for Windows and Linux, created using [Nuitka](https://nuitka.net). These standalone executables run without requiring a separate Python installation.

Download from [Revolution EDA Releases](https://github.com/eskiyerli/revolution-eda/releases):
- **Windows**: `reveda.exe`
- **Linux**: `reveda.bin` (make executable with `chmod +x reveda.bin`)

The binary releases consists of all files that need to start experimenting with Revolution EDA including a preliminary Global Foundries 180 MCU PDK for Revolution EDA. 

## PDK Installation

To use the preliminary IHP PDK:

```bash
git clone https://github.com/eskiyerli/ihp_pdk.git
```

Set the `REVEDA_PDK_PATH` environment variable in your `.env` file depending on where you installed it.
For example, if it is installed in `/home/UserName/ihp_pdk`, you would need to set it to:

```
REVEDA_PDK_PATH=/home/UserName/ihp_pdk
```

On Windows, the path would be something like:

```
REVEDA_PDK_PATH=C:\Users\UserName\ihp_pdk
```

Alternatively, you can use the *Revolution EDA Options* dialog by choosing *Options* menu
from the *Revolution EDA* main window and selecting the directory where the PDK is installed. 

![](assets/revedaOptionsDialogue.png)

The IHP PDK installation directory also has schematic symbols under the `sg13g2_pr` directory that can be used in your designs. There is also a preliminary GF 180 PDK available.

## Example Libraries

There is an example analogLib library and a
Use the Library Path Editor in Revolution EDA to add library paths to the browser.
