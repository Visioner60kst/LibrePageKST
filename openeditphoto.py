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
        self.setWindowTitle("External editor")
        self.setModal(True)
        self.resize(450, 200)

        self.temp_img_path = None

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Preparing the image...", self)
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()

        self.btn_apply = QPushButton("Apply changes", self)
        self.btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_apply.clicked.connect(self.accept)
        self.btn_apply.setEnabled(False)

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setStyleSheet("padding: 10px;")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

        # Start process automatically
        self.prepare_and_open()

    def prepare_and_open(self):
        # If the path to the editor is not specified or the file no longer exists, we ask the user to select it
        if not getattr(self.main_window, 'external_editor_path', None) or not os.path.exists(self.main_window.external_editor_path):
            editor_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select editor executable (Photoshop, GIMP, Krita, Paint etc.)",
                "",
                "Executable files (*.exe *.bat *.sh *.app);;All files (*.*)"
            )
            if not editor_path:
                self.info_label.setText("No editor selected. Operation canceled.")
                return
            # We save the path in the main window so as not to ask every time
            self.main_window.external_editor_path = editor_path

        try:
            # We get the selected area from PDF
            page_index = self.main_window.image_selection_manager.selected_page_index
            bbox = self.main_window.image_selection_manager.selected_bbox
            page = self.main_window.doc.load_page(page_index)

            # Extract in high quality (300 DPI)
            pix = page.get_pixmap(clip=bbox, dpi=300)

            # Create a temporary file in the OS temporary folder
            temp_dir = tempfile.gettempdir()
            self.temp_img_path = os.path.join(temp_dir, "librepage_external_edit.png")

            # Convert via PIL and save
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            img.save(self.temp_img_path, format="PNG")

            editor_name = os.path.basename(self.main_window.external_editor_path)
            self.info_label.setText(
                f"<b>The image opens in: {editor_name}</b><br><br>"
                "1. Make the necessary changes in the editor that opens.<br>"
                "2. <b>Save</b> file (usually <code>Ctrl+S</code> or File -> Save/Overwrite).<br>"
                "3. Return to this window and click the button <b>'Apply changes'</b> below."
            )
            self.btn_apply.setEnabled(True)

            # Launch an external editor passing the file path
            subprocess.Popen([self.main_window.external_editor_path, self.temp_img_path])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare image:\n{e}")
            self.reject()

    def get_modified_image_path(self):
        return self.temp_img_path