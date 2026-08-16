import sys
import re
import subprocess
import platform
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QCheckBox, QSpinBox, QPushButton, 
                             QGroupBox, QFormLayout, QRadioButton, QLineEdit, QScrollArea, QWidget, QInputDialog)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrinterInfo, QPageSetupDialog
from PyQt6.QtGui import QImage, QPixmap, QPainter, QTransform
from PyQt6.QtCore import Qt, QRect

class PrintWizard(QDialog):
    def __init__(self, file_path, current_page=1):
        super().__init__()
        self.file_path = file_path
        self.current_page = current_page
        self.doc = fitz.open(file_path) if file_path else None
        
        self._is_first_show = True
        self.current_preview_index = 0 
        self.lpi_percent = 100  # Meaning LPI by default
        
        self.setWindowTitle(f"Print Wizard: {file_path.split('/')[-1] if file_path else 'No file'}")
        self.resize(700, 500)
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
        """Handles window resizing, redrawing the preview to fit the new dimensions"""
        super().resizeEvent(event)
        if not self._is_first_show:
            self.update_preview()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # LEFT: Settings (fixed small width)
        controls_container = QWidget()
        controls_container.setMaximumWidth(320)
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        # 1. Printer
        group_printer = QGroupBox("Printing device")
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
        
        self.btn_settings = QPushButton("Printer settings...")
        self.btn_settings.clicked.connect(self.open_printer_settings)
        
        printer_layout.addWidget(self.combo_printers)
        printer_layout.addWidget(self.btn_settings)
        group_printer.setLayout(printer_layout)
        controls_layout.addWidget(group_printer)

        # 2. Selecting pages
        group_range = QGroupBox("Range")
        range_layout = QVBoxLayout()
        range_layout.setSpacing(5)
        
        self.radio_all = QRadioButton("All pages")
        self.radio_all.setChecked(True)
        self.radio_curr = QRadioButton(f"Current ({self.current_page})")
        
        custom_range_layout = QHBoxLayout()
        self.radio_custom = QRadioButton("Their:")
        self.input_custom = QLineEdit()
        self.input_custom.setPlaceholderText("1-5, 8")
        custom_range_layout.addWidget(self.radio_custom)
        custom_range_layout.addWidget(self.input_custom)
        
        range_layout.addWidget(self.radio_all)
        range_layout.addWidget(self.radio_curr)
        range_layout.addLayout(custom_range_layout)
        group_range.setLayout(range_layout)
        controls_layout.addWidget(group_range)

        # 3. Filter and order
        group_filter = QGroupBox("Filter")
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(5)
        self.check_odd = QCheckBox("Odd")
        self.check_even = QCheckBox("Even")
        self.check_reverse = QCheckBox("From the end of the document")
        filter_layout.addWidget(self.check_odd)
        filter_layout.addWidget(self.check_even)
        filter_layout.addWidget(self.check_reverse)
        group_filter.setLayout(filter_layout)
        controls_layout.addWidget(group_filter)

        # 4. Scale and transformation
        group_transform = QGroupBox("Display")
        transform_layout = QVBoxLayout()
        transform_layout.setSpacing(5)
        
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["Fit to Page", "Original Size", "Scale %"])
        form_layout.addRow("Scale:", self.combo_scale)
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(10, 500)
        self.spin_scale.setValue(100)
        form_layout.addRow("Percent:", self.spin_scale)
        transform_layout.addLayout(form_layout)

        checks_layout = QHBoxLayout()
        self.check_flip_v = QCheckBox("Neg. Vert.")
        self.check_flip_h = QCheckBox("Neg. Gore.")
        checks_layout.addWidget(self.check_flip_v)
        checks_layout.addWidget(self.check_flip_h)
        
        self.check_rotate = QCheckBox("Auto rotate")
        transform_layout.addLayout(checks_layout)
        transform_layout.addWidget(self.check_rotate)
        group_transform.setLayout(transform_layout)
        controls_layout.addWidget(group_transform)

        # 5. Print quality (LPI)
        group_quality = QGroupBox("Print quality")
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(5)
        
        self.btn_lpi = QPushButton(f"Change point LPI ({self.lpi_percent}%)")
        self.btn_lpi.clicked.connect(self.change_lpi)
        quality_layout.addWidget(self.btn_lpi)
        
        group_quality.setLayout(quality_layout)
        controls_layout.addWidget(group_quality)

        controls_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_print = QPushButton("Seal")
        btn_print.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        btn_print.clicked.connect(self.print_document)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("padding: 6px;")
        btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_print)
        controls_layout.addLayout(btn_layout)

        main_layout.addWidget(controls_container)

        # RIGHT SIDE: Compact preview + Navigation
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setWidget(self.preview_label)
        self.preview_scroll.setStyleSheet("background-color: #e0e0e0; border: none;")
        # Disable scroll bars, since the image will always fit entirely
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        preview_layout.addWidget(self.preview_scroll)
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Before")
        self.btn_next = QPushButton("After >")
        self.lbl_page_counter = QLabel("p: 0 / 0")
        self.lbl_page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_page_counter, 1)
        nav_layout.addWidget(self.btn_next)
        preview_layout.addLayout(nav_layout)
        
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # Connecting signals
        widgets = [self.check_odd, self.check_even, self.check_reverse, 
                   self.check_flip_v, self.check_flip_h, self.check_rotate,
                   self.spin_scale, self.radio_all, self.radio_curr, 
                   self.radio_custom, self.combo_scale]
        
        for w in widgets:
            if isinstance(w, QCheckBox) or isinstance(w, QRadioButton):
                w.toggled.connect(self.on_settings_changed)
            elif isinstance(w, QSpinBox):
                w.valueChanged.connect(self.on_settings_changed)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.on_settings_changed)
        
        self.input_custom.textChanged.connect(self.on_settings_changed)

    def change_lpi(self):
        """Opens a dialog for changing LPI"""
        value, ok = QInputDialog.getInt(
            self, 
            "Change point LPI", 
            "Enter percentage of points LPI (1-100):\nA lower value will make the photo grainier (for the risograph).", 
            self.lpi_percent, 1, 100, 1
        )
        if ok:
            self.lpi_percent = value
            self.btn_lpi.setText(f"Change point LPI ({self.lpi_percent}%)")
            self.on_settings_changed()

    def apply_lpi_effect(self, img):
        """Applies line reduction effect (LPI/grain size) To QImage"""
        if self.lpi_percent >= 100:
            return img
            
        factor = self.lpi_percent / 100.0
        new_w = max(1, int(img.width() * factor))
        new_h = max(1, int(img.height() * factor))
        
        orig_w = img.width()
        orig_h = img.height()
        
        # Compress the image to “lose” extra points
        small_img = img.scaled(new_w, new_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Stretch back WITHOUT smoothing to visualize large "dots"" (pixels/raster)
        grainy_img = small_img.scaled(orig_w, orig_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        
        return grainy_img

    def on_printer_changed(self, index):
        """Changing the active printer from the drop-down list"""
        printer_info = self.combo_printers.itemData(index)
        if printer_info:
            self.printer.setPrinterName(printer_info.printerName())

    def open_printer_settings(self):
        """Opens the native printer driver settings window"""
        printer_name = self.printer.printerName()
        
        if platform.system() == "Windows":
            try:
                # System call Windows, which opens the driver window (Printing Preferences)
                subprocess.run(["rundll32", "printui.dll,PrintUIEntry", "/e", "/n", printer_name])
                
                # We update the preview because the user could change the paper size in the driver window
                self.on_settings_changed()
            except Exception as e:
                print(f"Could not open driver settings Windows: {e}")
        else:
            # Fallback for macOS And Linux
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

        # 1. Range
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

        # 2. Even/Odd
        if self.check_odd.isChecked():
            indices_list = [i for i in indices_list if (i + 1) % 2 != 0]
        if self.check_even.isChecked():
            indices_list = [i for i in indices_list if (i + 1) % 2 == 0]
            
        # 3. Reverse
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
            self.preview_label.setText("No pages to display")
            self.lbl_page_counter.setText("p: 0 / 0")
            return

        if self.current_preview_index >= len(valid_indices):
            self.current_preview_index = len(valid_indices) - 1
        
        idx = valid_indices[self.current_preview_index]
        self.lbl_page_counter.setText(f"p: {self.current_preview_index + 1} / {len(valid_indices)}")
        
        page = self.doc.load_page(idx)
        
        # We always render previews in good quality (scale x2)
        # Regardless of what percentage is specified in the print settings
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        
        fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
        
        # We apply LPI preview effect
        img = self.apply_lpi_effect(img)
        
        img = img.mirrored(self.check_flip_h.isChecked(), self.check_flip_v.isChecked())
        
        if self.check_rotate.isChecked() and img.width() > img.height():
            img = img.transformed(QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation)
            
        # Scale the image to fit the available visible area
        viewport_size = self.preview_scroll.viewport().size()
        
        # Leave a gap in 4 pixel to avoid edge artifacts
        target_w = max(1, viewport_size.width() - 4)
        target_h = max(1, viewport_size.height() - 4)
        
        pixmap = QPixmap.fromImage(img)
        
        # KeepAspectRatio automatically fits a portrait page in height and a landscape page in width
        scaled_pixmap = pixmap.scaled(
            target_w, target_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
            
        self.preview_label.setPixmap(scaled_pixmap)

    def print_document(self):
        """Sending a document to a real printer"""
        valid_indices = self.get_valid_pages()
        if not valid_indices or not self.doc:
            return

        if not self.printer.isValid():
            print("Invalid printer selected.")
            return

        doc_name = self.file_path.split('/')[-1] if self.file_path else "Document PyMuPDF"
        self.printer.setDocName(doc_name)

        painter = QPainter()
        if not painter.begin(self.printer):
            print("The printing process failed to start. Check the printer connection.")
            return

        for i, page_idx in enumerate(valid_indices):
            if i > 0:
                self.printer.newPage()

            page = self.doc.load_page(page_idx)
            
            dpi = self.printer.logicalDpiX()
            zoom = dpi / 72.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
            
            img = img.convertToFormat(QImage.Format.Format_RGB32)
            
            # We apply LPI effect for printing on paper
            img = self.apply_lpi_effect(img)

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

            if scale_mode == "Fit to page":
                img = img.scaled(pr_w, pr_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            elif scale_mode == "Scale %":
                pct = self.spin_scale.value() / 100.0
                img = img.scaled(int(img.width() * pct), int(img.height() * pct), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            x = int((pr_w - img.width()) / 2)
            y = int((pr_h - img.height()) / 2)

            painter.drawImage(x, y, img)

        painter.end()
        self.accept()

# --- ADDED FUNCTION TO CALL FROM MAIN.PY ---
def start_print(file_path, page=1):
    """
    Creates and opens a modal print window (PrintWizard).
    Used when importing a module inside the main application (QApplication already launched).
    """
    # Since main.py has already launched the application, we just need to create a dialogue
    dialog = PrintWizard(file_path, page)
    # We use .exec(), to make the window modal (the user could not press other buttons 
    # in the main window until the print closes)
    dialog.exec()

# --- THE POSSIBILITY OF RUNNING AS A SEPARATE FILE IS SAVED ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_path = sys.argv[1] if len(sys.argv) > 1 else ""
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    window = PrintWizard(file_path, page)
    window.show()
    sys.exit(app.exec())