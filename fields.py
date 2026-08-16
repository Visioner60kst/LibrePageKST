from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QDoubleSpinBox, QComboBox, 
                             QPushButton, QGridLayout)
from PyQt6.QtCore import Qt

class FieldsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add fields (fields+)")
        self.resize(320, 200)
        
        layout = QVBoxLayout(self)
        
        grid = QGridLayout()
        
        # Above
        grid.addWidget(QLabel("Add fields on top (mm):"), 0, 0)
        self.spin_top = QDoubleSpinBox()
        self.setup_spinbox(self.spin_top)
        grid.addWidget(self.spin_top, 0, 1)
        
        # From below
        grid.addWidget(QLabel("Add fields below (mm):"), 1, 0)
        self.spin_bottom = QDoubleSpinBox()
        self.setup_spinbox(self.spin_bottom)
        grid.addWidget(self.spin_bottom, 1, 1)
        
        # Left
        grid.addWidget(QLabel("Add fields to the left (mm):"), 2, 0)
        self.spin_left = QDoubleSpinBox()
        self.setup_spinbox(self.spin_left)
        grid.addWidget(self.spin_left, 2, 1)
        
        # Right
        grid.addWidget(QLabel("Add fields to the right (mm):"), 3, 0)
        self.spin_right = QDoubleSpinBox()
        self.setup_spinbox(self.spin_right)
        grid.addWidget(self.spin_right, 3, 1)
        
        layout.addLayout(grid)
        
        # Mode selection
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "All pages", 
            "Current page", 
            "Even pages", 
            "Odd pages"
        ])
        layout.addWidget(self.combo_mode)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("APPLY")
        self.btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.btn_apply.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("padding: 6px; border-radius: 4px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
    def setup_spinbox(self, spinbox):
        spinbox.setRange(0.0, 5000.0) # Maximum field 500 cm
        spinbox.setSingleStep(1.0)
        spinbox.setDecimals(1)
        spinbox.setValue(0.0)

    def get_settings(self):
        return {
            'top': self.spin_top.value(),
            'bottom': self.spin_bottom.value(),
            'left': self.spin_left.value(),
            'right': self.spin_right.value(),
            'mode': self.combo_mode.currentText()
        }