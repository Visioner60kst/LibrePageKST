from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QDoubleSpinBox, QMessageBox)
from PyQt6.QtCore import Qt

class Booklet2Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка буклета в 2 сгиба")
        self.resize(350, 200)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Поля ввода для порядка страниц (по умолчанию 5, 6, 1 и 2, 3, 4)
        self.front_edit = QLineEdit("5, 6, 1")
        self.back_edit = QLineEdit("2, 3, 4")

        # Настройки смещения
        self.inner_spin = QDoubleSpinBox()
        self.inner_spin.setRange(-100, 100)
        self.inner_spin.setValue(0)
        self.inner_spin.setSuffix(" мм")

        self.outer_spin = QDoubleSpinBox()
        self.outer_spin.setRange(-100, 100)
        self.outer_spin.setValue(0)
        self.outer_spin.setSuffix(" мм")

        form.addRow("Порядок страниц (Лицо):", self.front_edit)
        form.addRow("Порядок страниц (Оборот):", self.back_edit)
        form.addRow("Смещение внутрь:", self.inner_spin)
        form.addRow("Смещение наружу:", self.outer_spin)

        layout.addLayout(form)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def get_settings(self):
        """Парсинг настроек, возвращает словарь при успехе"""
        try:
            # Преобразуем введенные строки в списки чисел
            front_list = [int(x.strip()) for x in self.front_edit.text().split(',')]
            back_list = [int(x.strip()) for x in self.back_edit.text().split(',')]
            
            if len(front_list) != 3 or len(back_list) != 3:
                raise ValueError("В каждом поле должно быть ровно 3 числа, разделенных запятой.")
                
            return {
                'front': front_list,
                'back': back_list,
                'inner_offset': self.inner_spin.value(),
                'outer_offset': self.outer_spin.value()
            }
        except Exception as e:
            QMessageBox.warning(self, "Ошибка ввода", "Проверьте правильность ввода порядка страниц (например: 5, 6, 1).")
            return None