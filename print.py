import sys
import re
import subprocess
import platform
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QCheckBox, QSpinBox, QPushButton, 
                             QGroupBox, QFormLayout, QRadioButton, QLineEdit, QScrollArea, QWidget)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo, QPageSetupDialog
from PyQt6.QtGui import QImage, QPixmap, QPainter, QTransform
from PyQt6.QtCore import Qt, QRect, QRectF

class PrintWizard(QDialog):
    def __init__(self, file_path, current_page=1):
        super().__init__()
        self.file_path = file_path
        self.current_page = current_page
        self.doc = fitz.open(file_path) if file_path else None
        
        self._is_first_show = True
        self.current_preview_index = 0 
        
        self.setWindowTitle(f"Мастер печати: {file_path.split('/')[-1] if file_path else 'Нет файла'}")
        self.resize(700, 520)
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if self._is_first_show:
            valid_indices = self.get_valid_pages()
            target_idx = self.current_page - 1
            
            if target_idx in valid_indices:
                self.current_preview_index = valid_indices.index(target_idx)
            else:
                self.current_preview_index = 0
            
            self.update_preview()
            self._is_first_show = False

    def resizeEvent(self, event):
        """Обрабатывает изменение размера окна, перерисовывая превью под новые габариты"""
        super().resizeEvent(event)
        if not self._is_first_show:
            self.update_preview()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ЛЕВАЯ ЧАСТЬ: Настройки (фиксированная небольшая ширина)
        controls_container = QWidget()
        controls_container.setMaximumWidth(320)
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        # 1. Принтер
        group_printer = QGroupBox("Устройство печати")
        printer_layout = QVBoxLayout()
        printer_layout.setSpacing(5)
        
        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.combo_printers = QComboBox()
        
        self.available_printers = QPrinterInfo.availablePrinters()
        default_printer = QPrinterInfo.defaultPrinter()
        
        for p in self.available_printers:
            self.combo_printers.addItem(p.printerName(), p)
            
        if not default_printer.isNull():
            self.combo_printers.setCurrentText(default_printer.printerName())
            self.printer.setPrinterName(default_printer.printerName())
            
        self.combo_printers.currentIndexChanged.connect(self.on_printer_changed)
        
        self.btn_settings = QPushButton("Настройки принтера...")
        self.btn_settings.clicked.connect(self.open_printer_settings)
        
        printer_layout.addWidget(self.combo_printers)
        printer_layout.addWidget(self.btn_settings)
        group_printer.setLayout(printer_layout)
        controls_layout.addWidget(group_printer)

        # 2. Выбор страниц
        group_range = QGroupBox("Диапазон")
        range_layout = QVBoxLayout()
        range_layout.setSpacing(5)
        
        self.radio_all = QRadioButton("Все страницы")
        self.radio_all.setChecked(True)
        self.radio_curr = QRadioButton(f"Текущая ({self.current_page})")
        
        custom_range_layout = QHBoxLayout()
        self.radio_custom = QRadioButton("Свои:")
        self.input_custom = QLineEdit()
        self.input_custom.setPlaceholderText("1-5, 8")
        custom_range_layout.addWidget(self.radio_custom)
        custom_range_layout.addWidget(self.input_custom)
        
        range_layout.addWidget(self.radio_all)
        range_layout.addWidget(self.radio_curr)
        range_layout.addLayout(custom_range_layout)
        group_range.setLayout(range_layout)
        controls_layout.addWidget(group_range)

        # 3. Фильтр и порядок
        group_filter = QGroupBox("Фильтр")
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(5)
        self.check_odd = QCheckBox("Нечетные")
        self.check_even = QCheckBox("Четные")
        self.check_reverse = QCheckBox("С конца документа")
        filter_layout.addWidget(self.check_odd)
        filter_layout.addWidget(self.check_even)
        filter_layout.addWidget(self.check_reverse)
        group_filter.setLayout(filter_layout)
        controls_layout.addWidget(group_filter)

        # 4. Масштаб и трансформация
        group_transform = QGroupBox("Отображение")
        transform_layout = QVBoxLayout()
        transform_layout.setSpacing(5)
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["По размеру страницы", "Исходный размер", "Масштаб %"])
        self.combo_scale.setCurrentText("Исходный размер")  # По умолчанию - Исходный размер
        form_layout.addRow("Масштаб:", self.combo_scale)
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(10, 500)
        self.spin_scale.setValue(100)
        form_layout.addRow("Процент:", self.spin_scale)
        transform_layout.addLayout(form_layout)

        checks_layout = QHBoxLayout()
        self.check_flip_v = QCheckBox("Отр. Верт.")
        self.check_flip_h = QCheckBox("Отр. Гор.")
        checks_layout.addWidget(self.check_flip_v)
        checks_layout.addWidget(self.check_flip_h)
        
        self.check_rotate = QCheckBox("Автоповорот")
        self.check_rotate.setChecked(True)  # По умолчанию включен автоповорот
        transform_layout.addLayout(checks_layout)
        transform_layout.addWidget(self.check_rotate)
        group_transform.setLayout(transform_layout)
        controls_layout.addWidget(group_transform)

        # 5. Качество и режим печати
        group_quality = QGroupBox("Качество печати")
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(5)
        
        self.check_high_dpi = QCheckBox("Высокая четкость (600 DPI MuPDF)")
        self.check_high_dpi.setChecked(True)
        self.check_high_dpi.setToolTip("Векторный рендеринг движком MuPDF в родное разрешение принтера 600/1200 DPI")
        
        self.check_mono = QCheckBox("1-бит Монохром (Бритвенные края)")
        self.check_mono.setChecked(True)
        self.check_mono.setToolTip("Исключает серые пиксели и растровую сетку (halftoning). 100% чистый черный тонер.")

        quality_layout.addWidget(self.check_high_dpi)
        quality_layout.addWidget(self.check_mono)
        
        group_quality.setLayout(quality_layout)
        controls_layout.addWidget(group_quality)

        controls_layout.addStretch()

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_print = QPushButton("Печать")
        btn_print.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        btn_print.clicked.connect(self.print_document)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet("padding: 6px;")
        btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_print)
        controls_layout.addLayout(btn_layout)

        main_layout.addWidget(controls_container)

        # ПРАВАЯ ЧАСТЬ: Компактное превью + Навигация
        preview_group = QGroupBox("Предварительный просмотр")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Превью")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setWidget(self.preview_label)
        self.preview_scroll.setStyleSheet("background-color: #e0e0e0; border: none;")
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        preview_layout.addWidget(self.preview_scroll)
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Пред")
        self.btn_next = QPushButton("След >")
        self.lbl_page_counter = QLabel("Стр: 0 / 0")
        self.lbl_page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_page_counter, 1)
        nav_layout.addWidget(self.btn_next)
        preview_layout.addLayout(nav_layout)
        
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # Подключение сигналов
        widgets = [self.check_odd, self.check_even, self.check_reverse, 
                   self.check_flip_v, self.check_flip_h, self.check_rotate,
                   self.spin_scale, self.radio_all, self.radio_curr, 
                   self.radio_custom, self.combo_scale, self.check_high_dpi, 
                   self.check_mono]
        
        for w in widgets:
            if isinstance(w, QCheckBox) or isinstance(w, QRadioButton):
                w.toggled.connect(self.on_settings_changed)
            elif isinstance(w, QSpinBox):
                w.valueChanged.connect(self.on_settings_changed)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.on_settings_changed)
        
        self.input_custom.textChanged.connect(self.on_settings_changed)

    def binarize_mono(self, img):
        """
        1-битная пороговая бинаризация (Threshold).
        Все полутона превращаются либо в 100% черный, либо в 100% белый.
        Исключает растровую сетку (halftone/dithering) драйвера принтера Canon.
        """
        gray = img.convertToFormat(QImage.Format.Format_Grayscale8)
        mono = gray.convertToFormat(
            QImage.Format.Format_Mono, 
            Qt.ImageConversionFlag.ThresholdDither | Qt.ImageConversionFlag.ColorOnly
        )
        return mono.convertToFormat(QImage.Format.Format_RGB32)

    def on_printer_changed(self, index):
        """Смена активного принтера из выпадающего списка"""
        printer_info = self.combo_printers.itemData(index)
        if printer_info:
            self.printer.setPrinterName(printer_info.printerName())

    def open_printer_settings(self):
        """Открывает родное окно настроек драйвера принтера"""
        printer_name = self.printer.printerName()
        
        if platform.system() == "Windows":
            try:
                subprocess.run(["rundll32", "printui.dll,PrintUIEntry", "/e", "/n", printer_name])
                self.on_settings_changed()
            except Exception as e:
                print(f"Не удалось открыть настройки драйвера Windows: {e}")
        else:
            dialog = QPageSetupDialog(self.printer, self)
            if dialog.exec():
                self.combo_printers.setCurrentText(self.printer.printerName())
                self.on_settings_changed()

    def on_settings_changed(self):
        self.current_preview_index = 0
        self.update_preview()

    def get_valid_pages(self):
        if not self.doc: return []
        total = len(self.doc)
        indices = set()

        # 1. Диапазон
        if self.radio_all.isChecked():
            indices = set(range(total))
        elif self.radio_curr.isChecked():
            indices = {self.current_page - 1}
        elif self.radio_custom.isChecked():
            text = self.input_custom.text()
            parts = text.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    try:
                        subparts = part.split('-')
                        start, end = int(subparts[0]), int(subparts[1])
                        for i in range(min(start, end), max(start, end) + 1):
                            if 1 <= i <= total:
                                indices.add(i - 1)
                    except ValueError:
                        continue
                elif part.isdigit():
                    val = int(part)
                    if 1 <= val <= total:
                        indices.add(val - 1)
        
        indices_list = sorted(list(indices))

        # 2. Четные/Нечетные
        if self.check_odd.isChecked():
            indices_list = [i for i in indices_list if (i + 1) % 2 != 0]
        if self.check_even.isChecked():
            indices_list = [i for i in indices_list if (i + 1) % 2 == 0]
            
        # 3. Реверс
        if self.check_reverse.isChecked():
            indices_list.reverse()
            
        return indices_list

    def prev_page(self):
        if self.current_preview_index > 0:
            self.current_preview_index -= 1
            self.update_preview()

    def next_page(self):
        valid = self.get_valid_pages()
        if valid and self.current_preview_index < len(valid) - 1:
            self.current_preview_index += 1
            self.update_preview()

    def update_preview(self):
        if not self.doc: return
        
        valid_indices = self.get_valid_pages()
        
        if not valid_indices:
            self.preview_label.setText("Нет страниц для отображения")
            self.lbl_page_counter.setText("Стр: 0 / 0")
            return

        if self.current_preview_index >= len(valid_indices):
            self.current_preview_index = len(valid_indices) - 1
        
        idx = valid_indices[self.current_preview_index]
        self.lbl_page_counter.setText(f"Стр: {self.current_preview_index + 1} / {len(valid_indices)}")
        
        page = self.doc.load_page(idx)
        
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        
        fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
        
        if self.check_mono.isChecked():
            img = self.binarize_mono(img)

        img = img.mirrored(self.check_flip_h.isChecked(), self.check_flip_v.isChecked())
        
        if self.check_rotate.isChecked() and img.width() > img.height():
            img = img.transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation)
            
        viewport_size = self.preview_scroll.viewport().size()
        target_w = max(1, viewport_size.width() - 4)
        target_h = max(1, viewport_size.height() - 4)
        
        pixmap = QPixmap.fromImage(img)
        scaled_pixmap = pixmap.scaled(
            target_w, target_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
            
        self.preview_label.setPixmap(scaled_pixmap)

    def print_document(self):
        """Отправка документа на печать"""
        valid_indices = self.get_valid_pages()
        if not valid_indices or not self.doc:
            return

        if not self.printer.isValid():
            print("Выбран недопустимый принтер.")
            return

        doc_name = self.file_path.split('/')[-1] if self.file_path else "Документ PyMuPDF"
        self.printer.setDocName(doc_name)

        painter = QPainter()
        if not painter.begin(self.printer):
            print("Не удалось запустить процесс печати. Проверьте подключение принтера.")
            return

        for i, page_idx in enumerate(valid_indices):
            if i > 0:
                self.printer.newPage()

            page = self.doc.load_page(page_idx)
            
            # Получаем реальное аппаратное разрешение принтера (например 600 DPI)
            target_dpi = self.printer.logicalDpiX() if self.check_high_dpi.isChecked() else 300
            if target_dpi < 300:
                target_dpi = 600

            # Векторный рендеринг страницы движком MuPDF прямо в целевое DPI принтера
            zoom = target_dpi / 72.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            fmt = QImage.Format.Format_RGB888
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
            
            # Если включен монохром, производим пороговую бинаризацию
            if self.check_mono.isChecked():
                img = self.binarize_mono(img)
            else:
                if img.format() != QImage.Format.Format_RGB32:
                    img = img.convertToFormat(QImage.Format.Format_RGB32)

            img = img.mirrored(self.check_flip_h.isChecked(), self.check_flip_v.isChecked())

            page_rect = self.printer.pageRect(QPrinter.Unit.DevicePixel)
            pr_w = int(page_rect.width())
            pr_h = int(page_rect.height())

            if self.check_rotate.isChecked():
                img_is_landscape = img.width() > img.height()
                page_is_landscape = pr_w > pr_h
                if img_is_landscape != page_is_landscape:
                    img = img.transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation)

            scale_mode = self.combo_scale.currentText()

            if scale_mode == "По размеру страницы":
                img = img.scaled(pr_w, pr_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif scale_mode == "Масштаб %":
                pct = self.spin_scale.value() / 100.0
                img = img.scaled(int(img.width() * pct), int(img.height() * pct), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            x = int((pr_w - img.width()) / 2)
            y = int((pr_h - img.height()) / 2)

            painter.drawImage(x, y, img)

        painter.end()
        self.accept()

# --- ФУНКЦИЯ ДЛЯ ВЫЗОВА ИЗ MAIN.PY ---
def start_print(file_path, page=1):
    """
    Создает и открывает модальное окно печати (PrintWizard).
    Используется при импорте модуля внутрь основного приложения (QApplication уже запущен).
    """
    dialog = PrintWizard(file_path, page)
    dialog.exec()

# --- ВОЗМОЖНОСТЬ ЗАПУСКА КАК ОТДЕЛЬНОГО ФАЙЛА ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_path = sys.argv[1] if len(sys.argv) > 1 else ""
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    window = PrintWizard(file_path, page)
    window.show()
    sys.exit(app.exec())