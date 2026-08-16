from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QDoubleSpinBox, QMessageBox)
from PyQt6.QtCore import Qt

class Booklet2Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Setting up a booklet in 2 fold")
        self.resize(350, 200)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Input fields for page order (by default 5, 6, 1 And 2, 3, 4)
        self.front_edit = QLineEdit("5, 6, 1")
        self.back_edit = QLineEdit("2, 3, 4")

        # Offset Settings
        self.inner_spin = QDoubleSpinBox()
        self.inner_spin.setRange(-100, 100)
        self.inner_spin.setValue(0)
        self.inner_spin.setSuffix(" mm")

        self.outer_spin = QDoubleSpinBox()
        self.outer_spin.setRange(-100, 100)
        self.outer_spin.setValue(0)
        self.outer_spin.setSuffix(" mm")

        form.addRow("Page order (Face):", self.front_edit)
        form.addRow("Page order (Turnover):", self.back_edit)
        form.addRow("Offset inward:", self.inner_spin)
        form.addRow("Outward offset:", self.outer_spin)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def get_settings(self):
        """Parsing settings, returns dictionary on success"""
        try:
            # Converting the entered strings into lists of numbers
            front_list = [int(x.strip()) for x in self.front_edit.text().split(',')]
            back_list = [int(x.strip()) for x in self.back_edit.text().split(',')]
            
            if len(front_list) != 3 or len(back_list) != 3:
                raise ValueError("Each field must be exactly 3 comma separated numbers.")
                
            return {
                'front': front_list,
                'back': back_list,
                'inner_offset': self.inner_spin.value(),
                'outer_offset': self.outer_spin.value()
            }
        except Exception as e:
            QMessageBox.warning(self, "Input error", "Check that the page order is entered correctly (For example: 5, 6, 1).")
            return None