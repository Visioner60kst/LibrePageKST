import os
import io
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QListWidget, QFileDialog, QMessageBox, QGroupBox,
    QDoubleSpinBox, QFormLayout, QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import Qt
from PIL import Image
import fitz  # PyMuPDF


# Размеры страниц ISO в миллиметрах (Ширина x Высота для портретной ориентации)
PAGE_SIZES_MM = {
    "A6": (105.0, 148.0),
    "A5": (148.0, 210.0),
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
}

# Коэффициент перевода миллиметров в типографские пункты (Points)
MM_TO_PT = 2.834645669291339


class ImageToPdfDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image в PDF — LibrePage")
        self.resize(520, 660)
        self.file_paths = []
        self.created_doc = None  # В этом свойстве сохраняется готовый объект PyMuPDF

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # 1. Верхняя кнопка: ДОБАВИТЬ ФАЙЛЫ
        self.btn_add_files = QPushButton("ДОБАВИТЬ ФАЙЛЫ")
        self.btn_add_files.setStyleSheet(
            "font-weight: bold; font-size: 14px; padding: 10px; background-color: #1976D2; color: white; border-radius: 4px;"
        )
        self.btn_add_files.clicked.connect(self.add_files)
        main_layout.addWidget(self.btn_add_files)

        # Список добавленных файлов
        self.list_files = QListWidget()
        self.list_files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_files.setToolTip("Список выбранных изображений. Вы можете удалять ненужные пункты.")
        main_layout.addWidget(self.list_files)

        # Управление списком файлов (Удалить / Очистить)
        btn_file_layout = QHBoxLayout()
        self.btn_remove = QPushButton("Удалить выделенные")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("Очистить список")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_file_layout.addWidget(self.btn_remove)
        btn_file_layout.addWidget(self.btn_clear)
        main_layout.addLayout(btn_file_layout)

        # 2. Группа параметров ориентации и размера
        settings_group = QGroupBox("Параметры конвертации")
        group_layout = QVBoxLayout()

        # Выбор режима ориентации
        lbl_mode = QLabel("Ориентация и размер листов:")
        lbl_mode.setStyleSheet("font-weight: bold;")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "1) Каждый лист оригинальный размер",
            "2) Все листы сделать одного размера и вертикальные",
            "3) Все листы сделать одного размера и горизонтальные"
        ])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        group_layout.addWidget(lbl_mode)
        group_layout.addWidget(self.combo_mode)

        # Выбор формата листа (А6 - А0, свой размер)
        self.lbl_size = QLabel("Формат всех листов:")
        self.lbl_size.setStyleSheet("font-weight: bold;")
        self.combo_size = QComboBox()
        self.combo_size.addItems(["A6", "A5", "A4", "A3", "A2", "A1", "A0", "Свой размер"])
        self.combo_size.setCurrentText("A4")
        self.combo_size.currentIndexChanged.connect(self.on_size_changed)

        group_layout.addWidget(self.lbl_size)
        group_layout.addWidget(self.combo_size)

        # Блок ввода пользовательского размера
        self.custom_size_group = QGroupBox("Пользовательский размер страницы (мм)")
        custom_layout = QFormLayout()
        
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(10.0, 10000.0)
        self.spin_width.setValue(210.0)
        self.spin_width.setSuffix(" мм")

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(10.0, 10000.0)
        self.spin_height.setValue(297.0)
        self.spin_height.setSuffix(" мм")

        custom_layout.addRow("Ширина:", self.spin_width)
        custom_layout.addRow("Высота:", self.spin_height)
        self.custom_size_group.setLayout(custom_layout)
        self.custom_size_group.setVisible(False)

        group_layout.addWidget(self.custom_size_group)

        # Переключатель: заполнение листа без белых полей
        self.chk_fill_page = QCheckBox("Заполнить страницу без белых полей (масштабирование до краев)")
        self.chk_fill_page.setToolTip(
            "Если пропорции картинки не совпадают с форматом листа, изображение увеличится до полного заполнения страницы без белых полей по краям."
        )
        group_layout.addWidget(self.chk_fill_page)

        settings_group.setLayout(group_layout)
        main_layout.addWidget(settings_group)

        # 3. Кнопка ПРИМЕНИТЬ
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet(
            "font-weight: bold; font-size: 15px; background-color: #388E3C; color: white; padding: 12px; border-radius: 4px;"
        )
        self.btn_apply.clicked.connect(self.process_images_to_pdf)
        main_layout.addWidget(self.btn_apply)

        # Инициализация первичного состояния
        self.on_mode_changed(0)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения",
            "",
            "Изображения (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.gif);;Все файлы (*.*)"
        )
        if files:
            for f in files:
                if f not in self.file_paths:
                    self.file_paths.append(f)
                    self.list_files.addItem(f)

    def remove_selected(self):
        selected_items = self.list_files.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.list_files.row(item)
            self.list_files.takeItem(row)
            if row < len(self.file_paths):
                self.file_paths.pop(row)

    def clear_files(self):
        self.file_paths.clear()
        self.list_files.clear()

    def on_mode_changed(self, index):
        # Если выбран режим "1) Каждый лист оригинальный размер", отключаем выбор формата и переключатель
        is_fixed_size = (index != 0)
        self.combo_size.setEnabled(is_fixed_size)
        self.lbl_size.setEnabled(is_fixed_size)
        self.chk_fill_page.setEnabled(is_fixed_size)
        
        if not is_fixed_size:
            self.custom_size_group.setVisible(False)
        else:
            self.on_size_changed()

    def on_size_changed(self):
        is_custom = (self.combo_size.currentText() == "Свой размер") and self.combo_size.isEnabled()
        self.custom_size_group.setVisible(is_custom)

    def get_target_page_dimensions_mm(self, mode_index):
        """Возвращает тупл (width_mm, height_mm) с учетом целевой ориентации."""
        size_str = self.combo_size.currentText()
        if size_str == "Свой размер":
            w_mm = self.spin_width.value()
            h_mm = self.spin_height.value()
        else:
            w_mm, h_mm = PAGE_SIZES_MM.get(size_str, (210.0, 297.0))

        # Режим 2: Все вертикальные (Ширина <= Высота)
        if mode_index == 1:
            width_mm = min(w_mm, h_mm)
            height_mm = max(w_mm, h_mm)
        # Режим 3: Все горизонтальные (Ширина >= Высота)
        elif mode_index == 2:
            width_mm = max(w_mm, h_mm)
            height_mm = min(w_mm, h_mm)
        else:
            width_mm, height_mm = w_mm, h_mm

        return width_mm, height_mm

    def process_images_to_pdf(self):
        if not self.file_paths:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, добавьте хотя бы один файл изображения.")
            return

        mode_index = self.combo_mode.currentIndex()
        fill_page = self.chk_fill_page.isChecked() and (mode_index != 0)

        try:
            doc = fitz.open()

            for img_path in self.file_paths:
                if not os.path.exists(img_path):
                    continue

                with Image.open(img_path) as img:
                    # Приводим к совместимому цветовому пространству RGB, если нужно
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    img_w, img_h = img.size

                    # --- РЕЖИМ 1: каждый лист оригинальный размер ---
                    if mode_index == 0:
                        dpi = img.info.get('dpi', (300, 300))
                        dpi_x = dpi[0] if isinstance(dpi, tuple) and dpi[0] > 0 else 300
                        dpi_y = dpi[1] if isinstance(dpi, tuple) and dpi[1] > 0 else 300

                        page_w_pt = (img_w / dpi_x) * 72.0
                        page_h_pt = (img_h / dpi_y) * 72.0

                        page = doc.new_page(width=page_w_pt, height=page_h_pt)
                        rect = fitz.Rect(0, 0, page_w_pt, page_h_pt)

                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="JPEG", quality=95)
                        page.insert_image(rect, stream=img_bytes.getvalue())

                    # --- РЕЖИМ 2: Все листы одного размера и вертикальные ---
                    elif mode_index == 1:
                        # Если картинка горизонтальная -> поворот на 90° по часовой стрелке
                        if img_w > img_h:
                            img = img.transpose(Image.Transpose.ROTATE_270)
                            img_w, img_h = img.size

                        w_mm, h_mm = self.get_target_page_dimensions_mm(1)
                        page_w_pt = w_mm * MM_TO_PT
                        page_h_pt = h_mm * MM_TO_PT

                        page = doc.new_page(width=page_w_pt, height=page_h_pt)

                        if fill_page:
                            scale = max(page_w_pt / img_w, page_h_pt / img_h)
                        else:
                            scale = min(page_w_pt / img_w, page_h_pt / img_h)

                        scaled_w = img_w * scale
                        scaled_h = img_h * scale

                        x0 = (page_w_pt - scaled_w) / 2.0
                        y0 = (page_h_pt - scaled_h) / 2.0
                        rect = fitz.Rect(x0, y0, x0 + scaled_w, y0 + scaled_h)

                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="JPEG", quality=95)
                        page.insert_image(rect, stream=img_bytes.getvalue())

                    # --- РЕЖИМ 3: Все листы одного размера и горизонтальные ---
                    elif mode_index == 2:
                        # Если картинка вертикальная -> поворот на 90° по часовой стрелке
                        if img_h > img_w:
                            img = img.transpose(Image.Transpose.ROTATE_270)
                            img_w, img_h = img.size

                        w_mm, h_mm = self.get_target_page_dimensions_mm(2)
                        page_w_pt = w_mm * MM_TO_PT
                        page_h_pt = h_mm * MM_TO_PT

                        page = doc.new_page(width=page_w_pt, height=page_h_pt)

                        if fill_page:
                            scale = max(page_w_pt / img_w, page_h_pt / img_h)
                        else:
                            scale = min(page_w_pt / img_w, page_h_pt / img_h)

                        scaled_w = img_w * scale
                        scaled_h = img_h * scale

                        x0 = (page_w_pt - scaled_w) / 2.0
                        y0 = (page_h_pt - scaled_h) / 2.0
                        rect = fitz.Rect(x0, y0, x0 + scaled_w, y0 + scaled_h)

                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="JPEG", quality=95)
                        page.insert_image(rect, stream=img_bytes.getvalue())

            # Преобразуем созданный документ в байты и переносим в оперативный PyMuPDF документ
            pdf_bytes = doc.write()
            doc.close()

            # Сохраняем независимый объект fitz.Document в свойстве created_doc
            self.created_doc = fitz.open("pdf", pdf_bytes)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать PDF документ:\n{str(e)}")


def show_image_to_pdf_dialog(parent=None):
    dialog = ImageToPdfDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.created_doc
    return None