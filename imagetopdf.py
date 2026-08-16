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


# Page sizes ISO in millimeters (Width x Height for portrait orientation)
PAGE_SIZES_MM = {
    "A6": (105.0, 148.0),
    "A5": (148.0, 210.0),
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
}

# Conversion factor of millimeters to printing points (Points)
MM_TO_PT = 2.834645669291339


class ImageToPdfDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image V PDF — LibrePage")
        self.resize(520, 660)
        self.file_paths = []
        self.created_doc = None  # This property stores the finished object PyMuPDF

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # 1. Top button: ADD FILES
        self.btn_add_files = QPushButton("ADD FILES")
        self.btn_add_files.setStyleSheet(
            "font-weight: bold; font-size: 14px; padding: 10px; background-color: #1976D2; color: white; border-radius: 4px;"
        )
        self.btn_add_files.clicked.connect(self.add_files)
        main_layout.addWidget(self.btn_add_files)

        # List of added files
        self.list_files = QListWidget()
        self.list_files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_files.setToolTip("List of selected images. You can delete unnecessary items.")
        main_layout.addWidget(self.list_files)

        # File list management (Delete / Clear)
        btn_file_layout = QHBoxLayout()
        self.btn_remove = QPushButton("Delete selected")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("Clear list")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_file_layout.addWidget(self.btn_remove)
        btn_file_layout.addWidget(self.btn_clear)
        main_layout.addLayout(btn_file_layout)

        # 2. Group of orientation and size parameters
        settings_group = QGroupBox("Conversion options")
        group_layout = QVBoxLayout()

        # Selecting Orientation Mode
        lbl_mode = QLabel("Sheet orientation and size:")
        lbl_mode.setStyleSheet("font-weight: bold;")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "1) Each sheet is original size",
            "2) Make all sheets the same size and vertical",
            "3) Make all sheets the same size and horizontal"
        ])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        group_layout.addWidget(lbl_mode)
        group_layout.addWidget(self.combo_mode)

        # Selecting a Sheet Size (A6 - A0, your size)
        self.lbl_size = QLabel("Format of all sheets:")
        self.lbl_size.setStyleSheet("font-weight: bold;")
        self.combo_size = QComboBox()
        self.combo_size.addItems(["A6", "A5", "A4", "A3", "A2", "A1", "A0", "Your size"])
        self.combo_size.setCurrentText("A4")
        self.combo_size.currentIndexChanged.connect(self.on_size_changed)

        group_layout.addWidget(self.lbl_size)
        group_layout.addWidget(self.combo_size)

        # Custom size input block
        self.custom_size_group = QGroupBox("Custom Page Size (mm)")
        custom_layout = QFormLayout()
        
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(10.0, 10000.0)
        self.spin_width.setValue(210.0)
        self.spin_width.setSuffix(" mm")

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(10.0, 10000.0)
        self.spin_height.setValue(297.0)
        self.spin_height.setSuffix(" mm")

        custom_layout.addRow("Width:", self.spin_width)
        custom_layout.addRow("Height:", self.spin_height)
        self.custom_size_group.setLayout(custom_layout)
        self.custom_size_group.setVisible(False)

        group_layout.addWidget(self.custom_size_group)

        # Switch: fill the sheet without white margins
        self.chk_fill_page = QCheckBox("Fill the page without white margins (scaling to edges)")
        self.chk_fill_page.setToolTip(
            "If the proportions of the image do not match the sheet size, the image will be enlarged until it completely fills the page without white margins at the edges."
        )
        group_layout.addWidget(self.chk_fill_page)

        settings_group.setLayout(group_layout)
        main_layout.addWidget(settings_group)

        # 3. APPLY button
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet(
            "font-weight: bold; font-size: 15px; background-color: #388E3C; color: white; padding: 12px; border-radius: 4px;"
        )
        self.btn_apply.clicked.connect(self.process_images_to_pdf)
        main_layout.addWidget(self.btn_apply)

        # Initialization of the primary state
        self.on_mode_changed(0)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select images",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.gif);;All files (*.*)"
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
        # If the mode is selected "1) Each sheet is original size", disable the format selection and switch
        is_fixed_size = (index != 0)
        self.combo_size.setEnabled(is_fixed_size)
        self.lbl_size.setEnabled(is_fixed_size)
        self.chk_fill_page.setEnabled(is_fixed_size)
        
        if not is_fixed_size:
            self.custom_size_group.setVisible(False)
        else:
            self.on_size_changed()

    def on_size_changed(self):
        is_custom = (self.combo_size.currentText() == "Your size") and self.combo_size.isEnabled()
        self.custom_size_group.setVisible(is_custom)

    def get_target_page_dimensions_mm(self, mode_index):
        """Returns a tuple (width_mm, height_mm) taking into account target orientation."""
        size_str = self.combo_size.currentText()
        if size_str == "Your size":
            w_mm = self.spin_width.value()
            h_mm = self.spin_height.value()
        else:
            w_mm, h_mm = PAGE_SIZES_MM.get(size_str, (210.0, 297.0))

        # Mode 2: All vertical (Width <= Height)
        if mode_index == 1:
            width_mm = min(w_mm, h_mm)
            height_mm = max(w_mm, h_mm)
        # Mode 3: All horizontal (Width >= Height)
        elif mode_index == 2:
            width_mm = max(w_mm, h_mm)
            height_mm = min(w_mm, h_mm)
        else:
            width_mm, height_mm = w_mm, h_mm

        return width_mm, height_mm

    def process_images_to_pdf(self):
        if not self.file_paths:
            QMessageBox.warning(self, "Warning", "Please add at least one image file.")
            return

        mode_index = self.combo_mode.currentIndex()
        fill_page = self.chk_fill_page.isChecked() and (mode_index != 0)

        try:
            doc = fitz.open()

            for img_path in self.file_paths:
                if not os.path.exists(img_path):
                    continue

                with Image.open(img_path) as img:
                    # Reduce to a compatible color space RGB, if necessary
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    img_w, img_h = img.size

                    # --- MODE 1: each sheet is original size ---
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

                    # --- MODE 2: All sheets are the same size and vertical ---
                    elif mode_index == 1:
                        # If the picture is horizontal -> turn to 90° clockwise
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

                    # --- MODE 3: All sheets are the same size and horizontal ---
                    elif mode_index == 2:
                        # If the picture is vertical -> turn to 90° clockwise
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

            # We convert the created document into bytes and transfer it to operational PyMuPDF document
            pdf_bytes = doc.write()
            doc.close()

            # Saving an independent object fitz.Document in property created_doc
            self.created_doc = fitz.open("pdf", pdf_bytes)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create PDF document:\n{str(e)}")


def show_image_to_pdf_dialog(parent=None):
    dialog = ImageToPdfDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.created_doc
    return None