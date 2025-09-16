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
import os
import importlib
from dotenv import load_dotenv
import pathlib
import sys
load_dotenv()

def importPDKModule(moduleName):
    pdkPath = os.environ.get("REVEDA_PDK_PATH",'./defaultPDK')
    pdkPathObj = pathlib.Path(pdkPath).resolve()
    if pdkPathObj.exists():
        pdkPathParentObj = pdkPathObj.resolve().parent
        pdkPathParentStr = str(pdkPathParentObj)
        if pdkPathParentStr not in sys.path:
            sys.path.append(pdkPathParentStr)
        fullModuleName = f"{pdkPathObj.name}.{moduleName}"
        return importlib.import_module(fullModuleName)
    else:
        pdkPath = "./defaultPDK"
        pdkPathObj = pathlib.Path(pdkPath).resolve()
        pdkPathParentObj = pdkPathObj.resolve().parent
        pdkPathParentStr = str(pdkPathParentObj)
        sys.path.append(pdkPathParentStr)
        fullModuleName = f"{pdkPathObj.name}.{moduleName}"
        return importlib.import_module(fullModuleName)

