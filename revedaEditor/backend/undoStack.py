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


from PySide6.QtCore import QPoint
from PySide6.QtGui import QUndoCommand, QUndoStack
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem
import revedaEditor.common.shapes as shp
import revedaEditor.common.layoutShapes as lshp
from typing import List, Tuple, Sequence, Union

class undoStack(QUndoStack):
    def __init__(self):
        super().__init__()

    def removeLastCommand(self):
        # Remove the last command without undoing it
        if self.canUndo():
            self.setIndex(self.index() - 1)


class addShapeUndo(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, shape: QGraphicsItem):
        super().__init__()
        self._scene = scene
        self._shape = shape
        self.setText("Draw Shape")

    def undo(self):
        self._scene.removeItem(self._shape)

    def redo(self):
        self._scene.addItem(self._shape)

class addDeleteShapesUndo(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, newShapes: List[QGraphicsItem], oldShapes: List[QGraphicsItem]):
        super().__init__()
        self._scene = scene
        self._newShapes = newShapes
        self._oldShapes = oldShapes
        self.setText("Add/Delete Shapes")

    def undo(self):
        for item in self._newShapes:
            self._scene.removeItem(item)
        for item in self._oldShapes:
            self._scene.addItem(item)

    def redo(self):
        for item in self._newShapes:
            self._scene.addItem(item)
        for item in self._oldShapes:
            self._scene.removeItem(item)

class addShapesUndo(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, shapes: List[QGraphicsItem]):
        super().__init__()
        self._scene = scene
        self._shapes = shapes
        self.setText("Add Shapes")

    def undo(self):
        for item in self._shapes:
            self._scene.removeItem(item)

    def redo(self):
        for item in self._shapes:
            self._scene.addItem(item)


class loadShapesUndo(addShapesUndo):
    """
    A hack to load the file but disallow the undo
    """

    def __init__(self, scene: QGraphicsScene, shapes: list[QGraphicsItem]):
        super().__init__(scene, shapes)

    def undo(self):
        pass


class deleteShapeUndo(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, shape: QGraphicsItem):
        super().__init__()
        self._scene = scene
        self._shape = shape
        self.setText("Delete Shape")

    def undo(self):
        self._scene.addItem(self._shape)

    def redo(self):
        self._scene.removeItem(self._shape)

class deleteShapesUndo(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, shapes: list[QGraphicsItem]):
        super().__init__()
        self._scene = scene
        self._shapes = shapes
        self.setText("Delete Shapes")

    def undo(self):
        [self._scene.addItem(item) for item in self._shapes]

    def redo(self):
        [self._scene.removeItem(item) for item in self._shapes]

class addDeleteShapeUndo(QUndoCommand):
    def __init__(
        self, scene: QGraphicsScene, addShape: QGraphicsItem, deleteShape: QGraphicsItem
    ):
        super().__init__()
        self._scene = scene
        self._addshape = addShape
        self._deleteShape = deleteShape
        self.setText("Add/Delete Shape")

    def undo(self):
        self._scene.removeItem(self._addshape)
        self._scene.addItem(self._deleteShape)

    def redo(self):
        self._scene.addItem(self._addshape)
        self._scene.removeItem(self._deleteShape)

class addDeleteNetUndo(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, addNet: QGraphicsItem, deleteNet: QGraphicsItem):
        super().__init__()
        self._scene = scene
        self._addNet = addNet
        self._deleteNet = deleteNet
        self.setText("Add/Delete Net")

    def undo(self):
        self._scene.removeItem(self._addNet)
        self._scene.addItem(self._deleteNet)

    def redo(self):
        self._scene.addItem(self._addNet)
        self._scene.removeItem(self._deleteNet)

class updateSymUndo(QUndoCommand):
    def __init__(self, item: QGraphicsItem, oldItemList: list, newItemList: list):
        super().__init__()
        self._item = item
        self._oldItemList = oldItemList
        self._newItemList = newItemList
        self.setText("Update Symbol undo")

    def undo(self):
        pass

    def redo(self):
        pass


class moveShapeUndo(QUndoCommand):
    def __init__(
        self,
        scene,
        item: QGraphicsItem,
        attribute: str,
        oldPosition: QPoint,
        newPosition: QPoint,
    ):
        self._scene = scene
        self._item = item
        self._attribute = attribute
        self._oldPosition = oldPosition
        self._newPosition = newPosition
        self.setText('move shape undo')

    def undo(self):
        setattr(self._item, self._attribute, self._oldPosition)

    def redo(self):
        setattr(self._item, self._attribute, self._newPosition)


class undoRotateShape(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, shape: Union[shp.symbolShape, lshp.layoutShape],
                 point:QPoint,
                 angle:int):
        super().__init__()
        self._scene = scene
        self._shape = shape
        self._point = point
        self._angle = angle
        self.setText("Undo Shape rotation")

    def undo(self) -> None:
        # self._shape.setRotation(self._angle - 90)
        rotationOriginPoint = self._shape.mapFromScene(self._point)
        self._shape.setTransformOriginPoint(rotationOriginPoint)
        self._shape.angle -= self._angle

    def redo(self) -> None:
        rotationOriginPoint = self._shape.mapFromScene(self._point)
        self._shape.setTransformOriginPoint(rotationOriginPoint)
        self._shape.angle += self._angle

class undoMoveShapesCommand(QUndoCommand):
    def __init__(self, shapes: Sequence[QGraphicsItem],
                 startPos: QPoint, endPos: QPoint):
        super().__init__()
        self._shapes = shapes
        self._startPos = startPos
        self._endPos = endPos
        self.setText('undo move shapes')

    def undo(self) -> None:
        for shape in self._shapes:
            shape.setPos(self._startPos + shape.offset)


    def redo(self) -> None:
        for shape in self._shapes:
            shape.setPos(self._endPos + shape.offset)


class undoMoveByCommand(QUndoCommand):
    def __init__(self, scene, items: List, dx: float, dy: float, description: str = "Move Items"):
        super().__init__(description)
        self.scene = scene
        self.items = items
        self.dx = dx
        self.dy = dy
        self.oldPositions: List[Tuple[QPoint, QPoint]] = []
        self.setText('undo move by command')

    def redo(self):
        for item in self.items:
            oldPos = item.pos()
            newPos = oldPos + QPoint(self.dx, self.dy)
            self.oldPositions.append((item, oldPos))
            item.setPos(newPos)

    def undo(self):
        for item, oldPos in self.oldPositions:
            item.setPos(oldPos)