# Revolution EDA Symbol Editor

Symbol Editor is where the schematic representation of a basic circuit component, such as an
inductor, capacitor or even an entire circuit can be created to be later used in the
schematic
editor.

Revolution EDA symbol editor is geared towards representation of integrated circuit
components
with complex geometry dependent parameters. Symbol editor has basic drawing functionality
for

1. Lines
2. Circles
3. Arcs
4. Rectangles
5. Polygons

Edits can be undone or redone using `Undo` or `Redo` toolbar buttons, or `U` or `Shift-U`
keys.

<img src="assets/symbolEditorWindow.png"  class="image fit" />

## Quick Orientation (for Virtuoso Users)

| Virtuoso Action | Revolution EDA Equivalent | Notes |
|---|---|---|
| Add wire/line | `Create -> Create Line...` or `W` | Draws horizontal/vertical line segments |
| Add rectangle | `Create -> Create Rectangle...` or `R` | Click two diagonal corners |
| Add circle | `Create -> Create Circle...` | Click centre, drag to set radius |
| Add arc | `Create -> Create Arc...` | Two-corner bounding box; direction set by diagonal angle |
| Add polygon | `Create -> Create Polygon...` | Left-click to add points; double-click to finish |
| Add pin | `Create -> Create Pin...` or `P` | Set name, direction, and type in the dialog |
| Add label | `Create -> Create Label...` or `L` | Normal, NLPLabel, or PyLabel types |
| Edit properties | Select item, press `Q` | Shape, pin, or label properties |
| Edit cellview attributes | `Edit -> Cellview Properties...` | Symbol-level netlist attributes |
| Stretch shape | Select item, press `S` | Adjust endpoints/radius of lines, arcs, circles |
| Undo | `U` | Up to 99-level undo stack |
| Redo | `Shift+U` | Reapply the last undone operation |
| Fit to window | `F` | Scales the view to show all items |

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `W` | Create Line |
| `R` | Create Rectangle |
| `P` | Create Pin |
| `L` | Create Label |
| `S` | Stretch selected item |
| `C` | Copy selected items |
| `U` | Undo |
| `Shift+U` | Redo |
| `Q` | Object Properties |
| `F` | Fit to Window |
| `Delete` | Delete selected items |
| `Ctrl+R` | Rotate 90° CW |
| `Ctrl+A` | Select All |
| `Shift+A` | Align Items |

## Menu Actions

### File Menu

<img src="assets/symbolEditorFileMenu.png"  class="small-image" />

The File menu handles saving, printing, and exporting the symbol cellview.

| Action | Shortcut | Notes |
|---|---|---|
| `File -> Check-Save` | None | Validates and saves the symbol to disk. |
| `File -> Save` | None | Saves without running checks. |
| `File -> Update Design` | None | Reloads all referenced cell data from disk. |
| `File -> Print...` | None | Sends the symbol view to a printer. |
| `File -> Print Preview...` | None | Preview print output before printing. |
| `File -> Export...` | None | Exports the symbol as a PNG/JPEG/BMP image file. |
| `File -> Close Window` | `Ctrl+Q` | Closes the window; symbol is auto-saved on close. |

### View Menu

<img src="assets/symbolEditorViewMenu.png"  class="small-image" />

| Action | Shortcut | Notes |
|---|---|---|
| `View -> Fit to Window` | `F` | Scales the view to show all symbol items. |
| `View -> Zoom In` | None | Increases magnification; mouse wheel also zooms. |
| `View -> Zoom Out` | None | Decreases magnification. |
| `View -> Pan View` | None | Click to re-centre the view at the clicked point. |
| `View -> Redraw` | None | Forces a full repaint of the scene. |

### Edit Menu

<img src="assets/symbolEditorEditMenu.png"  class="small-image" />

The Edit menu provides shape manipulation, transformation, and undo/redo commands.

| Action | Shortcut | Notes |
|---|---|---|
| `Edit -> Undo` | `U` | Reverts the most recent change (up to 99 levels). |
| `Edit -> Redo` | `Shift+U` | Reapplies the last undone change. |
| `Edit -> Paste` | None | Pastes copied items at the cursor location. |
| `Edit -> Delete` | `Delete` | Removes selected items from the symbol. |
| `Edit -> Copy` | `C` | Copies the current selection for pasting. |
| `Edit -> Move` | None | Moves selected items interactively on the canvas. |
| `Edit -> Move By...` | None | Moves the selection by a precise X/Y offset via dialog. |
| `Edit -> Move Origin` | None | Repositions the scene origin; click to set the new point. |
| `Edit -> Stretch` | `S` | Adjusts endpoints of lines, arcs, and radius of circles. |
| `Edit -> Rotate...` | `Ctrl+R` | Rotates selected items 90° clockwise around a pivot point. |
| `Edit -> Horizontal Flip` | None | Mirrors selected items across the vertical axis. |
| `Edit -> Vertical Flip` | None | Mirrors selected items across the horizontal axis. |
| `Edit -> Align Items...` | `Shift+A` | Opens the alignment dialog for edge or guide-line alignment. |
| `Edit -> Selection -> Select All` | `Ctrl+A` | Selects every item in the symbol view. |
| `Edit -> Selection -> Unselect All` | None | Clears the current selection. |
| `Edit -> Cellview Properties...` | None | Opens the symbol attributes and label summary dialog. |

### Create Menu

<img src="assets/symbolEditorCreateMenu.png"  class="small-image" />

| Action | Shortcut | Notes |
|---|---|---|
| `Create -> Create Line...` | `W` | Draw a line segment: click to start, release to end. |
| `Create -> Create Rectangle...` | `R` | Click two diagonal corners to define the rectangle. |
| `Create -> Create Polygon...` | None | Left-click to add points; double-click to finish. |
| `Create -> Create Circle...` | None | Click the centre point, then drag to set the radius. |
| `Create -> Create Arc...` | None | Click two diagonal corners; arc direction follows the diagonal angle. |
| `Create -> Create Label...` | `L` | Opens the label dialog; choose Normal, NLPLabel, or PyLabel type. |
| `Create -> Create Pin...` | `P` | Opens the pin dialog to set pin name, type, and direction. |

### Options Menu

<img src="assets/symbolEditorOptionsMenu.png"  class="small-image" />

The symbol editor inherits the `Options` menu from the base editor window.

- `Options -> Display Config...`: configure the grid display (dot or line grid) and the major/snap grid spacing.
- `Options -> Selection Config...`: choose between **partial** (intersects items) and **full** (contains items entirely) selection mode.

<table>
    <tr>
        <td><img src="assets/schematicDisplayOptionsDialogue.png"  class="small-image" /></td>
        <td><img src="assets/schematicSelectionConfigDialogue.png"  class="small-image" /></td>
    </tr>
</table> 

| Action | Notes |
|---|---|
| `Options -> Display Config...` | Major grid, snap grid, dot vs. line grid background. |
| `Options -> Selection Config...` | Partial selection allows rubber-band to intersect shapes; full selection requires full containment. |

### Tools Menu


| Action | Notes |
|---|---|
| `Tools -> Read Only` | Toggle; when checked, no edits are permitted in the current view. |

## Drawing Actions

## Lines

Lines are drawn by pointing-and-pressing left mouse button at the start and releasing at the
end
point of the line. Lines can be horizontal or vertical. A drawn line can be edited either by
selecting it and pressing `q` key

<img src="assets/symbolLineProperties.png" class="small-image" />

or by selecting `stretch` mode (`s`-key or selecting `stretch` option at the context menu accessible with right-mouse button click). Then, select either end of the line, the line will turn red and end points of the line will be indicated by a circle. The user should click on which ever end point is to be changed and move it to the new location and release the left mouse button.

<img src="assets/symbolEditorStretchLine.png" class="small-image" />


## Circles

Circles are drawn by selecting a centre point, pressing left-mouse button at that point and
releasing left-mouse button. It can be also edited similarly to a line either by displaying
the
properties dialogue (select the circle and press `q` key or select the `Properties` option
in
the contextual menu),

<!-- Screenshot: Circle properties dialog -->

or by pressing `m` key or selecting `stretch` option. The circle will turn red and a hand
shape
will denote that stretch mode is activated. Just move the hand-cursor so that the circle is
the
right size.

<!-- Screenshot: Stretching a circle -->

Beyond drawing a the symbol outline, the symbol editor can also indicate pins, where the
element
or the circuit is connected to the other elements or circuits.

## Rectangles

Rectangles are similarly created by pressing mouse button at one corner and then releasing
it at
the other diagonal corner.

<!-- Screenshot: Rectangle creation example -->

Rectangles can be similarly edited using properties dialogues or stretching any side by
selecting that side after pressing `m` key or selecting `stretch` option in the contextual
menu.

<!-- Screenshot: Rectangle properties or stretch example -->

## Arcs

Arc drawing is performed similarly to a rectangle drawing. Depending on the angle of
diagonal
arc will be pointing any of the four directions:

| Diagonal Angle       | Arc Direction |
|----------------------|---------------|
| 90 > $\theta$ > 0    | Up            |
| 180 > $\theta$ > 90  | Left          |
| 270 > $\theta$ > 180 | Down          |
| 360 > $\theta$ > 270 | Right         |

Similarly to other shapes, arcs can be also be edited using property dialogue or by
stretching.
One caveat in stretching is that if the bounding rectangle of a stretched arc is flipped, it
will be saved correctly in the cellview file. This is a known bug.

<!-- Screenshot: Arc creation or stretch example -->

## Polygons

Polygons are created by selecting `Create->Create Polygon…` menu item or pressing
`Create Polygon` item from the
toolbar. To start the polygon, click on the right mouse button for the first point. A guide
line will be shown between
that point and the present cursor location. Now press the right mouse button again to select
the second point of the
polygon. A line will be created between the first and second point, while the guideline
between these points will be
erased. Instead, there will be another guide line between the second point and the cursor
position. Once again pressing
right mouse button will create another line between second and third points. Moreover a
triangle consisting of first,
second and third points will be drawn. If the user double clicks right mouse button at this
point, the polygon create
action will be stopped. Alternatively, the user can press `Esc` button on the keyboard. On
the other hand, if the user
now clicks another point on the editor, a *quadrilateral* will be created. Similarly adding
another point will yield a
pentagram and so on.

<!-- Screenshot: Polygon creation example -->

A polygon can be edited in a few different ways. The easiest is to select the polygon and
press `S` key to stretch the polygon. Now press on one of the corners of the polygon, if the
corner is selected, a blue circle will be placed at that corner. Now move your cursor while
pressing right mouse button and release it when you polygon corner is where you want it to
be:

<!-- Screenshot: Polygon stretch example -->

Polygons can be also be edited using a dialogue. Select the polygon and bring up the
`Symbol Polygon Properties` dialogue. All the points will be listed with their x and y
coordinates. The designer can delete any point selecting the checkbox on the first column or
edit that point. Alternatively, a new point can be edited using the last empty row. When
that row is edited, a new row is created for further point entry. There can be up to 999
points in a polygon.

<!-- Screenshot: Symbol polygon properties dialog -->

## Pins

Pins denote the connection of the element or circuit defined by symbol to the external
circuits.
Pins can be created by clicking toolbar icon or selecting `create Pin…` menu item under
`Create`
menu. Note that pin direction and pin type information is not saved or used for the symbol
cell
views at the moment.

<!-- Screenshot: Create pin dialog -->

## Labels

Labels carry all the relevant information for an instance of a cellview. Thus labels may
have
different values (texts) for each instance.

There are three types of labels:

1. **Normal**: These type of labels is just adding some notes on the text. They are not used
   in
   netlisting.

2. **NLPLabel**: These types of labels are evaluated using simple rules. Their format is:

   `[@propertyName:propertyName=%:propertyName=defaultValue]`

   The parts of the NLPLabel is separated by columns(:). Note that
   only **@propertyName** part is mandatory. The second and third parts
   do not need to exist in all NLPLabels.

   If only first part exists, there are a limited number of *predefined* labels that can be
   used.
   These are:

   | Label Name     | Label Definition | Explanation                                       |
      | -------------- | ---------------- | ------------------------------------------------- |
   | cell name      | `[@cellName]`    | Cell Name, e.g. nand2, nmos, etc                  |
   | instance name  | `[@instName]`    | Instance name for netlisting, e.g. I1, I15, etc.  |
   | library Name   | `[@libName]`     | Library Name for the symbol                       |
   | view Name      | `[@viewName]`    | View Name, normally includes *symbol* in the name |
   | element Number | `[@elementNum]`  | Element Number, forms a part of Instance Name     |
   | model Name     | `[@modelName]`   | Model name for the element in the netlist         |

   Model name label `[@modelName]` defaults to `modelName` entry in symbol attributes. If
   the third part exists, the label text is determined by whether a label value is entered
   for the instance. If the label value is entered, then the second part is used to display
   the label, if not the third part is shown and used.

   NLP labels can be referred by their the first part of the label definition. For example,
   if the label definition
   is `[@w:w=%:w=1u]`, then the label can be referred in the symbol attributes as `@w`.

3. **Python Label**: Python labels allow the label values to be determined dynamically based
   on the
   values of other labels or any other values defined in the process design kit (PDK). The
   relevant functions that can be used in Python labels are defined in the
   `PDK/callbacks.py`
   file. Each symbol should have a corresponding class defined in `callbacks.py`. A few
   sample
   definitions are shown in the included `PDK/callbacks.py` file:

   ```python
   class baseInst:
       def __init__(self, labels_dict: dict):
           self._labelsDict = labels_dict
   
   
   class res(baseInst):
       def __init__(self, labels_dict: dict):
           super().__init__(labels_dict)
   
       def doubleR(self):
           Rvalue = self._labelsDict.get("R").labelValue
           if Rvalue.isalnum():
               return str(2 * Quantity(Rvalue))
           return "?"
   
   
   class nmos(baseInst):
       def __init__(self, labels_dict: dict):
           super().__init__(labels_dict)
           self.w = Quantity(self._labelsDict["@w"].labelValue)
           self.l = Quantity(self._labelsDict["@l"].labelValue)
           self.nf = Quantity(self._labelsDict["@nf"].labelValue)
           self.sd1p8v = 0.28
           self.sa1p8v = sb1p8v = 0.265
           self.sourceDiffs = lambda nf: int(int(nf) / 2 + 1)
   
       def asparm(self):
           return self.sourceDiffs(self.nf) * (self.w / self.nf) * self.sd1p8v
   ```

   For example, an `nmos` symbol has an `asparm()` function defined. We can use it to define
   the value of a label
   for the `nmos` symbol. When this symbol is instantiated in a schematic, the value of the
   `as` label will be determined
   by the `asparm()` function defined in the `callbacks.py` file. This means that instance
   callbacks can use all the
   facilities of Python, including advanced libraries, to calculate parameters dynamically.

    <!-- Screenshot: Python label example -->

   Labels can be also be hidden to reduce the clutter in the schematic instance of a symbol.
   Hidden labels are as valid as visible labels. Label properties dialogue also
   have `labelAlignment`, `labelOrientation` and `labelUse` fields, which are currently not
   implemented. However, labels can be rotated using context menu’s `rotate` option.

## Attributes

Attributes are properties that are common to all instances of a symbol. They could denote
for example, how a particular
symbol would be netlisted in Xyce circuit simulator netlist using `SpiceNetlistLine`
attribute. *NLPDeviceFormat*
expressions was originally created for Glade by Peardrop Design Systems. It consists of
string constants and NLP
Expressions.

Some of the important attributes for a symbol are summarized below:

| Attribute Name          | Attribute Use                                           | Example                                                              |
|-------------------------|---------------------------------------------------------|----------------------------------------------------------------------|
| SpiceNetlistLine        | Netlist template used for symbol/spice/veriloga views   | `M@instName %pinOrder %modelName w=@w l=@l nf=@nf as=@as m=@m`      |
| SpiceNetlistLine        | Veriloga-style template example                         | `Yres @instName %pinOrder resModel @R`                               |
| SpiceNetlistLine        | Spice subckt template example                           | `X@instName %pinOrder newckt`                                        |
| vaModelLine             | Used as a model line for Veriloga netlisting            | `.MODEL resModel res R = 1`                                          |
| vaHDLLine               | Used to by Revolution EDA to create linkable modules    | *`.HDL /home/user/exampleLibraries/analogLib/resVa/res.va`           |
| pinOrder                | To sync pin order between netlists of various cellviews | `PLUS, MINUS`                                                        |
| incLine                 | To include imported Spice subcircuit                    | `.INC /home/user/exampleLibraries/anotherLibrary/example1/newckt.sp` |

Note that the labels are referred by their names prefixed by `@` in the attributes of a
symbol. If a symbol attribute
should be referred in another symbol attribute, it should be prefixed by `%`, see the
example
for `SpiceNetlistLine` in the table above where `modelName` attribute is referred as
`%modelName`.  `pinOrder`
attribute is important to synchronise the various formats for netlisting. It should list all
symbol pins separated by
commas in the order required for the netlisting. This string will replace `%pinOrder` token
in the attributes.

Attributes are defined in the `Cellview properties` dialogue that can be accessed under
`Edit` menu:

<!-- Screenshot: Cellview properties dialog -->

This dialogue has two parts. The first part summarises the already defined labels. Label
properties can be changed also
here.
However labels can be deleted or added here. The second part is the `Symbol attributes`
part. In this dialogue, any
number of symbol attributes can be defined. These attributes will not be shown but can also
be inspected but not edited
in the schematic view.

Depending on how symbol is created not all the attributes needed to use various cellviews
for netlisting are not
available on the same symbol. For example, a designer creates a symbol from the schematic,
but there is also a Verilog-a
view for that cell. In that case, the symbol will have `SpiceNetlistLine` needed for the use
of the Symbol View in
the netlisting but not the attributes to have veriloga cellview to be used in the
netlisting. In that case, the user
should add those attributes manually in the symbol editor window.

### Required attributes for netlisting

The current netlister implementation in `schematicEditor.xyceNetlist` uses
`SpiceNetlistLine` as the netlist template key for symbol, spice, and veriloga views.
In templates, use `%pinOrder` to emit the expanded connection list.

#### Symbol

If a *symbol* cellview is to be used in the netlisting, these are the minimum attributes
that should be defined for that
symbol.

| Attribute Name   | Example                                                        |
|------------------|----------------------------------------------------------------|
| SpiceNetlistLine | `M@instName %pinOrder %modelName w=@w l=@l nf=@nf as=@as m=@m` |
| pinOrder         | `D, G, B, S`                                                   |

Note that another attribute `modelName` needs to be defined for the example in the table.
`pinOrder` controls the net order used by `%pinOrder` during netlisting.

#### Veriloga

If the veriloga cellview is to be used in the circuit netlisting, these attributes should be
added to symbol. Note that
if the veriloga file is imported and used to create a symbol, they will be automatically
added to the symbol.

| Attribute Name          | Example                                                    |
|-------------------------|------------------------------------------------------------|
| SpiceNetlistLine        | `Yres @instName %pinOrder resModel @R`                     |
| vaModelLine             | `.MODEL resModel res R = 1`                                |
| vaHDLLine               | *`.HDL /home/user/exampleLibraries/analogLib/resVa/res.va` |
| pinOrder                | a, b, c                                                    |

`vaModelLine` and `vaHDLLine` are collected and written to the netlist output.

#### Spice

Spice subcircuits can be used in the netlists when the symbol has the proper attributes. The
required attributes for the
netlist inclusion of a SPICE subcircuit are summarised in the table below:

| Attribute Name       | Example                                                              |
|----------------------|----------------------------------------------------------------------|
| SpiceNetlistLine     | `X@instName %pinOrder newckt`                                        |
| incLine              | `.INC /home/user/exampleLibraries/anotherLibrary/example1/newckt.sp` |
| pinOrder             | PLUS, MINUS                                                          |

`incLine` is collected and emitted as an include directive in the generated netlist.

## Other Editing functions

Any item on the symbol editor can be ==rotated, moved or copied== using by selecting menu
item or by clicking on the
relevant button on the toolbar as well as using context menu.

The cursor position is displayed at left-bottom corner of the editor. If the user wants to
move
the origin point of the symbol editor, it can use `Move Origin` menu item under `Edit` menu.
Once it is selected, click at the new origin point. Hereafter, all the editing functions
will
refer to the new origin point.

## Context Menu (Right-click on Item)

Right-clicking on a selected item opens a context menu with the most frequently needed
operations without navigating the menu bar.

<!-- Screenshot: Symbol editor context menu -->

| Action | Shortcut | Notes |
|---|---|---|
| Copy | `C` | Copies the selected item; paste with `Edit -> Paste`. |
| Move | None | Starts interactive move mode for the selected item. |
| Move By... | None | Opens a dialog for a precise X/Y offset move. |
| Vertical Flip | None | Mirrors the item across the horizontal axis. |
| Horizontal Flip | None | Mirrors the item across the vertical axis. |
| Rotate | `Ctrl+R` | Rotates the item 90° clockwise. |
| Delete | `Delete` | Removes the item from the symbol. |
| Object Properties... | `Q` | Opens the property dialog for the item (shape, pin, or label). |
| Select All | `Ctrl+A` | Selects every item in the symbol view. |
| Unselect All | None | Clears the current selection. |
| Stretch | `S` | Enters stretch mode for the selected item. |

