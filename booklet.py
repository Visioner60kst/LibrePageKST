from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QComboBox, 
                             QPushButton, QLabel, QFormLayout, QDoubleSpinBox, QButtonGroup)
from PyQt6.QtCore import Qt

class BookletDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Booklet Settings")
        self.setFixedWidth(350)
        
        layout = QVBoxLayout(self)
        
        # Heading
        title = QLabel("Booklet Settings")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Type group
        self.group_type = QButtonGroup(self)
        self.rad_one = QRadioButton("One notebook (whole file)")
        self.rad_many = QRadioButton("Several notebooks")
        self.rad_one.setChecked(True)
        self.group_type.addButton(self.rad_one)
        self.group_type.addButton(self.rad_many)
        
        layout.addWidget(self.rad_one)
        layout.addWidget(self.rad_many)
        
        # Selecting pages in a notebook
        form = QFormLayout()
        self.combo_pages = QComboBox()
        # Standard notebook sizes (multiples 4)
        pages = ["4", "8", "16", "24", "32", "40", "48", "64"]
        self.combo_pages.addItems(pages)
        form.addRow("Pages in one notebook:", self.combo_pages)
        
        # Offsets
        self.spin_inner = QDoubleSpinBox()
        self.spin_inner.setRange(0, 50)
        self.spin_inner.setSuffix(" mm")
        
        self.spin_outer = QDoubleSpinBox()
        self.spin_outer.setRange(0, 50)
        self.spin_outer.setSuffix(" mm")
        
        form.addRow("Offset inward:", self.spin_inner)
        form.addRow("Outward offset:", self.spin_outer)
        
        layout.addLayout(form)
        
        # Button
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; padding: 5px;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

    def get_settings(self):
        return {
            "type": "one" if self.rad_one.isChecked() else "many",
            "pages": int(self.combo_pages.currentText()),
            "inner_offset": self.spin_inner.value(),
            "outer_offset": self.spin_outer.value()
        }