# Revolution EDA Layout Editor

The layout editor in Revolution EDA provides a comprehensive suite of tools for designing
the physical layout of custom integrated circuits. It supports hierarchical design through
cell instantiation and includes advanced features like parametric cells, design rule
checking (DRC), and GDS import/export.

## Supported Editing Elements

The layout editor enables creation and editing of:

1. **Instances** of other layout cells to create hierarchical layouts
2. **Rectangles** on any layout layer
3. **Paths (Wires)** with configurable width, orientation, and extensions
4. **Pins** including pin rectangles and labels for connectivity
5. **Labels** for net names, port labels, and annotations
6. **Vias** (single and array) to vertically connect different layers
7. **Polygons** with arbitrary corners and complex shapes
8. **Parametric Cells (pcells)** for programmatically generated layout instances
9. **Rulers** for on-screen measurement of dimensions and distances

## Layout Editor Interface

The Layout Editor Window consists of the following main areas below the menu and toolbar:

### Layer Selection Window (LSW)

Located on the left side, the LSW presents layer information in five columns:

1. **Layer Stipple**: Visual texture sample of the layer (created via the Stipple Editor in
   Tools menu)
2. **Layer Name**: Name of the layer, typically corresponding to a GDS layer number
3. **Layer Purpose**: Layer purpose such as "drawing", "pin", "text", etc. (corresponds to
   GDS datatype)
4. **Visibility**: Checkbox to toggle layer visibility in the layout view
5. **Selectable**: Checkbox to toggle whether shapes on this layer can be selected

### Layout Editor Scene

The main editing area where all layout operations are performed. The scene provides:

- Multi-layer editing with layer-based filtering
- Grid-based snapping for precise placement
- Zoom and pan capabilities
- Selection and manipulation of layout elements

<img src="assets/layoutEditorWindowAnnotated.png" class="image fit"/>

## Additional Editing Tools

### Align Items

Align selected layout elements to common edges or centers for organized, professional
layouts.

**Usage**:

1. Select multiple items (rectangles, paths, instances, etc.)
2. Press `Shift+A` or select `Edit→Align Items`
3. Choose alignment type:
    - **Align Left**: Align left edges
    - **Align Right**: Align right edges
    - **Align Top**: Align top edges
    - **Align Bottom**: Align bottom edges
    - **Center Horizontally**: Distribute centers horizontally
    - **Center Vertically**: Distribute centers vertically

### Cut Shape

Cut shapes from the layout using boolean operations.

**Usage**:

1. Select a shape (path, rectangle or polygon) to cut from
2. Press `Shift+C` or select `Edit→Cut Item`
3. Enter cut mode and define cutting line.
4. Cut line could be diagonal, vertical or horizontal.
5. A path would be divided into two paths, while rectangles and polygons would be divided
   into two polygons.

This is useful for creating complex layouts by subtracting areas from rectangles or
polygons.

## PDK creation for Layout Editor

A process design kit for the physical layout of an integrated circuit requires extensive
information. Among others, a PDK should include:

1. Layout layers information
2. Process information such as database units (dbu), via definitions, via layers, etc
3. Layout parametric cells
4. Layout design rules for Design Rules (DRC) checking.
5. Layout extraction rules for layout-versus-schematic checks (LVS).
6. Layout parasitics extraction, i.e. resistive, capacitive and inductive parasitic elements
   due to physical layout.

**Current Support**: Revolution EDA infrastructure currently includes the first four items.
LVS verification functionality will be soon integrated to Revolution EDA. Layout parasitics
extraction is planned to be implemented after version 1.0.

**PDK Structure**: PDKs are Python modules structured in several distinct files. The PDK
folder is referenced via the `REVEDA_PDK_PATH` environment variable (or `.env` file), making
it easy to support multiple PDKs or project-specific configurations.

**Example Configuration** in `.env`:

```bash
REVEDA_PDK_PATH = ./pdk  # or absolute path, or ../gf180_pdk, etc.
```

## PDK Module Structure

A Revolution EDA PDK consists of the following Python modules:

### LayoutLayers (`layoutLayers.py`)

```python
@dataclass
class layLayer:
    name: str = ""  # edLayer name
    purpose: str = "drawing"  # layout Layer purpose
    pcolor: QColor = Qt.black  # pen colour
    pwidth: int = 1  # pen width
    pstyle: Qt.PenStyle = Qt.SolidLine  # pen style
    bcolor: QColor = Qt.transparent  # brush colour
    btexture: str = ""  # brush texture
    z: int = 1  # z-index
    selectable: bool = True  # selectable
    visible: bool = True  # visible
    gdsLayer: int = 0  # gds edLayer
    datatype: int = 0  # gds datatype
```

Note that all the relevant information for a layer is collated in a single definition. A
layout layer definition entry in `layoutLayers.py` module will look like this:

```python
odLayer_drw = ddef.layLayer(
    name="od",
    purpose="drw",
    pcolor=QColor(255, 0, 0, 127),
    pwidth=1,
    pstyle=Qt.SolidLine,
    bcolor=QColor(255, 0, 0, 127),
    btexture="pdk/stipple1.png",
    z=1,
    visible=True,
    selectable=True,
    gdsLayer=0,
)
```

- *name*: Name of the layer
- *purpose*: Purpose of the layer such as **drw**, **pin**, etc.
- *pcolor*: Colour of the layer expressed as Red, Green, Blue and Transparency levels.
- pwidth: Pen width
- pstyle: Pen style
- *bcolor*: Similarly colour ofbrush is defined by `bcolor` property.
- *btexture*: This property defines the texture of brush defined in a stipple png file.
  There is a separate stipple editor that can be accessed from the main Revolution EDA
  window using `Tools->Create Stipple…` menu item.
- **z**: Stacking order (higher values appear on top)
- **gdsLayer/datatype**: GDS layer/datatype numbers for foundry compatibility

### Parametric Cells (`pcells.py`)

Defines parametric layout cells as Python classes. These cells programmatically generate
geometry based on parameters, enabling:

- Reusable device definitions (NMOS, PMOS, capacitors, etc.)
- Automatic recalculation when parameters change
- Consistent design rule compliance

**Key Concepts**:

- Inherits from `lshp.layoutPcell` (layout shape base class)
- Implements `__call__()` method to regenerate shapes when parameters change
- Initially created empty; shapes generated when called with parameters
- Parameters can include device W/L/M and other PDK-specific values

**Example**: NMOS Parametric Cell

```python
class nmos(lshp.layoutPcell):
    # Design rule constants (in grid units)
    cut = int(0.17 * fabproc.dbu)
    poly_to_cut = int(0.055 * fabproc.dbu)
    diff_ovlp_cut = int(0.06 * fabproc.dbu)
    # ... more constants ...

    def __init__(self, width: str = "4.0", length: str = "0.13", nf: str = "1"):
        """Initialize with default parameters; shapes created empty."""
        self._deviceWidth = float(width)
        self._drawnWidth = int(fabproc.dbu * self._deviceWidth)
        self._deviceLength = float(length)
        self._drawnLength = int(fabproc.dbu * self._deviceLength)
        self._nf = int(float(nf))  # Number of fingers
        self._widthPerFinger = int(self._drawnWidth / self._nf)
        self._shapes = []  # Empty initially
        super().__init__(self._shapes)

    def __call__(self, width: float, length: float, nf: int):
        """
        Called to update parameters and regenerate shapes.
        Removes old shapes and creates new geometry based on parameters.
        """
        self._deviceWidth = float(width)
        self._drawnWidth = int(self._deviceWidth * fabproc.dbu)
        self._deviceLength = float(length)
        self._drawnLength = int(self._deviceLength * fabproc.dbu)
        self._nf = int(float(nf))
        self._widthPerFinger = self._drawnWidth / self._nf
        self.shapes = self.createGeometry()  # Regenerate layout

    def createGeometry(self) -> list[lshp.layoutShape]:
        """Create and return list of layout shapes (rectangles, paths, etc.)."""
        # Example: Create active area rectangle
        activeRect = lshp.layoutRect(
            QPoint(0, 0),
            QPoint(self._widthPerFinger, ...),
            laylyr.odLayer_drw,  # On OD (diffusion) layer
        )
        # Create poly fingers
        polyFingers = [...]  # Multiple poly rectangles
        return [activeRect, *polyFingers]
```

**Usage in Layout Editor**:

1. Create parametric cell instance via `Create→Create Instance`
2. Select pcell from library
3. Instance appears as a single unit but contains all generated shapes
4. Edit instance properties to change W/L/M parameters
5. Geometry automatically regenerates based on new parameters

### Process (`process.py`)

```python
from PySide6.QtCore import (
    QPoint,
)

import pdk.layoutLayers as laylyr
import pdk.process as fabproc
import revedaEditor.common.layoutShapes as lshp

class nmos(lshp.layoutPcell):
    cut = int(0.17 * fabproc.dbu)
    poly_to_cut = int(0.055 * fabproc.dbu)
    diff_ovlp_cut = int(0.06 * fabproc.dbu)
    poly_ovlp_diff = int(0.13 * fabproc.dbu)
    nsdm_ovlp_diff = int(0.12 * fabproc.dbu)
    li_ovlp_cut = int(0.06 * fabproc.dbu)
    sa = poly_to_cut + cut + diff_ovlp_cut
    sd = 2 * (max(poly_to_cut, diff_ovlp_cut)) + cut

    # when initialized it has no shapes.
    def __init__(
        self,
        width: str = 4.0,
        length: str = 0.13,
        nf: str = 1,
    ):
        self._shapes = []
        # define the device parameters here but set them to zero
        self._deviceWidth = float(width)  # device width
        self._drawnWidth: int = int(
            fabproc.dbu * self._deviceWidth
        )  # width in grid points
        self._deviceLength = float(length)  # gate length
        self._drawnLength: int = int(fabproc.dbu * self._deviceLength)
        self._nf = int(float(nf))  # number of fingers.
        self._widthPerFinger = int(self._drawnWidth / self._nf)
        super().__init__(self._shapes)

    #

    def __call__(self, width: float, length: float, nf: int):
        """
        When pcell instance is called, it removes all the shapes and recreates them and adds them as child items to pcell.
        """
        self._deviceWidth = float(width)  # total gate width
        self._drawnWidth = int(
            self._deviceWidth * fabproc.dbu
        )  # drawn gate width in grid points
        self._deviceLength = float(length)  # gate length
        self._drawnLength = int(
            self._deviceLength * fabproc.dbu
        )  # drawn gate length in grid points
        self._nf = int(float(nf))  # number of fingers
        self._widthPerFinger = self._drawnWidth / self._nf
        self.shapes = self.createGeometry()

    def createGeometry(self) -> list[lshp.layoutShape]:
        activeRect = lshp.layoutRect(
            QPoint(0, 0),
            QPoint(
                self._widthPerFinger,
                int(
                    self._nf * self._drawnLength
                    + 2 * nmos.sa
                    + (self._nf - 1) * nmos.sd
                ),
            ),
            laylyr.odLayer_drw,
        )
        polyFingers = [
            lshp.layoutRect(
                QPoint(
                    -nmos.poly_ovlp_diff,
                    nmos.sa + finger * (self._drawnLength + nmos.sd),
                ),
                QPoint(
                    self._widthPerFinger + nmos.poly_ovlp_diff,
                    nmos.sa
                    + finger * (self._drawnLength + nmos.sd)
                    + self._drawnLength,
                ),
                laylyr.poLayer_drw,
            )
            for finger in range(self._nf)
        ]
        # contacts = [lshp.layoutRect(

        # )]
        return [activeRect, *polyFingers]

    @property
    def width(self):
        return self._deviceWidth

    @width.setter
    def width(self, value: float):
        self._deviceWidth = value

    @property
    def length(self):
        return self._deviceLength

    @length.setter
    def length(self, value: float):
        self._deviceLength = value

    @property
    def nf(self):
        return self._nf

    @nf.setter
    def nf(self, value: int):
        self._nf = value
```

### Process (`process.py`)

Defines PDK-specific constants and process parameters:

**Database Units (dbu)**: Conversion factor between user coordinates and GDS grid

- Typically: 1 dbu = 1 nanometer or 1 picometer
- Example: `dbu = 1e-9` (1 nm grid)

**Via Definitions**: Specifies via layers and geometry for vertical interconnection

- `processVias`: List of via definitions with layer pairs and dimensions
- Minimal and maximal spacing constraints

**Path Definitions**: Configures available metal/polysilicon layers for routing paths

- `processPaths`: List of path types with width and extension constraints
- Minimum width and spacing rules

**GDS Export Settings**:

- `gdsUnit`: GDS database unit (typically 1e-6 = 1 μm)
- `gdsPrecision`: Coordinate precision (typically 1e-9 = 1 nm)

### Schematic Layers (`schLayers.py`)

Defines layer properties used in schematic views (wire, pin, text, etc.). Uses the same
`edLayer` dataclass as used elsewhere in the codebase. Schematic layers define:

- Wire net layer appearance
- Pin and port symbols
- Text annotation layers
- Connection points and junction markers

### Symbol Layers (`symLayers.py`)

Defines layer properties for symbol representations (visual schematic symbols). Similar to
schematic layers, uses `edLayer` dataclass and controls:

- Symbol pin appearance
- Symbol shape rendering
- Text label styling
- Visual distinction for different symbol types

## Editing Functions

All editing operations are accessible via:

- Menu items under `Create` and `Edit` menus
- Toolbar buttons for quick access
- Keyboard shortcuts for efficient workflow

### Rectangles

Create rectangles on any layer by:

1. Selecting `Create→Rectangle` menu item
2. Pressing the `Create Rectangle` toolbar button
3. Pressing the `r` key

**Creation**: Click the right mouse button at one diagonal corner, then at the opposite
corner. Rectangle is created on the selected layer in the LSW.

**Properties Dialog**: Select a rectangle and press `q` or choose
`Edit→Properties→Object Properties` to modify:

- Width and height
- Top-left corner coordinates (in μm)
- Layer assignment

<img src="assets/drawingLayoutRectangles.png" class="image fit" />
<img src="assets/layoutRectanglePropertiesDialogue.png" style="zoom: 67%;" />

### Paths (Wires)

Draw paths by:

- Selecting `Create→Create Path...` menu item
- Pressing the `Create Path` toolbar button
- Pressing the `w` key

This opens the **Create Path Dialog** with configurable settings:

**Path Orientation Options**:

- **Manhattan**: 0°, 90°, 180°, 270° angles only
- **Diagonal**: 45° step angles (0°, 45°, 90°, 135°, etc.)
- **Any**: Arbitrary angles
- **Horizontal**: 0° and 180° angles only
- **Vertical**: 90° and 270° angles only

**Settings**:

1. **Path Layer**: Choose from available drawing layers (default: first drawing layer)
2. **Path Width**: Minimum width defaults from PDK process definition
3. **Start Extend**: Extension behind starting point (default: width/2)
4. **End Extend**: Extension beyond ending point (default: width/2)

**Editing After Creation**:

- Modify with `Path Properties Dialog` after drawing
- Use **Stretch Mode** (`s` key) to adjust endpoints interactively
    - Select path, press `s`, click endpoint (cursor shows double-arrow)
    - Move mouse to desired location, press `Esc` to finish

<img src="assets/createPathDialogue.png" style="zoom:67%;" />
<img src="assets/pathEditExamples.png" class="image fit" />
<img src="assets/layoutPathPropertiesDialogue.png" class="small-image" />
<img src="assets/layoutPathStretch.png" class="small-image" />

### Pins

Pins in Revolution EDA consist of two components:

1. **Pin Rectangle**: Defines the pin boundary/shape on a pin layer
2. **Pin Label**: Defines the pin name and its position

Most LVS (Layout-versus-Schematic) tools use label information and placement to verify pin
locations.

**Creation**:

1. Press `p` key, select `Create→Create Pin...`, or click the `Create Pin` toolbar button
2. Configure pin properties in the dialog:
    - **Pin Name**: Required; must match schematic port names
    - **Pin Direction**: Input, Output, Inout, or Power
    - **Pin Type**: Signal, Power, Ground, etc.
    - **Pin Layer**: Defaults to first pin layer (from `pdkPinLayers`)
    - **Label Properties**: Font, size, height, alignment, orientation

    - Pin layer defaults to first member of `pdkPinLayers` list in `layoutLayers.py`
    - Label layer defaults to first member of `pdkTextLayers` list

3. Click `OK`, then:
    - Right-click for first corner of pin rectangle
    - Drag and right-click again for opposite corner
    - Label appears at cursor location
    - Right-click to place label within pin rectangle
    - Press `Esc` to finish

<img src="assets/createLayoutPinDialogue.png" class="small-image" />
<img src="assets/layoutPinEntry.png" class="small-image" />

### Labels

Create standalone labels (without pin shapes) by:

- Pressing `Shift+L` or `L` key
- Selecting `Create→Create Label...`
- Clicking the `Create Label` toolbar button

**In the Label Dialog**:

1. Enter label name
2. Choose label layer from available text layers (`pdkTextLayers`)
3. Click `OK`

The label follows your cursor and is placed by right-clicking at the desired location.
Labels are used by LVS tools to define net connectivity and are essential for layout
verification.

<img src="assets/layoutLabelCreateDialogue.png" class="small-image" />

### Polygons

Create arbitrary closed shapes with 3 or more corners by:

- Pressing `Shift+P` or relevant menu item
- Selecting `Create→Create Polygon`

**Editing Process**:

1. Right-click to place each corner sequentially
2. A guide line shows connection to cursor position after each click
3. Continue adding corners as needed
4. Right-click on the first corner again to close the polygon
5. Press `Esc` to finish

**Editing Existing Polygons**:

- Use **Stretch Mode** (`s` key) to move individual corners:
    - Select polygon, press `s`
    - Right-click on corner to move
    - Drag while holding right-click
    - Release to place at new location
- Use `Layout Polygon Properties` dialog to:
    - Edit corner coordinates directly
    - Change polygon layer
    - Modify other properties

<img src="assets/layoutPolygonEditingFirst.png" class="vertical-image" />
<img src="assets/layoutPolygonEditingSecond.png" class="vertical-image" />
<img src="assets/layoutPolygonPropertiesDialogue.png" class="small-image" /> 

### Rulers

Rulers measure distances between two points on the layout. Revolution EDA supports
orthogonal (horizontal/vertical) rulers.

**Creation**:

- Press `k` key
- Select `Create→Add Ruler`
- Click `Add Ruler` toolbar button

**Usage**:

1. Right-click at first measurement point
2. Right-click at second measurement point (ruler measures between points)
3. Press `Esc` or select another editing function to finish

**Management**:

- **Delete All Rulers**: Press `Shift+K`, or select `Delete Rulers` menu item/toolbar button
- **Move Rulers**: Select a ruler and drag to new position
- **Delete Individual Ruler**: Select and delete with `Delete` key

<img src="assets/layoutRulerAddition.png" class="image fit" />

### Vias

Vias electrically connect different metal layers vertically. Revolution EDA supports both
single vias and via arrays configured through the PDK's via definitions.

**Creating Vias**:

- Press `v` key
- Select `Create→Create Via...`
- Click `Create Via` toolbar button

Opens the **Create Via Dialog** allowing you to:

1. Select via type from PDK definitions
2. Choose between **Single Via** or **Via Array** mode
3. Configure array parameters (spacing and repetition)

**Single Via**: Click right mouse button at desired location to place.

**Via Array**:

- Specify X and Y spacing between via centers
- Define number of vias in X and Y directions
- Useful for creating regular interconnect patterns with proper spacing constraints

### Instantiating Layout Cells

By creating layout cells including other layout cells, rectangles, paths, pins, labels,
polygons and parametric layout cells (pcells), a hierarchic layout design can be
accomplished. A layout cell can be instantiated similar to a schematic cell either by
pressing `I` key, or selecting `Create->Create Instance` menu item.

<img src="assets/layoutInstance.png" class="image fit"/>

## GDS Export and Design Verification

### GDS Export

GDS (Graphical Data System) is the standard output format for integrated circuit foundries.
Revolution EDA exports hierarchical binary GDS files using the industry-standard `gdstk`
package.

**Exporting to GDS**:

1. Select `Tools→Export GDS` menu item
2. In the export dialog, configure:
    - **Database Unit**: Defaults from `process.py` (typically 1e-6 meters or 1 micron)
    - **Precision**: Resolution for GDS coordinates (default from PDK)
    - **Export Location**: Directory where GDS file will be saved

3. Click `OK` to export hierarchical GDS file

The exported GDS can be further processed, viewed in KLayout, and used for DRC/LVS
verification.

<img src="assets/GDSExport.png" class="image fit"/>

### KLayout Design Rule Checking (DRC)

For PDKs with DRC support, Revolution EDA integrates KLayout's DRC engine for rule
verification. DRC checking requires:

- KLayout installed on your system
- PDK with DRC rules (`klayoutDRC` module and `.lydrc` rule files)

**Running KLayout DRC**:

1. Select `Tools→KLayout DRC/LVS→KLayout DRC...`
2. In the DRC Configuration Dialog, specify:
    - **KLayout Path**: Location of KLayout executable
    - **Cell Name**: Name of cell to verify (auto-filled)
    - **DRC Rule Set**: Select from available rule files (minimal, maximal, etc.)
    - **Run Limit**: Number of parallel DRC processes
    - **Output Directory**: Where DRC report files are saved

3. **GDS Export**: Optionally auto-export GDS during DRC run
4. Click **Run** to execute DRC verification

**DRC Results**:

- Results displayed in DRC Errors Dialog showing rule violations
- Violations can be highlighted by layer/rule type
- Clicking violations highlights corresponding layout polygons in real-time
- Results saved to `.lyrdb` (KLayout report database) format and can also be viewed in
  KLayout if so preferred.

This enables efficient design verification within the Revolution EDA workflow without manual
KLayout interaction.


