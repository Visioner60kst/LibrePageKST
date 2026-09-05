import os
import tempfile
import subprocess
from PIL import Image
import io
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt

class ExternalEditorDialog(QDialog):
    def __init__(self, parent_main_window):
        super().__init__(parent_main_window)
        self.main_window = parent_main_window
        self.setWindowTitle("Внешний редактор")
        self.setModal(True)
        self.resize(450, 200)

        self.temp_img_path = None

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Подготовка изображения...", self)
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()

        self.btn_apply = QPushButton("Применить изменения", self)
        self.btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_apply.clicked.connect(self.accept)
        self.btn_apply.setEnabled(False)

        self.btn_cancel = QPushButton("Отмена", self)
        self.btn_cancel.setStyleSheet("padding: 10px;")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

        # Start process automatically
        self.prepare_and_open()

    def prepare_and_open(self):
        # Если путь к редактору не задан или файл больше не существует, просим пользователя выбрать его
        if not getattr(self.main_window, 'external_editor_path', None) or not os.path.exists(self.main_window.external_editor_path):
            editor_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите исполняемый файл редактора (Photoshop, GIMP, Krita, Paint и т.д.)",
                "",
                "Исполняемые файлы (*.exe *.bat *.sh *.app);;Все файлы (*.*)"
            )
            if not editor_path:
                self.info_label.setText("Редактор не выбран. Операция отменена.")
                return
            # Сохраняем путь в основном окне, чтобы не спрашивать каждый раз
            self.main_window.external_editor_path = editor_path

        try:
            # Получаем выделенную область из PDF
            page_index = self.main_window.image_selection_manager.selected_page_index
            bbox = self.main_window.image_selection_manager.selected_bbox
            page = self.main_window.doc.load_page(page_index)

            # Извлекаем в высоком качестве (300 DPI)
            pix = page.get_pixmap(clip=bbox, dpi=300)

            # Создаем временный файл во временной папке ОС
            temp_dir = tempfile.gettempdir()
            self.temp_img_path = os.path.join(temp_dir, "librepage_external_edit.png")

            # Конвертируем через PIL и сохраняем
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            img.save(self.temp_img_path, format="PNG")

            editor_name = os.path.basename(self.main_window.external_editor_path)
            self.info_label.setText(
                f"<b>Изображение открывается в: {editor_name}</b><br><br>"
                "1. Внесите нужные изменения в открывшемся редакторе.<br>"
                "2. <b>Сохраните</b> файл (обычно <code>Ctrl+S</code> или Файл -> Сохранить/Перезаписать).<br>"
                "3. Вернитесь в это окно и нажмите кнопку <b>'Применить изменения'</b> ниже."
            )
            self.btn_apply.setEnabled(True)

            # Запускаем внешний редактор с передачей пути к файлу
            subprocess.Popen([self.main_window.external_editor_path, self.temp_img_path])

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подготовить изображение:\n{e}")
            self.reject()

    def get_modified_image_path(self):
        return self.temp_img_path