import fitz
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QRadioButton, 
                             QButtonGroup, QMessageBox, QHBoxLayout, QLabel)

class RotatePageDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Rotate pages")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Angle group
        self.angle_group = QButtonGroup(self)
        self.btn_m90 = QRadioButton("-90° (counterclockwise)")
        self.btn_90 = QRadioButton("+90° (clockwise)")
        self.btn_180 = QRadioButton("180°")
        self.btn_90.setChecked(True)
        
        self.angle_group.addButton(self.btn_m90, -90)
        self.angle_group.addButton(self.btn_90, 90)
        self.angle_group.addButton(self.btn_180, 180)
        
        layout.addWidget(QLabel("Rotation angle:"))
        layout.addWidget(self.btn_m90)
        layout.addWidget(self.btn_90)
        layout.addWidget(self.btn_180)
        
        # Page selection group
        self.scope_group = QButtonGroup(self)
        self.btn_current = QRadioButton("Current page")
        self.btn_all = QRadioButton("All pages")
        self.btn_current.setChecked(True)
        
        self.scope_group.addButton(self.btn_current, 0)
        self.scope_group.addButton(self.btn_all, 1)
        
        layout.addWidget(QLabel("Apply to:"))
        layout.addWidget(self.btn_current)
        layout.addWidget(self.btn_all)
        
        # OK button
        btn_ok = QPushButton("Apply")
        btn_ok.clicked.connect(self.apply_rotation)
        layout.addWidget(btn_ok)

    def apply_rotation(self):
        angle = self.angle_group.checkedId()
        is_all = self.scope_group.checkedId() == 1
        
        try:
            if is_all:
                for page in self.main_window.doc:
                    page.set_rotation((page.rotation + angle) % 360)
            else:
                idx = self.main_window.active_page_index
                page = self.main_window.doc.load_page(idx)
                page.set_rotation((page.rotation + angle) % 360)
            
            self.main_window.render_all()
            self.main_window.history_manager.save_state()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error when turning: {e}")