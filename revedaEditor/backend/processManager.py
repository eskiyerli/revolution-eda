# SPDX-License-Identifier: MPL-2.0
#
# Copyright (c) 2024-2026 Revolution Semiconductor (Registered in the Netherlands)
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this file, You can obtain one at
# https://mozilla.org/MPL/2.0/.
#
# Add-ons and extensions developed for this software may be distributed
# under their own separate licenses.

from collections import deque
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QObject, QProcess, Slot
from PySide6.QtGui import QWindow


@dataclass
class Process:
    program: str
    arguments: List
    outputFile: str = ""
    process: QProcess = None
    id: int = 0


class ProcessManager(QObject):
    def __init__(self, max_processes=3, parent=None):
        super().__init__()
        self._maxProcesses = max_processes
        self.parent = parent
        self.process_queue = deque()
        self.running_processes = []
        self.processCounter = 0

    def add_process(self, program, arguments, outputFile=None):
        # print(f'program: {program}, arguments: {arguments}, outputFile: {outputFile}')
        self.processCounter += 1
        if outputFile:
            processItem = Process(program=program, arguments=arguments,
                                  outputFile=outputFile)
        else:
            processItem = Process(program=program, arguments=arguments)
        self.process_queue.append(processItem)
        self.start_next_process()
        return processItem

    def start_next_process(self):
        if len(self.running_processes) < self._maxProcesses and self.process_queue:
            processItem = self.process_queue.popleft()
            processItem.process = QProcess(self)
            processItem.process.setProgram(processItem.program)
            processItem.process.setArguments(processItem.arguments)
            if processItem.outputFile:
                processItem.process.setStandardOutputFile(processItem.outputFile)
            processItem.id = f'{processItem.arguments[-1]}_{self.processCounter}'
            processItem.process.readyReadStandardOutput.connect(lambda: self.handle_output(
                processItem.process))
            processItem.process.finished.connect(self.process_finished)
            processItem.process.start()
            self.running_processes.append(processItem)

    @Slot(int, QProcess.ExitStatus)
    def process_finished(self, exit_code, exit_status):
        finishedProcess = self.sender()
        processItem = next(
            (item for item in self.running_processes if item.process == finishedProcess),
            None)
        self.running_processes.remove(processItem)
        processItem.process.deleteLater()
        self.start_next_process()
        self.parent.logger.info(f"Process {processItem.id} finished.")

    @Slot(QProcess)
    def handle_output(self, process):
        output = process.readAllStandardOutput().data().decode("utf-8").strip()
        for line in output.split("\n"):
            self.parent.logger.info(line)

    def stop_all(self):
        for processItem in self.running_processes:
            processItem.process.terminate()
        self.process_queue.clear()

    @property
    def maxProcesses(self):
        return self._maxProcesses

    @maxProcesses.setter
    def maxProcesses(self, value: int):
        if isinstance(value, int):
            self._maxProcesses = value


class ProcessRunner():
    def __init__(self, parent: QWindow, program: str, arguments: List[str]):
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(lambda: self.handle_output)
        self.process.finished.connect(self.process_finished)
        self.process.readyReadStandardError.connect(lambda: self.handle_error)
        self.process.setProgram(program)
        self.process.setArguments(arguments)
        self.parent = parent
        self.process.start()
        self.process.waitForFinished()

    def handle_output(self, process):
        output = process.readAllStandardOutput().data().decode("utf-8").strip()
        for line in output.split("\n"):
            self.parent.logger.info(line)

    def handle_error(self, process):
        output = process.readAllStandardError().data().decode("utf-8").strip()
        for line in output.split("\n"):
            self.parent.logger.info(line)

    def process_finished(self, exit_code, exit_status):
        self.parent.logger.info(
            f"Process finished with exit code {exit_code} and status {exit_status}")
