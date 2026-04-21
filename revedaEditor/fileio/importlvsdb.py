from PySide6.QtGui import (QBrush, QColor, QPen)
from PySide6.QtCore import (QRect, Qt)
from PySide6.QtWidgets import QGraphicsRectItem
import re
from typing import List, Dict, Any, Optional, Iterator, Tuple
# from revedaEditor.backend.pdkLoader import importPDKModule

class LVSErrorRect(QGraphicsRectItem):
    def __init__(self, rect: QRect) -> None:
        super().__init__(rect)
        self.lvsRect = rect
        # self.setBrush(QBrush(QColor(255, 0, 0, 100)))
        self.setZValue(100)
        # self.setOpacity(0.3)
        # self.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
        self._cell = ""

    def __repr__(self) -> str:
        return f"LVSErrorRect({self.lvsRect})"

    def __str__(self) -> str:
        return f"LVSErrorRect({self.lvsRect})"

    @property
    def cell(self):
        return self._cell

    @cell.setter
    def cell(self, value: str):
        self._cell = value


class LVSDBParser:
    """
    Parses KLayout .lvsdb files into Python structures for Revolution EDA.
    Handles the S-expression format and extracts Layers, Nets, Devices,
    Schematic views, and Cross-reference mappings.

    When pdk_module is provided, resolves GDS layers to PDK layer names
    using the PDK's layer definitions (e.g., layoutLayers.py).
    """

    def __init__(self, filepath: str, pdk_module=None):
        """
        Initialize the LVSDB parser.

        Args:
            filepath: Path to the .lvsdb file to parse.
            pdk_module: Optional PDK module with layer definitions (e.g., layoutLayers).
                        When provided, enables resolution of GDS layer numbers to PDK layer names.

        Attributes:
            layer_map: Mapping from LVSDB internal layer IDs to GDS strings (layer/datatype).
            gds_to_pdk: Mapping from (gdsLayer, datatype) tuples to PDK layer names.
            data: Raw parsed S-expression data from the file.
            layout_cells: Cache of parsed layout cell data.
            schematic_cells: Cache of parsed schematic cell data.
            crossrefs: Cross-reference mappings between layout and schematic cells.
        """
        self.filepath = filepath
        self.pdk = pdk_module
        self.layer_map: Dict[str, Optional[str]] = {}  # lvsdb_id -> gds_string
        self.gds_to_pdk: Dict[Tuple[int, int], str] = {}  # (layer, datatype) -> pdk_name
        self.unit_scale: float = 1.0
        self.data: List[Any] = []
        self.layout_cells: Dict[str, Dict] = {}
        self.schematic_cells: Dict[str, Dict] = {}
        self.crossrefs: Dict[str, Dict] = {}

        if pdk_module:
            self._build_gds_lookup()

    def tokenize(self, text: str) -> Iterator[str]:
        """
        Tokenize the Lisp-like S-expression format.

        Splits the input text into tokens including parentheses, quoted strings,
        and unquoted atoms. Handles both single and double quotes.

        Args:
            text: The S-expression text to tokenize.

        Yields:
            Individual tokens as strings (e.g., '(', ')', 'cell_name', '"quoted string"').
        """
        # Handle both single and double quotes, including empty strings
        token_pattern = r'\(|\)|"([^"]*)"|\'([^\']*)\'|[^\s()\'"]+'
        for match in re.finditer(token_pattern, text):
            yield match.group(0)

    def parse_expression(self, tokens):
        """
        Recursively build a tree from tokens.

        Parses a parenthesized S-expression into a nested list structure.
        Handles nested expressions by recursively parsing content within parentheses.

        Args:
            tokens: Iterator of tokens from tokenize().

        Returns:
            Nested list representing the parsed S-expression tree.
        """
        res = []
        for token in tokens:
            if token == '(':
                res.append(self.parse_expression(tokens))
            elif token == ')':
                return res
            else:
                # Remove quotes if present
                if (token.startswith("'") and token.endswith("'")) or \
                   (token.startswith('"') and token.endswith('"')):
                    token = token[1:-1]
                res.append(token)
        return res

    def load(self):
        """
        Load and parse the LVSDB file.

        Reads the file, strips the header, tokenizes the S-expression content,
        and builds the parse tree. After loading, processes layer mappings
        and cross-reference sections.

        Returns:
            The parsed data structure (list of S-expressions).

        Raises:
            FileNotFoundError: If the filepath does not exist.
            IOError: If the file cannot be read.
        """
        with open(self.filepath, 'r') as f:
            content = f.read()
            # Skip the header #%lvsdb-klayout
            content = re.sub(r'^#%lvsdb-klayout', '', content).strip()
            # Wrap in extra parens so all top-level sections are parsed as one list
            tokens = self.tokenize('(' + content + ')')
            result = self.parse_expression(tokens)
            # Unwrap the outer list to get [tag, content, tag, content, ...]
            self.data = result[0] if (isinstance(result, list) and len(result) == 1) else result

        self._process_units()
        self._process_layers()
        self._process_crossrefs()
        return self.data

    def _process_units(self):
        """
        Extract layout database unit scale from the J section.

        KLayout LVSDB stores a scalar U(value) in the layout section. We keep
        this metadata for consumers that need physical conversion, but parser
        geometry is kept in raw LVSDB coordinates to match editor scene units.
        """
        self.unit_scale = 1.0
        for i in range(len(self.data)):
            if self.data[i] == 'J' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                for j in range(len(section)):
                    if section[j] == 'U' and j + 1 < len(section):
                        item = section[j + 1]
                        if isinstance(item, list) and len(item) >= 1:
                            try:
                                self.unit_scale = float(item[0])
                            except (ValueError, TypeError):
                                self.unit_scale = 1.0
                        return

    def _process_crossrefs(self):
        """
        Extract cross-reference mappings from the Z section.

        The Z section contains equivalence information between layout and schematic
        cells, including net, pin, and device mappings. Populates self.crossrefs
        with mappings for each cell.

        Cross-reference format: X(cell_name schematic_name equiv mapping...)
        where mapping contains net, pin, and device correspondences.
        """
        for i in range(len(self.data)):
            if self.data[i] == 'Z' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                # Z section has tag-pair format: X, (content), X, (content)...
                for j in range(0, len(section), 2):
                    tag = self._safe_get(section, j)
                    if tag != 'X' or j + 1 >= len(section):
                        continue
                    item = section[j + 1]
                    if not isinstance(item, list) or len(item) < 3:
                        continue
                    cell_name = self._safe_get(item, 0)
                    schematic_name = self._safe_get(item, 1)
                    equiv = self._safe_get(item, 2)
                    # Remaining items are the mapping content (in tag-pair format)
                    mapping = self._parse_crossref_mapping(item[3:])
                    self.crossrefs[cell_name] = {
                        'schematic_name': schematic_name,
                        'equivalent': equiv == '1',
                        'mapping': mapping
                    }

    def _parse_crossref_mapping(self, mapping_items: List) -> Dict:
        """
        Parse the Z section mapping block with tag-pair format.

        Extracts net, pin, and device mappings from the cross-reference section.
        The mapping uses a tag-pair format where tags (N, P, D) are followed by
        content lists describing the correspondence.

        Args:
            mapping_items: List of tag-content pairs from the Z section.

        Returns:
            Dictionary with keys 'nets', 'pins', 'devices', each containing
            a list of mapping dictionaries with layout/schematic correspondences
            and status information.
        """
        mapping = {
            'nets': [],
            'pins': [],
            'devices': []
        }
        # mapping_items is in tag-pair format: Z, (content), ...
        for i in range(0, len(mapping_items), 2):
            tag = self._safe_get(mapping_items, i)
            if tag != 'Z' or i + 1 >= len(mapping_items):
                continue
            content = mapping_items[i + 1]
            if not isinstance(content, list):
                continue

            # Content is also in tag-pair format: N, (l s st), N, (l s st), P, ..., D, ...
            for j in range(0, len(content), 2):
                subtag = self._safe_get(content, j)
                if j + 1 >= len(content):
                    continue
                subcontent = content[j + 1]
                if not isinstance(subcontent, list):
                    continue

                if subtag == 'N' and len(subcontent) >= 2:
                    mapping['nets'].append({
                        'layout_net': self._safe_get(subcontent, 0),
                        'schem_net': self._safe_get(subcontent, 1),
                        'status': self._safe_get(subcontent, 2)
                    })
                elif subtag == 'P' and len(subcontent) >= 2:
                    mapping['pins'].append({
                        'layout_pin': self._safe_get(subcontent, 0),
                        'schem_pin': self._safe_get(subcontent, 1),
                        'status': self._safe_get(subcontent, 2)
                    })
                elif subtag == 'D' and len(subcontent) >= 2:
                    mapping['devices'].append({
                        'layout_dev': self._safe_get(subcontent, 0),
                        'schem_dev': self._safe_get(subcontent, 1),
                        'status': self._safe_get(subcontent, 2)
                    })
        return mapping

    def get_all_layout_cells(self) -> List[str]:
        """
        Return list of all layout cell names.

        Scans the J (layout) section of the parsed data to extract all
        cell names defined in the layout view.

        Returns:
            List of layout cell name strings.
        """
        cells = []
        for i in range(len(self.data)):
            if self.data[i] == 'J' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                # J section has alternating tag/content pairs
                for j in range(len(section)):
                    if section[j] == 'X' and j + 1 < len(section):
                        item = section[j + 1]
                        if isinstance(item, list) and len(item) >= 1:
                            cells.append(item[0])
        return cells

    def get_all_schematic_cells(self) -> List[str]:
        """
        Return list of all schematic cell names.

        Scans the H (schematic/circuit) section of the parsed data to extract
        all cell names defined in the schematic view.

        Returns:
            List of schematic cell name strings.
        """
        cells = []
        for i in range(len(self.data)):
            if self.data[i] == 'H' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                # H section has alternating tag/content pairs
                for j in range(len(section)):
                    if section[j] == 'X' and j + 1 < len(section):
                        item = section[j + 1]
                        if isinstance(item, list) and len(item) >= 1:
                            cells.append(item[0])
        return cells

    def _safe_get(self, lst: List, idx: int, default: Any = None) -> Any:
        """
        Safely get an item from a list with bounds checking.

        Helper method to safely access list elements without raising IndexError.
        Also handles cases where the input is not a list.

        Args:
            lst: The list to access.
            idx: The index to retrieve.
            default: Value to return if index is out of bounds or lst is not a list.

        Returns:
            The item at index idx, or default if out of bounds.
        """
        if not isinstance(lst, list):
            return default
        return lst[idx] if 0 <= idx < len(lst) else default

    def _build_gds_lookup(self):
        """
        Build reverse lookup from (gdsLayer, datatype) to PDK layer name.

        Scans the PDK module for layLayer objects (objects with gdsLayer and
        datatype attributes) and builds a lookup dictionary. This enables
        resolution of GDS layer numbers to human-readable PDK layer names.

        Populates self.gds_to_pdk with (gdsLayer, datatype) -> pdk_name mappings.
        """
        if not self.pdk:
            return
        # Scan PDK module for layLayer objects
        for attr_name in dir(self.pdk):
            attr = getattr(self.pdk, attr_name)
            # Check if it's a layLayer-like object with gdsLayer and datatype
            if hasattr(attr, 'gdsLayer') and hasattr(attr, 'datatype'):
                gds_layer = getattr(attr, 'gdsLayer')
                datatype = getattr(attr, 'datatype')
                if gds_layer is not None and datatype is not None:
                    # Also get the name if available
                    name = getattr(attr, 'name', attr_name)
                    self.gds_to_pdk[(int(gds_layer), int(datatype))] = name

    def _get_layer_name(self, lvsdb_layer_id: str) -> Optional[str]:
        """Get PDK layer name from LVSDB internal layer ID.

        Resolution order:
        1. Look up lvsdb_id in layer_map -> get GDS string 'layer/datatype'
        2. Parse GDS string to (layer, datatype)
        3. Look up (layer, datatype) in PDK gds_to_pdk -> get PDK name
        4. If no PDK mapping, return GDS string; if no GDS mapping, return lvsdb_id
        """
        # Get GDS string from LVSDB layer map
        gds_str = self.layer_map.get(lvsdb_layer_id)
        if not gds_str:
            # No GDS mapping in LVSDB - return the internal ID
            return lvsdb_layer_id

        # Parse GDS string 'layer/datatype'
        try:
            parts = gds_str.split('/')
            if len(parts) >= 2:
                gds_layer = int(parts[0])
                datatype = int(parts[1])

                # Look up in PDK
                pdk_name = self.gds_to_pdk.get((gds_layer, datatype))
                if pdk_name:
                    return pdk_name

                # No PDK mapping - return GDS string
                return gds_str
        except (ValueError, AttributeError):
            pass

        return lvsdb_layer_id

    def _process_layers(self):
        """
        Extract L(id 'GDS') mappings from the J section into a usable dict.

        The J section contains layer definitions with L tags that map internal
        LVSDB layer IDs to GDS strings in the format 'layer/datatype'.

        Populates self.layer_map with lvsdb_id -> gds_string mappings.
        """
        for i in range(len(self.data)):
            if self.data[i] == 'J' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                # J section has alternating tag/content pairs: W, U, L, C, K, X, ...
                for j in range(len(section)):
                    if section[j] == 'L' and j + 1 < len(section):
                        item = section[j + 1]
                        if isinstance(item, list) and len(item) >= 1:
                            layer_id = item[0]
                            gds = item[1] if len(item) > 1 else None
                            if layer_id:
                                self.layer_map[layer_id] = gds

    def get_nets(self, cell_name: str) -> List[Dict]:
        """
        Return all geometry associated with nets in a specific layout cell.

        Retrieves the parsed net data for a layout cell, including net names
        and associated geometric shapes (rectangles, polygons, labels).

        Args:
            cell_name: Name of the layout cell to query.

        Returns:
            List of net dictionaries, each containing 'net_id', 'name',
            and 'shapes' (list of geometry dictionaries).
        """
        nets = []
        cell_data = self._get_layout_cell(cell_name)
        if cell_data and 'nets' in cell_data:
            return cell_data['nets']
        return nets

    def get_nets_with_schematic_names(self, cell_name: str) -> List[Dict]:
        """
        Return layout nets with schematic net names for easier identification.

        This method returns the same net geometry data as get_nets(), but
        replaces layout net names with their corresponding schematic net names.
        If a layout net has no schematic mapping, the original layout name is kept.

        Args:
            cell_name: Name of the layout cell to query.

        Returns:
            List of net dictionaries with keys:
            - 'net_id': Layout net ID
            - 'name': Schematic net name (or layout name if no mapping exists)
            - 'layout_name': Original layout net name
            - 'shapes': List of geometry dictionaries
        """
        # Get layout nets
        layout_nets = self.get_nets(cell_name)
        if not layout_nets:
            return []

        # Get cross-reference mapping
        xref = self.get_crossref(cell_name)
        if not xref:
            # No cross-reference, return nets with original names
            return [
                {
                    'net_id': net['net_id'],
                    'name': net['name'],
                    'layout_name': net['name'],
                    'shapes': net['shapes']
                }
                for net in layout_nets
            ]

        # Get schematic cell name and schematic nets
        schematic_name = xref.get('schematic_name', cell_name.upper())
        schem_cell_data = self._get_schematic_cell(schematic_name)

        # Build schematic net ID -> schematic net name lookup
        schem_net_id_to_name = {}
        if schem_cell_data and 'nets' in schem_cell_data:
            for net in schem_cell_data['nets']:
                net_id = net.get('net_id')
                net_name = net.get('name', '')
                if net_id:
                    schem_net_id_to_name[net_id] = net_name

        # Build layout net ID -> schematic net ID mapping from crossref
        layout_to_schem_net_id = {}
        for mapping in xref.get('mapping', {}).get('nets', []):
            layout_net_id = mapping.get('layout_net')
            schem_net_id = mapping.get('schem_net')
            if layout_net_id and schem_net_id:
                layout_to_schem_net_id[layout_net_id] = schem_net_id

        # Map each layout net to its schematic name
        result = []
        for net in layout_nets:
            layout_net_id = net['net_id']
            layout_name = net['name']

            # Look up schematic net ID, then schematic net name
            schem_net_id = layout_to_schem_net_id.get(layout_net_id)
            schem_name = schem_net_id_to_name.get(schem_net_id, '') if schem_net_id else ''

            # Use schematic name if available, otherwise keep layout name
            display_name = schem_name if schem_name else layout_name

            result.append({
                'net_id': layout_net_id,
                'name': display_name,
                'layout_name': layout_name,
                'shapes': net['shapes']
            })

        return result

    def get_layout_devices(self, cell_name: str) -> List[Dict]:
        """
        Return all devices in a specific layout cell.

        Retrieves the device data extracted from the LVSDB for a layout cell,
        including device IDs, types, positions, parameters, and terminal mappings.

        Args:
            cell_name: Name of the layout cell to query.

        Returns:
            List of device dictionaries with keys: 'id', 'type', 'position',
            'params', 'terminals', 'subdevices'.
        """
        cell_data = self._get_layout_cell(cell_name)
        if cell_data and 'devices' in cell_data:
            return cell_data['devices']
        return []

    def get_schematic_devices(self, cell_name: str) -> List[Dict]:
        """
        Return all devices from the schematic view of a cell.

        Retrieves device data from the schematic/circuit representation,
        including device names, types, parameters, and terminal net connections.

        Args:
            cell_name: Name of the schematic cell to query.

        Returns:
            List of schematic device dictionaries with keys: 'id', 'type',
            'name', 'params', 'terminals'.
        """
        cell_data = self._get_schematic_cell(cell_name)
        if cell_data and 'devices' in cell_data:
            return cell_data['devices']
        return []

    def get_schematic_nets(self, cell_name: str) -> List[Dict]:
        """
        Return all nets from the schematic view of a cell.

        Retrieves net data from the schematic/circuit representation,
        including net IDs and names.

        Args:
            cell_name: Name of the schematic cell to query.

        Returns:
            List of schematic net dictionaries with keys: 'net_id', 'name'.
        """
        cell_data = self._get_schematic_cell(cell_name)
        if cell_data and 'nets' in cell_data:
            return cell_data['nets']
        return []

    def get_extracted_schematic(self, layout_cell_name: str) -> Optional[Dict]:
        """
        Returns extracted schematic with resolved net names for creating a schematic view.

        Returns dict with:
        - 'name': schematic cell name
        - 'nets': list of {id, name, layout_net_id}  # schematic nets with names resolved
        - 'devices': list of {id, name, type, params, terminals}  # devices with terminal net names
        - 'equivalent': True/False/None  # LVS equivalence status
        """
        xref = self.get_crossref(layout_cell_name)
        if not xref:
            return None

        schematic_name = xref.get('schematic_name', layout_cell_name.upper())
        cell_data = self._get_schematic_cell(schematic_name)
        if not cell_data:
            return None

        # Build net ID -> name lookup from schematic nets
        net_id_to_name = {}
        for net in cell_data.get('nets', []):
            net_id_to_name[net['net_id']] = net.get('name', '')

        # Build layout net ID -> schematic net name mapping from crossref
        layout_to_schem_net = {}
        for mapping in xref.get('mapping', {}).get('nets', []):
            layout_net = mapping.get('layout_net')
            schem_net = mapping.get('schem_net')
            if layout_net and schem_net:
                # schem_net is an ID, look up its name
                layout_to_schem_net[layout_net] = net_id_to_name.get(schem_net, schem_net)

        # Process devices - resolve terminal net IDs to names
        devices = []
        for dev in cell_data.get('devices', []):
            resolved_dev = {
                'id': dev['id'],
                'name': dev.get('name', ''),
                'type': dev['type'],
                'params': dev.get('params', {}),
                'terminals': {}
            }
            # Resolve terminal net IDs to names
            for term_name, net_id in dev.get('terminals', {}).items():
                net_name = net_id_to_name.get(net_id, net_id)
                resolved_dev['terminals'][term_name] = net_name
            devices.append(resolved_dev)

        # Process nets with their layout mapping
        nets = []
        for net in cell_data.get('nets', []):
            net_id = net['net_id']
            net_name = net.get('name', '')
            # Find corresponding layout net
            layout_net_id = None
            for mapping in xref.get('mapping', {}).get('nets', []):
                if mapping.get('schem_net') == net_id:
                    layout_net_id = mapping.get('layout_net')
                    break
            nets.append({
                'id': net_id,
                'name': net_name,
                'layout_net_id': layout_net_id
            })

        return {
            'name': schematic_name,
            'nets': nets,
            'devices': devices,
            'equivalent': xref.get('equivalent')
        }

    def get_crossref(self, cell_name: str) -> Optional[Dict]:
        """
        Return cross-reference mapping between layout and schematic.

        Retrieves the pre-parsed cross-reference data for a cell, which includes
        the schematic cell name, equivalence status, and net/pin/device mappings.

        Args:
            cell_name: Name of the layout cell to query.

        Returns:
            Dictionary with keys 'schematic_name', 'equivalent', 'mapping',
            or None if no cross-reference exists for this cell.
        """
        return self.crossrefs.get(cell_name)

    def get_connectivity(self, layout_cell_name: str) -> Optional[Dict]:
        """
        Return bidirectional connectivity information.

        Builds both device-centric and net-centric views of connectivity:
        - Device-centric: which nets connect to each device terminal
        - Net-centric: which device terminals connect to each net

        Args:
            layout_cell_name: Name of the layout cell to extract connectivity from.

        Returns:
            Dictionary with keys:
            - 'devices': Dict mapping device names to {terminal: net_name} dicts
            - 'nets': Dict mapping net names to [(dev_name, terminal), ...] lists
            - 'netlist': List of (dev_name, type, {terminal: net_name, ...}) tuples
            Returns None if the cell cannot be found or has no extracted schematic.
        """
        extracted = self.get_extracted_schematic(layout_cell_name)
        if not extracted:
            return None

        devices = {}
        nets = {}
        netlist = []

        # Build device-centric view and collect net connections
        for dev in extracted['devices']:
            dev_name = dev['name']
            dev_type = dev['type']
            terminals = dev.get('terminals', {})
            devices[dev_name] = terminals
            netlist.append((dev_name, dev_type, terminals))

            # Build net-centric view
            for term, net_name in terminals.items():
                if net_name not in nets:
                    nets[net_name] = []
                nets[net_name].append((dev_name, term))

        return {
            'devices': devices,
            'nets': nets,
            'netlist': netlist
        }

    def _get_layout_cell(self, cell_name: str) -> Optional[Dict]:
        """
        Get parsed layout cell data, processing if not cached.

        Looks up the cell in the layout cell cache first. If not found,
        searches the J section of the parsed data, parses the cell definition,
        and caches the result.

        Args:
            cell_name: Name of the layout cell to retrieve.

        Returns:
            Dictionary with parsed cell data ('name', 'bbox', 'nets', 'pins', 'devices'),
            or None if the cell is not found.
        """
        if cell_name in self.layout_cells:
            return self.layout_cells[cell_name]

        for i in range(len(self.data)):
            if self.data[i] == 'J' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                # J section has alternating tag/content pairs
                for j in range(len(section)):
                    if section[j] == 'X' and j + 1 < len(section):
                        item = section[j + 1]
                        if isinstance(item, list) and len(item) >= 1 and item[0] == cell_name:
                            cell_data = self._parse_layout_cell(item)
                            self.layout_cells[cell_name] = cell_data
                            return cell_data
        return None

    def _get_schematic_cell(self, cell_name: str) -> Optional[Dict]:
        """
        Get parsed schematic cell data, processing if not cached.

        Looks up the cell in the schematic cell cache first. If not found,
        searches the H section of the parsed data, parses the cell definition,
        and caches the result.

        Args:
            cell_name: Name of the schematic cell to retrieve.

        Returns:
            Dictionary with parsed cell data ('name', 'nets', 'pins', 'devices'),
            or None if the cell is not found.
        """
        if cell_name in self.schematic_cells:
            return self.schematic_cells[cell_name]

        for i in range(len(self.data)):
            if self.data[i] == 'H' and i + 1 < len(self.data):
                section = self.data[i + 1]
                if not isinstance(section, list):
                    continue
                # H section has alternating tag/content pairs
                for j in range(len(section)):
                    if section[j] == 'X' and j + 1 < len(section):
                        item = section[j + 1]
                        if isinstance(item, list) and len(item) >= 1 and item[0] == cell_name:
                            cell_data = self._parse_schematic_cell(item)
                            self.schematic_cells[cell_name] = cell_data
                            return cell_data
        return None

    def _parse_layout_cell(self, cell_list: List) -> Dict:
        """
        Parse an X(cell_name ...) layout cell definition from the J section.

        Layout cells contain a bounding box, nets with geometry, pins, and devices.
        The content is in tag-pair format: R (bbox), N (net), P (pin), D (device).

        Args:
            cell_list: List containing the cell definition starting with cell name.

        Returns:
            Dictionary with keys: 'name', 'bbox', 'nets', 'pins', 'devices'.
        """
        cell_name = self._safe_get(cell_list, 0, '')
        bbox = None
        nets = []
        pins = []
        devices = []

        # Cell content is in tag-pair format: R, (coords), N, (net), P, (pin), D, (dev)...
        for i in range(1, len(cell_list), 2):
            tag = cell_list[i]
            if i + 1 >= len(cell_list):
                continue
            content = cell_list[i + 1]

            if tag == 'R' and isinstance(content, list) and len(content) == 2:
                bbox = self._parse_bbox(content[0], content[1])
            elif tag == 'N' and isinstance(content, list):
                net = self._parse_net([tag] + content)  # Reconstruct as [N, ...]
                if net:
                    nets.append(net)
            elif tag == 'P' and isinstance(content, list):
                pin = self._parse_pin([tag] + content)
                if pin:
                    pins.append(pin)
            elif tag == 'D' and isinstance(content, list):
                device = self._parse_device([tag] + content)
                if device:
                    devices.append(device)

        return {
            'name': cell_name,
            'bbox': bbox,
            'nets': nets,
            'pins': pins,
            'devices': devices
        }

    def _parse_schematic_cell(self, cell_list: List) -> Dict:
        """
        Parse an X(cell_name ...) schematic cell definition from the H section.

        Schematic cells contain nets, pins, and devices in tag-pair format:
        N (net), P (pin), D (device). Unlike layout cells, schematic cells
        do not have geometric bounding boxes.

        Args:
            cell_list: List containing the cell definition starting with cell name.

        Returns:
            Dictionary with keys: 'name', 'nets', 'pins', 'devices'.
        """
        cell_name = self._safe_get(cell_list, 0, '')
        nets = []
        pins = []
        devices = []

        # Cell content is in tag-pair format
        for i in range(1, len(cell_list), 2):
            tag = cell_list[i]
            if i + 1 >= len(cell_list):
                continue
            content = cell_list[i + 1]

            if tag == 'N' and isinstance(content, list):
                net = self._parse_schematic_net([tag] + content)
                if net:
                    nets.append(net)
            elif tag == 'P' and isinstance(content, list):
                pin = self._parse_pin([tag] + content)
                if pin:
                    pins.append(pin)
            elif tag == 'D' and isinstance(content, list):
                device = self._parse_schematic_device([tag] + content)
                if device:
                    devices.append(device)

        return {
            'name': cell_name,
            'nets': nets,
            'pins': pins,
            'devices': devices
        }

    def _parse_bbox(self, min_pt: List, max_pt: List) -> Optional[List[List[float]]]:
        """
        Parse bounding box from two coordinate lists.

        Converts string or numeric coordinates to float and formats as
        a 2x2 bounding box matrix.

        Args:
            min_pt: List of [x, y] coordinates for the minimum corner.
            max_pt: List of [x, y] coordinates for the maximum corner.

        Returns:
            Bounding box as [[xmin, ymin], [xmax, ymax]], or None if parsing fails.
        """
        try:
            # First pair is p1 (written from ref=0,0, so it's absolute).
            # Second pair is the displacement from p1 to p2 (i.e. width/height).
            x0 = float(min_pt[0])
            y0 = float(min_pt[1])
            dx = float(max_pt[0])
            dy = float(max_pt[1])
            x1 = x0 + dx
            y1 = y0 + dy
            return [[min(x0, x1), min(y0, y1)], [max(x0, x1), max(y0, y1)]]
        except (ValueError, IndexError, TypeError):
            return None

    def _parse_pin(self, pin_list: List) -> Optional[Dict]:
        """
        Parse a P(pin_id I(name)) pin definition.

        Pins are defined in tag-pair format with an ID and optional name.

        Args:
            pin_list: List containing pin data: [tag, pin_id, [I, (name)]].

        Returns:
            Dictionary with 'pin_id' and 'name', or None if parsing fails.
        """
        if len(pin_list) < 2:
            return None
        pin_id = self._safe_get(pin_list, 1)
        name = ''
        if len(pin_list) > 2 and isinstance(pin_list[2], list):
            name = self._safe_get(pin_list[2], 1, '')
        return {'pin_id': pin_id, 'name': name}

    def _parse_schematic_net(self, net_list: List) -> Optional[Dict]:
        """
        Parse a schematic net with tag-pair format: N id I(name).

        Schematic nets contain a net ID and optionally a name in I tag format.

        Args:
            net_list: List containing net data: [N, net_id, I, (name), ...].

        Returns:
            Dictionary with 'net_id' and 'name', or None if parsing fails.
        """
        if not isinstance(net_list, list) or len(net_list) < 2:
            return None
        net_id = self._safe_get(net_list, 1)
        name = ''

        # Net content is in tag-pair format starting from index 2
        for i in range(2, len(net_list), 2):
            tag = net_list[i]
            if i + 1 >= len(net_list):
                continue
            content = net_list[i + 1]

            if tag == 'I' and isinstance(content, list) and len(content) >= 1:
                name = content[0]

        return {'net_id': net_id, 'name': name}

    def _parse_schematic_device(self, dev_list: List) -> Optional[Dict]:
        """
        Parse a schematic device with tag-pair format.

        Device format: D id type I(name) E(name val) T(term net) ...
        - I tag: Instance name
        - E tag: Parameters (name-value pairs)
        - T tag: Terminal connections (terminal name -> net ID)

        Args:
            dev_list: List containing device data starting with tag, id, type.

        Returns:
            Dictionary with keys: 'id', 'type', 'name', 'params', 'terminals',
            or None if parsing fails.
        """
        if not isinstance(dev_list, list) or len(dev_list) < 3:
            return None

        device_id = self._safe_get(dev_list, 1)
        device_type = self._safe_get(dev_list, 2)
        name = ''
        params = {}
        terminals = {}

        # Device content is in tag-pair format starting from index 3
        for i in range(3, len(dev_list), 2):
            tag = dev_list[i]
            if i + 1 >= len(dev_list):
                continue
            content = dev_list[i + 1]

            if tag == 'I' and isinstance(content, list) and len(content) >= 1:
                name = content[0]
            elif tag == 'E' and isinstance(content, list) and len(content) >= 2:
                param_name = self._safe_get(content, 0)
                param_value = self._safe_get(content, 1)
                if param_name:
                    params[param_name] = param_value
            elif tag == 'T' and isinstance(content, list) and len(content) >= 2:
                term_name = self._safe_get(content, 0)
                net_id = self._safe_get(content, 1)
                if term_name:
                    terminals[term_name] = net_id

        return {
            'id': device_id,
            'type': device_type,
            'name': name,
            'params': params,
            'terminals': terminals
        }

    def _parse_net(self, net_list: List) -> Optional[Dict]:
        """
        Parse a layout net with tag-pair format.

        Net format: [N, id, I(name), R(layer origin size), Q(layer points...), J(layer text pos)...]
        - I tag: Net name
        - R tag: Rectangle geometry (layer, origin [x,y], size [w,h])
        - Q tag: Polygon geometry (layer, list of [x,y] points)
        - J tag: Text label (layer, text string, position [x,y])

        Args:
            net_list: List containing net data starting with tag and net_id.

        Returns:
            Dictionary with 'net_id', 'name', and 'shapes' (list of geometry dicts),
            or None if parsing fails.
        """
        if not isinstance(net_list, list) or len(net_list) < 2:
            return None

        net_id = self._safe_get(net_list, 1)
        net_name = ""
        geometries = []

        # KLayout LVSDB uses running reference (delta-encoded) coordinates.
        # All R/Q/J shape coordinates are displacements from a running ref
        # that accumulates across all shapes in the net (reset to 0,0 per net).
        ref = [0.0, 0.0]

        for i in range(2, len(net_list), 2):
            tag = net_list[i]
            if i + 1 >= len(net_list):
                continue
            content = net_list[i + 1]

            if tag == 'I' and isinstance(content, list) and len(content) >= 1:
                net_name = content[0]
            elif tag == 'R' and isinstance(content, list) and len(content) >= 3:
                lvsdb_layer_id = content[0]
                try:
                    # First pair: displacement from running ref to p1 (lower-left)
                    dx1, dy1 = float(content[1][0]), float(content[1][1])
                    # Second pair: displacement from p1 to p2 (width, height)
                    dx2, dy2 = float(content[2][0]), float(content[2][1])
                    x0 = ref[0] + dx1
                    y0 = ref[1] + dy1
                    ref = [x0, y0]  # update ref to p1
                    x1 = ref[0] + dx2
                    y1 = ref[1] + dy2
                    ref = [x1, y1]  # update ref to p2
                    bbox = [[min(x0, x1), min(y0, y1)], [max(x0, x1), max(y0, y1)]]
                    geometries.append({
                        "type": "rect",
                        "layer": self._get_layer_name(lvsdb_layer_id),
                        "lvsdb_layer": lvsdb_layer_id,
                        "bbox": bbox
                    })
                except (ValueError, TypeError, IndexError):
                    continue
            elif tag == 'Q' and isinstance(content, list) and len(content) >= 2:
                lvsdb_layer_id = content[0]
                try:
                    points = []
                    # Each vertex encoded as displacement from running ref
                    for pt in content[1:]:
                        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            dx, dy = float(pt[0]), float(pt[1])
                            px = ref[0] + dx
                            py = ref[1] + dy
                            ref = [px, py]
                            points.append([px, py])
                    if points:
                        geometries.append({
                            "type": "polygon",
                            "layer": self._get_layer_name(lvsdb_layer_id),
                            "lvsdb_layer": lvsdb_layer_id,
                            "points": points
                        })
                except (ValueError, TypeError):
                    continue
            elif tag == 'J' and isinstance(content, list) and len(content) >= 3:
                lvsdb_layer_id = content[0]
                label_text = content[1] if len(content) > 1 else ''
                try:
                    pos_raw = content[2]
                    dx, dy = float(pos_raw[0]), float(pos_raw[1])
                    px = ref[0] + dx
                    py = ref[1] + dy
                    ref = [px, py]
                    geometries.append({
                        "type": "label",
                        "layer": self._get_layer_name(lvsdb_layer_id),
                        "lvsdb_layer": lvsdb_layer_id,
                        "text": label_text,
                        "pos": [px, py]
                    })
                except (ValueError, TypeError):
                    continue

        return {
            "net_id": net_id,
            "name": net_name,
            "shapes": geometries
        }
    def _parse_device(self, dev_list: List) -> Optional[Dict]:
        """
        Parse a layout device with tag-pair format.

        Device format: D id type Y(x y) E(name val) T(term net) D(subdevice) C(conn)...
        - id: Device identifier
        - type: Device type (e.g., 'MOS', 'RES', 'CAP')
        - Y tag: Position coordinates [x, y]
        - E tag: Parameters (name-value pairs, value converted to float if possible)
        - T tag: Terminal connections (terminal name -> net ID)
        - D tag: Sub-devices (for hierarchical devices)
        - C tag: Connections between terminals

        Args:
            dev_list: List containing device data starting with tag, id, type.

        Returns:
            Dictionary with keys: 'id', 'type', 'position', 'params', 'terminals', 'subdevices',
            or None if parsing fails.
        """
        if not isinstance(dev_list, list) or len(dev_list) < 3:
            return None

        device_id = self._safe_get(dev_list, 1)
        device_type = self._safe_get(dev_list, 2)
        params = {}
        terminals = {}
        subdevices = []
        position = None

        # Device content is in tag-pair format starting from index 3
        for i in range(3, len(dev_list), 2):
            tag = dev_list[i]
            if i + 1 >= len(dev_list):
                continue
            content = dev_list[i + 1]

            if tag == 'D' and isinstance(content, list):  # Sub-device
                subdev = self._parse_subdevice([tag] + content)
                if subdev:
                    subdevices.append(subdev)
            elif tag == 'C' and isinstance(content, list) and len(content) >= 2:  # Connection
                net_idx = self._safe_get(content, 0)
                term1 = self._safe_get(content, 1)
                term2 = self._safe_get(content, 2)
                terminals[f"conn_{net_idx}"] = {'from': term1, 'to': term2}
            elif tag == 'Y' and isinstance(content, list) and len(content) >= 2:  # Position
                try:
                    position = [float(content[0]), float(content[1])]
                except (ValueError, TypeError):
                    pass
            elif tag == 'E' and isinstance(content, list) and len(content) >= 2:  # Parameter
                param_name = self._safe_get(content, 0)
                param_value = self._safe_get(content, 1)
                if param_name:
                    try:
                        params[param_name] = float(param_value)
                    except (ValueError, TypeError):
                        params[param_name] = param_value
            elif tag == 'T' and isinstance(content, list) and len(content) >= 2:  # Terminal
                term_name = self._safe_get(content, 0)
                net_id = self._safe_get(content, 1)
                if term_name:
                    terminals[term_name] = net_id

        return {
            'id': device_id,
            'type': device_type,
            'position': position,
            'params': params,
            'terminals': terminals,
            'subdevices': subdevices
        }

    def _parse_subdevice(self, subdev_list: List) -> Optional[Dict]:
        """
        Parse a sub-device reference.

        Sub-device format: D(name Y(x y))
        Represents a child device within a hierarchical device structure.

        Args:
            subdev_list: List containing sub-device data: [D, name, Y, (x, y)].

        Returns:
            Dictionary with 'name' and 'transform' (position [x, y]),
            or None if parsing fails.
        """
        if len(subdev_list) < 2:
            return None
        name = self._safe_get(subdev_list, 1)
        transform = None
        for item in subdev_list[2:]:
            if isinstance(item, list) and self._safe_get(item, 0) == 'Y':
                try:
                    transform = [float(item[1]), float(item[2])]
                except (ValueError, TypeError, IndexError):
                    pass
        return {'name': name, 'transform': transform}


if __name__ == '__main__':
    import sys
    print('main')
    if len(sys.argv) < 2:
        print("Usage: python lvsdb_parser.py <lvsdb_file> [cell_name]")
        print("Example: python lvsdb_parser.py opamp.lvsdb opamp")
        print("\nWith PDK (shows layer names instead of GDS numbers):")
        print("  python -c \"import ihp_pdk.layoutLayers as ly; from lvsdb_parser import LVSDBParser; p = LVSDBParser('opamp.lvsdb', ly); p.load() ...\"")
        sys.exit(1)

    filepath = sys.argv[1]
    cell_name = sys.argv[2] if len(sys.argv) > 2 else None

    # Try to import PDK layers for better layer naming
    pdk_module = None
    try:
        # When run from within ihp_pdk package
        from .. import layoutLayers as pdk_module
    except ImportError:
        try:
            # When ihp_pdk is in path
            import layoutLayers as pdk_module
        except ImportError:
            pass
            
    parser = LVSDBParser(filepath, pdk_module)
    parser.load()

    print(f"Layer map ({len(parser.layer_map)} layers):")
    for lid, gds in list(parser.layer_map.items())[:500]:
        print(f"  {lid} -> {gds}")
    if len(parser.layer_map) > 500:
        print(f"  ... and {len(parser.layer_map) - 500} more")

    print(f"\nLayout cells: {parser.get_all_layout_cells()}")
    print(f"Schematic cells: {parser.get_all_schematic_cells()}")

    if cell_name:
        print(f"\n--- Layout: {cell_name} ---")
        nets = parser.get_nets(cell_name)
        print(f"Nets: {len(nets)}")
        for net in nets[:3]:
            print(f"  {net['net_id']}: {net['name']} ({len(net['shapes'])} shapes)")

        devices = parser.get_devices(cell_name)
        print(f"\nDevices: {len(devices)}")
        for dev in devices[:3]:
            print(f"  {dev['id']}: {dev['type']} @ {dev['position']}")

        xref = parser.get_crossref(cell_name)
        if xref:
            print(f"\nCross-reference: {cell_name} <-> {xref['schematic_name']}")
            print(f"  Equivalent: {xref['equivalent']}")
            print(f"  Nets mapped: {len(xref['mapping']['nets'])}")
            print(f"  Devices mapped: {len(xref['mapping']['devices'])}")

        # Show extracted schematic view
        schematic_name = xref['schematic_name'] if xref else cell_name.upper()
        print(f"\n--- Schematic: {schematic_name} ---")
        sch_nets = parser.get_schematic_nets(schematic_name)
        print(f"Schematic Nets: {len(sch_nets)}")
        for net in sch_nets[:5]:
            print(f"  {net['net_id']}: {net['name']}")

        sch_devices = parser.get_schematic_devices(schematic_name)
        print(f"\nSchematic Devices: {len(sch_devices)}")
        for dev in sch_devices[:5]:
            name = dev.get('name', '')
            print(f"  {dev['id']}: {dev['type']} ({name})")

        # Show extracted schematic (ready for creating schematic view)
        extracted = parser.get_extracted_schematic(cell_name)
        if extracted:
            print(f"\n--- Extracted Schematic: {extracted['name']} ---")
            print(f"LVS Equivalent: {extracted['equivalent']}")
            print(f"\nNets ({len(extracted['nets'])}):")
            for net in extracted['nets'][:5]:
                print(f"  {net['id']}: '{net['name']}' (layout: {net['layout_net_id']})")
            print(f"\nDevices ({len(extracted['devices'])}):")
            for dev in extracted['devices'][:15]:
                params = ', '.join([f"{k}={v}" for k, v in list(dev['params'].items())[:3]])
                terms = ', '.join([f"{k}:{v}" for k, v in dev['terminals'].items()])
                print(f"  {dev['name']} ({dev['type']})")
                if params:
                    print(f"    Params: {params}")
                if terms:
                    print(f"    Terminals: {terms}")

        # Show connectivity - which net connects to which device terminal
        conn = parser.get_connectivity(cell_name)
        if conn:
            print(f"\n--- Connectivity for {cell_name} ---")
            print("\nNet-Centric View:")
            for net_name, connections in list(conn['nets'].items())[:10]:
                dev_terms = ', '.join([f"{d}.{t}" for d, t in connections[:4]])
                if len(connections) > 4:
                    dev_terms += f" (+{len(connections)-4} more)"
                print(f"  {net_name}: {dev_terms}")

            print("\nDevice-Centric View:")
            for dev_name, terminals in list(conn['devices'].items())[:10]:
                term_str = ', '.join([f"{t}={n}" for t, n in terminals.items()])
                print(f"  {dev_name}: {term_str}")

        # Show all rectangles for Net 1 (VDD)
        vdd_net = None
        for net in nets:
            # if net['net_id'] == '1' or net['name'] == 'VDD':
            if net['name'] == 'NET1':
                vdd_net = net
                break

        if vdd_net:
            print(f"\n--- Net {vdd_net['net_id']}: {vdd_net['name']} Details ---")
            rects = [s for s in vdd_net['shapes'] if s['type'] == 'rect']
            print(f"Rectangles: {len(rects)}")
            for i, rect in enumerate(rects[:500]):
                bbox = rect['bbox']
                layer = rect['layer'] or rect.get('layer')
                print(f"  {i+1}. Layer {layer}: ({bbox[0][0]}, {bbox[0][1]}) - ({bbox[1][0]}, {bbox[1][1]})")
            if len(rects) > 500:
                print(f"  ... and {len(rects) - 500} more rectangles")
