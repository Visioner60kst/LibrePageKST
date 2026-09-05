from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                             QLineEdit, QPushButton, QLabel, QHBoxLayout)
from PyQt6.QtCore import Qt

class MovePageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сдвиг страниц")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Все страницы", 
            "Четные страницы", 
            "Нечетные страницы", 
            "Текущая страница"
        ])
        form_layout.addRow("Применить к:", self.mode_combo)
        
        self.input_h = QLineEdit("0")
        self.input_v = QLineEdit("0")
        
        form_layout.addRow("Сдвиг по горизонтали (мм):", self.input_h)
        form_layout.addRow("Сдвиг по вертикали (мм):", self.input_v)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Применить")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_settings(self):
        return {
            'mode': self.mode_combo.currentText(),
            'dx': float(self.input_h.text() or 0),
            'dy': float(self.input_v.text() or 0)
        }