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
import pathlib
import re

class verilogaC:
    """
    This class represents an imported verilog-A module.
    """

    def __init__(self, pathObj: pathlib.Path):
        """
        Initialize the class with a given path object.

        Args:
            pathObj (pathlib.Path): The path object representing the file to be processed.
        """
        self._pathObj = pathObj
        self._vaModule = ""
        self.instanceParams = dict()
        self.modelParams = dict()
        self._pins = list()
        self.inPins = list()
        self.inoutPins = list()
        self.outPins = list()
        self._netlistLine = ""
        self.statementLines = list()
        self._pinOrder = ""

        with open(self._pathObj) as f:
            self.fileLines = f.readlines()

        self.findPinsParams(self.oneLiners(self.stripComments()))

    def stripComments(self) -> list:
        """
        Strip comments from the file lines and store the non-comment lines in the statementLines list.
        """

        statementLines = []
        comment = False
        for line in self.fileLines:
            # Concatenate the lines until it reaches a ';'
            stripLine = line.strip()

            if stripLine.startswith("/*"):
                # Set comment to True if the line starts with '/*'
                comment = True

            if not comment:
                doubleSlashLoc = stripLine.find("//")
                if doubleSlashLoc > -1:
                    # Remove single-line comments starting from '//'
                    stripLine = stripLine[:doubleSlashLoc]

                if stripLine:
                    # Add non-empty lines to statementLines list
                    statementLines.append(stripLine)

            if comment and stripLine.endswith("*/"):
                # Set comment to False if the line ends with '*/'
                comment = False

        return statementLines

    def oneLiners(self, statementLines: list):
        """
        Convert the statement lines into one-liners.
        """
        tempLine = ""
        oneLiners = list()
        for line in statementLines:
            stripLine = line.strip()
            if not stripLine.startswith("`include"):
                tempLine = f"{tempLine} {stripLine}"
                if tempLine.endswith(";"):
                    oneLiners.append(tempLine.strip())
                    tempLine = ""
        return oneLiners

    def findPinsParams(self, filteredLines: list):
        for line in filteredLines:
            splitLine = line.strip().split(" ", 1)
            match splitLine[0].lower():
                case "module":
                    if "(" in splitLine[1]:
                        self._vaModule = splitLine[1].split("(")[0]
                    else:
                        self._vaModule = splitLine[1].replace(";", "").strip()
                    if "(" in splitLine[1] and ")" in splitLine[1]:
                        pinList = line.split("(")[1].split(")")[0].split(",")
                        self._pins = [pin.strip() for pin in pinList]
                    else:
                        self._pins = []
                case "in":
                    rawPins = line.replace("in ", "").replace(";", "").split(",")
                    self.inPins.extend([pin.strip() for pin in rawPins])
                case "input":
                    rawPins = line.replace("input ", "").replace(";", "").split(",")
                    self.inPins.extend([pin.strip() for pin in rawPins])
                case "out":
                    rawPins = line.replace("out ", "").replace(";", "").split(",")
                    self.outPins.extend([pin.strip() for pin in rawPins])
                case "output":
                    rawPins = line.replace("output ", "").replace(";", "").split(",")
                    self.outPins.extend([pin.strip() for pin in rawPins])
                case "inout":
                    rawPins = line.replace("inout ", "").replace(";", "").split(",")
                    self.inoutPins.extend([pin.strip() for pin in rawPins])
                case "parameter":
                    paramDefPart = (
                        line.replace("parameter", "").replace(";", "").split("*(")[0]
                    )
                    paramName = paramDefPart.split("=")[0].split()[-1].strip()
                    paramValue = paramDefPart.split("=")[1].split()[0].strip()
                    if "(*" in line:
                        paramAttr = line.strip().split("(*")[1]
                    else:
                        paramAttr = ""
                    if "type" in paramAttr and '"instance"' in paramAttr:
                        # parameter value is between = and (*
                        self.instanceParams[paramName] = paramValue
                        if "xyceAlsoModel" in paramAttr and '"yes"' in paramAttr:
                            self.modelParams[paramName] = paramValue
                    else:  # no parameter attribute statement
                        self.modelParams[paramName] = paramValue

    @property
    def pathObj(self):
        return self._pathObj

    @pathObj.setter
    def pathObj(self, value: pathlib.Path):
        assert isinstance(value, pathlib.Path)
        self._pathObj = value

    @property
    def pinOrder(self):
        # Join the pins with commas
        self._pinOrder = ", ".join(self._pins)
        return self._pinOrder

    @pinOrder.setter
    def pinOrder(self, value: str):
        assert isinstance(value, str)
        self._pinOrder = value

    @property
    def netlistLine(self):

        # Create a string of instance parameters in the format [@key:key=%:key=item]
        instParamString = " ".join(
            [
                f"[@{key}:{key}=%:{key}={item}]"
                for key, item in self.instanceParams.items()
            ]
        )

        # Create the netlist line string with the formatted values
        self._netlistLine = f"Y{self._vaModule} @instName %pinOrder  {self._vaModule}Model {instParamString}"

        # Return the netlist line
        return self._netlistLine

    @property
    def vaModule(self):
        return self._vaModule

class spiceC:
    def __init__(self, pathObj: pathlib.Path):
        self._pathObj = pathObj
        self._pins = []
        self._pinOrder = ""
        with self._pathObj.open("r", encoding="utf-8") as f:
            self._fileLines = f.readlines()
        self.subcktParams = self.extractSubcktParams()
        self._netlistLine = ""

    @property
    def pinOrder(self):
        self._pinOrder = ", ".join(self._pins)
        return self._pinOrder

    @property
    def netlistLine(self):
        instParamString = " ".join(
            [f"[@{k}:{k}=%:{k}={v}]" for k, v in self.subcktParams.get("params", {}).items()]
        )
        name = self.subcktParams.get("name", "")
        if instParamString.strip():
            self._netlistLine = f'X@instName %pinOrder {name} PARAM: {instParamString}'
        else:
            self._netlistLine = f'X@instName %pinOrder {name}'
        return self._netlistLine

    def subcktLineExtract(self):
        subcktLines = ""
        for lineno, line in enumerate(self._fileLines):
            if line.lstrip().upper().startswith('.SUBCKT'):
                subcktLines = line.strip()
                for cont in self._fileLines[lineno+1:]:
                    if cont.lstrip().startswith('+'):
                        subcktLines = f"{subcktLines} {cont.lstrip()[1:].strip()}"
                        continue
                    break
                break
        return subcktLines

    def extractSubcktParams(self):
        subcktDict = {"params": {}}
        subcktLine = self.subcktLineExtract()
        if not subcktLine:
            subcktDict["name"] = ""
            subcktDict["pins"] = []
            self._pins = []
            self._pinOrder = ""
            return subcktDict
        tokens = subcktLine.split()
        if len(tokens) < 2:
            subcktDict["name"] = ""
            subcktDict["pins"] = []
            self._pins = []
            self._pinOrder = ""
            return subcktDict
        subcktDict["name"] = tokens[1]
        cap = subcktLine.upper()
        if 'PARAM:' in cap:
            param_index = cap.split().index('PARAM:')
            subcktDict['pins'] = tokens[2:param_index]
            params_tokens = tokens[param_index+1:]
            params_string = ' '.join(params_tokens)
            for m in re.finditer(r'([A-Za-z_][\w]*)\s*=\s*([^\s]+)', params_string):
                subcktDict['params'][m.group(1)] = m.group(2)
        else:
            subcktDict['pins'] = tokens[2:]
        self._pins = [p.strip() for p in subcktDict['pins'] if p.strip()]
        self._pinOrder = ','.join(self._pins)
        return subcktDict

    @property
    def pathObj(self):
        return self._pathObj
