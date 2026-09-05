import sys
import os
import fitz

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # EXE: resources лежит рядом с EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # Запуск через Python/VS Code
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

class HistoryManager:
    def __init__(self, parent_module):
        self.parent = parent_module
        self.history = []
        self.index = -1

        # Путь к иконкам
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "resources",
            "icon"
        )

        # Кнопка Отменить действие
        self.btn_undo = QPushButton()
        self.btn_undo.setIcon(QIcon(resource_path("resources/icon/undo.png"
        )))
        self.btn_undo.setIconSize(QSize(23, 23))
        self.btn_undo.setToolTip("Отменить действие")
        self.btn_undo.clicked.connect(self.undo)

        # Кнопка Вернуть действие
        self.btn_redo = QPushButton()
        self.btn_redo.setIcon(QIcon(resource_path("resources/icon/redo.png"
        )))
        self.btn_redo.setIconSize(QSize(23, 23))
        self.btn_redo.setToolTip("Вернуть действие")
        self.btn_redo.clicked.connect(self.redo)

    def save_state(self):
        if not self.parent.doc:
            return

        # Удаляем историю после текущего состояния
        self.history = self.history[:self.index + 1]

        # Сохраняем текущее состояние PDF
        self.history.append(self.parent.doc.write())
        self.index += 1

    def undo(self):
        if self.index > 0:
            self.index -= 1
            self.load_state()

    def redo(self):
        if self.index < len(self.history) - 1:
            self.index += 1
            self.load_state()

    def load_state(self):
        if self.index < 0:
            return

        pdf_bytes = self.history[self.index]

        # Безопасное закрытие текущего документа
        if self.parent.doc:
            self.parent.doc.close()
            self.parent.doc = None

        # Загружаем сохранённое состояние
        self.parent.doc = fitz.open("pdf", pdf_bytes)

        # Обновляем открытый документ
        if self.parent.current_file_path:
            self.parent.open_docs[
                self.parent.current_file_path
            ] = self.parent.doc

        # Проверяем активную страницу
        self.parent.active_page_index = min(
            self.parent.active_page_index,
            len(self.parent.doc) - 1
        )

        # Перерисовываем документ
        self.parent.render_all()
        self.parent.update_page_info()