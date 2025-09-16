import xml.etree.ElementTree as ET
import re
import logging
#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
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


from pathlib import Path

from PySide6.QtGui import (
    QColor,
)

from revedaEditor.backend.dataDefinitions import layLayer
from revedaEditor.gui.stippleEditor import stippleEditor
from PySide6.QtCore import Qt

# Set up logging for better error reporting
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_source_field(source_text: str) -> tuple[str, str, int, int]:
    """
    Parse the source field to extract name, purpose, gdsLayer, and dataType.
    
    Expected formats:
    - "COMP 22/0@1" -> name="COMP", purpose="drawing", gdsLayer=22, dataType=0
    - "pass_mk 2/222@1" -> name="pass_mk", purpose="drawing", gdsLayer=2, dataType=222
    - "5/222@1" -> name="layer5", purpose="drawing", gdsLayer=5, dataType=222
    
    Args:
        source_text: The source field text from the LYP file
        
    Returns:
        tuple: (name, purpose, gdsLayer, dataType)
    """
    if not source_text or not source_text.strip():
        logger.warning("Empty source field, using defaults")
        return "unknown", "drawing", 0, 0
    
    # Remove @ and everything after it
    clean_source = source_text.split('@')[0].strip()
    
    # Split on whitespace to separate potential name from layer/datatype
    parts = clean_source.split()
    
    if len(parts) == 1:
        # Format: "22/0" or just "22"
        layer_part = parts[0]
        name = None
    else:
        # Format: "COMP 22/0" or "pass_mk 2/222"
        # Everything except the last part is the name
        name = "_".join(parts[:-1])
        layer_part = parts[-1]
    
    # Parse the layer/datatype part
    if '/' in layer_part:
        try:
            gds_layer_str, datatype_str = layer_part.split('/', 1)
            gds_layer = int(float(gds_layer_str))
            datatype = int(float(datatype_str))
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse layer/datatype from '{layer_part}': {e}")
            gds_layer, datatype = 0, 0
    else:
        # Only layer number provided
        try:
            gds_layer = int(float(layer_part))
            datatype = 0
        except ValueError as e:
            logger.warning(f"Failed to parse layer from '{layer_part}': {e}")
            gds_layer, datatype = 0, 0
    
    # Generate name if not found
    if not name:
        name = f"layer{gds_layer}"
    
    # Use default purpose
    purpose = "drawing"
    
    return name, purpose, gds_layer, datatype


def safe_get_text(element, default: str = "") -> str:
    """Safely get text from an XML element, returning default if element is None or has no text."""
    if element is None:
        return default
    return element.text if element.text is not None else default


def safe_get_color(color_text: str, default_color: QColor = QColor(Qt.black)) -> QColor:
    """Safely parse color text, returning default color if parsing fails."""
    try:
        if color_text and color_text.strip():
            return QColor.fromString(color_text.upper())
    except Exception as e:
        logger.warning(f"Failed to parse color '{color_text}': {e}")
    return default_color


def safe_get_bool(bool_text: str, default: bool = True) -> bool:
    """Safely parse boolean text."""
    if not bool_text:
        return default
    return bool_text.lower() == 'true'


def safe_get_int(int_text: str, default: int = 1) -> int:
    """Safely parse integer text."""
    try:
        if int_text and int_text.strip():
            return int(float(int_text))
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse integer '{int_text}': {e}")
    return default

def parseLyp(lypFile: str, outputFileDir: str) -> bool:
    """
    Parse a LYP (Layer Properties) file and generate layoutLayers.py file.
    
    This function is more robust and handles cases where name fields are empty
    by parsing the source field to extract layer information.
    
    Args:
        lypFile: Path to the input LYP file
        outputFileDir: Directory where layoutLayers.py will be generated
        
    Returns:
        bool: True if parsing was successful, False otherwise
    """
    try:
        lypFileObj = Path(lypFile)
        outputFileDirObj = Path(outputFileDir)
        
        # Validate input file exists
        if not lypFileObj.exists():
            logger.error(f"LYP file does not exist: {lypFile}")
            return False
            
        # Create output directory if it doesn't exist
        outputFileDirObj.mkdir(parents=True, exist_ok=True)
        
        # Parse XML file
        try:
            tree = ET.parse(lypFileObj)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML file '{lypFile}': {e}")
            return False
        
        purposeDict = {}
        layout_layers = []
        skipped_layers = 0
        
        with outputFileDirObj.joinpath("layoutLayers.py").open("w", encoding="utf-8") as file:
            # Write header
            file.write("# Auto-generated layoutLayers.py from LYP file\n")
            file.write("# Do not edit this file manually\n\n")
            file.write("import revedaEditor.backend.dataDefinitions as ddef\n\n")
            
            logger.info(f"Processing LYP file: {lypFile}")
            
            for i, layerItem in enumerate(root.iterfind("properties")):
                try:
                    # Extract basic properties with safe parsing
                    frame_color_elem = layerItem.find("frame-color")
                    fill_color_elem = layerItem.find("fill-color")
                    dither_pattern_elem = layerItem.find("dither-pattern")
                    valid_elem = layerItem.find("valid")
                    visible_elem = layerItem.find("visible")
                    width_elem = layerItem.find("width")
                    name_elem = layerItem.find("name")
                    source_elem = layerItem.find("source")
                    
                    # Parse colors
                    pcolor = safe_get_color(safe_get_text(frame_color_elem), QColor(Qt.black))
                    bcolor = safe_get_color(safe_get_text(fill_color_elem), QColor(Qt.transparent))
                    
                    # Parse other properties
                    btexture = safe_get_text(dither_pattern_elem, "I3") + ".txt"
                    selectable = safe_get_bool(safe_get_text(valid_elem), True)
                    visible = safe_get_bool(safe_get_text(visible_elem), True)
                    pwidth = safe_get_int(safe_get_text(width_elem), 1)
                    
                    # Get name and source text
                    name_text = safe_get_text(name_elem)
                    source_text = safe_get_text(source_elem)
                    
                    # Determine layer name and properties
                    if name_text and name_text.strip():
                        # Use existing name if available
                        if "." in name_text:
                            name, purpose = name_text.split(".", 1)
                        else:
                            name = name_text
                            purpose = "drawing"
                        
                        # Still need to parse source for GDS layer info
                        _, _, gdsLayer, dataType = parse_source_field(source_text)
                    else:
                        # Parse source field when name is empty
                        name, purpose, gdsLayer, dataType = parse_source_field(source_text)
                    
                    # Validate required fields
                    if not name or not name.strip():
                        logger.warning(f"Skipping layer {i}: Invalid name")
                        skipped_layers += 1
                        continue
                    
                    # Clean up name (remove invalid characters)
                    name = re.sub(r'[^\w]', '_', name.strip())
                    purpose = re.sub(r'[^\w]', '_', purpose.strip())
                    
                    # Create layer object
                    layoutLayerItem = layLayer(
                        name=name,
                        purpose=purpose,
                        pcolor=pcolor,
                        pwidth=pwidth,
                        pstyle=Qt.SolidLine,
                        bcolor=bcolor,
                        btexture=btexture,
                        z=i,
                        selectable=selectable,
                        visible=visible,
                        gdsLayer=gdsLayer,
                        datatype=dataType,
                    )
                    
                    # Add to collections
                    layout_layers.append(layoutLayerItem)
                    if purpose not in purposeDict:
                        purposeDict[purpose] = []
                    purposeDict[purpose].append(layoutLayerItem)
                    
                    # Write layer definition
                    file.write(
                        f"{layoutLayerItem.name}_{layoutLayerItem.purpose} = "
                        f"ddef.{layoutLayerItem}\n"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing layer {i}: {e}")
                    skipped_layers += 1
                    continue
            
            # Write purpose-based layer lists
            file.write("\n# Purpose-based layer lists\n")
            pdkAllLayerString = "pdkAllLayers = ["
            
            for purpose, layerList in purposeDict.items():
                if layerList:  # Only write non-empty lists
                    purposeString = f"pdk{purpose.capitalize()}Layers = ["
                    for layer in layerList:
                        layer_var = f"{layer.name}_{layer.purpose}"
                        purposeString += f" {layer_var},"
                        pdkAllLayerString += f" {layer_var},"
                    purposeString += " ]\n"
                    file.write(purposeString)
            
            pdkAllLayerString += " ]\n"
            file.write(pdkAllLayerString)
            
            logger.info(f"Successfully processed {len(layout_layers)} layers")
            if skipped_layers > 0:
                logger.warning(f"Skipped {skipped_layers} layers due to errors")
        
        # Process dither patterns
        process_dither_patterns(root, lypFileObj)
        
        return True
        
    except Exception as e:
        logger.error(f"Fatal error processing LYP file '{lypFile}': {e}")
        return False


def process_dither_patterns(root, lypFileObj: Path) -> None:
    """Process custom dither patterns from the LYP file."""
    try:
        for ditherPattern in root.iterfind("custom-dither-pattern"):
            for orderItem in ditherPattern.iterfind("order"):
                fileName = f"C{orderItem.text}.txt"
                fileObj = lypFileObj.parent.joinpath(fileName)
                
                with fileObj.open("w", encoding="utf-8") as patternFile:
                    for pattern in ditherPattern.findall("pattern"):
                        for lineItem in pattern.iterfind("line"):
                            if lineItem.text:
                                patternFile.write(
                                    f"{lineItem.text.replace('.','0 ').replace('*','1 ')}\n"
                                )
                
                # Generate PNG file
                imageFileObj = fileObj.with_suffix(".png")
                try:
                    stippleEditW = stippleEditor(None)
                    stippleEditW.loadPatternFromFile(str(fileObj))
                    stippleEditW.imageExportToFile(str(imageFileObj))
                except Exception as e:
                    logger.warning(f"Failed to generate PNG for pattern {fileName}: {e}")
                    
    except Exception as e:
        logger.error(f"Error processing dither patterns: {e}")
