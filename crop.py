from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QComboBox,
    QGroupBox
)


class CropPageDialog(QDialog):

    # Сигнал:
    # top, bottom, left, right, mode
    preview_changed = pyqtSignal(float, float, float, float, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Кадрирование (Обрезка)")
        self.resize(300, 250)

        layout = QVBoxLayout(self)

        # ==========================================
        # НАСТРОЙКИ КАДРИРОВАНИЯ
        # ==========================================

        margins_group = QGroupBox(
            "Укажите значения обрезки в мм"
        )

        margins_layout = QVBoxLayout(margins_group)

        # ------------------------------------------
        # Сверху
        # ------------------------------------------

        h_top = QHBoxLayout()

        h_top.addWidget(QLabel("Сверху:"))

        self.spin_top = QDoubleSpinBox()
        self.spin_top.setRange(0, 1000)
        self.spin_top.setDecimals(2)
        self.spin_top.setSuffix(" мм")

        h_top.addWidget(self.spin_top)

        margins_layout.addLayout(h_top)

        # ------------------------------------------
        # Снизу
        # ------------------------------------------

        h_bottom = QHBoxLayout()

        h_bottom.addWidget(QLabel("Снизу:"))

        self.spin_bottom = QDoubleSpinBox()
        self.spin_bottom.setRange(0, 1000)
        self.spin_bottom.setDecimals(2)
        self.spin_bottom.setSuffix(" мм")

        h_bottom.addWidget(self.spin_bottom)

        margins_layout.addLayout(h_bottom)

        # ------------------------------------------
        # Слева
        # ------------------------------------------

        h_left = QHBoxLayout()

        h_left.addWidget(QLabel("Слева:"))

        self.spin_left = QDoubleSpinBox()
        self.spin_left.setRange(0, 1000)
        self.spin_left.setDecimals(2)
        self.spin_left.setSuffix(" мм")

        h_left.addWidget(self.spin_left)

        margins_layout.addLayout(h_left)

        # ------------------------------------------
        # Справа
        # ------------------------------------------

        h_right = QHBoxLayout()

        h_right.addWidget(QLabel("Справа:"))

        self.spin_right = QDoubleSpinBox()
        self.spin_right.setRange(0, 1000)
        self.spin_right.setDecimals(2)
        self.spin_right.setSuffix(" мм")

        h_right.addWidget(self.spin_right)

        margins_layout.addLayout(h_right)

        layout.addWidget(margins_group)

        # ==========================================
        # ВЫБОР СТРАНИЦ
        # ==========================================

        self.combo_mode = QComboBox()

        self.combo_mode.addItems([
            "Все страницы",
            "Четные страницы",
            "Нечетные страницы",
            "Текущая страница"
        ])

        layout.addWidget(
            QLabel("Применить к:")
        )

        layout.addWidget(
            self.combo_mode
        )

        # ==========================================
        # КНОПКА ПРИМЕНИТЬ
        # ==========================================

        self.btn_apply = QPushButton(
            "ПРИМЕНИТЬ"
        )

        self.btn_apply.setStyleSheet(
            "background-color: #ffc107; "
            "color: black; "
            "font-weight: bold;"
        )

        self.btn_apply.clicked.connect(
            self._apply_clicked
        )

        layout.addWidget(
            self.btn_apply
        )

        # ==========================================
        # ОБНОВЛЕНИЕ ЛИНИЙ ПРИ ВВОДЕ
        # ==========================================

        self.spin_top.valueChanged.connect(
            self._preview_changed
        )

        self.spin_bottom.valueChanged.connect(
            self._preview_changed
        )

        self.spin_left.valueChanged.connect(
            self._preview_changed
        )

        self.spin_right.valueChanged.connect(
            self._preview_changed
        )

        self.combo_mode.currentTextChanged.connect(
            self._preview_changed
        )

    # ==================================================
    # ПРЕДПРОСМОТР КАДРИРОВАНИЯ
    # ==================================================

    def _preview_changed(self, *args):

        self.preview_changed.emit(
            self.spin_top.value(),
            self.spin_bottom.value(),
            self.spin_left.value(),
            self.spin_right.value(),
            self.combo_mode.currentText()
        )

    # ==================================================
    # ПРИМЕНИТЬ
    # ==================================================

    def _apply_clicked(self):

        # Перед закрытием сообщаем main.py,
        # что предварительный просмотр нужно убрать.
        self.preview_changed.emit(
            -1,
            -1,
            -1,
            -1,
            "__APPLY__"
        )

        self.accept()

    # ==================================================
    # ЗАКРЫТИЕ БЕЗ ПРИМЕНЕНИЯ
    # ==================================================

    def reject(self):

        # Убираем линии
        self.preview_changed.emit(
            -1,
            -1,
            -1,
            -1,
            "__CANCEL__"
        )

        super().reject()

    # ==================================================
    # ПОЛУЧИТЬ НАСТРОЙКИ
    # ==================================================

    def get_settings(self):

        return {
            'top': self.spin_top.value(),
            'bottom': self.spin_bottom.value(),
            'left': self.spin_left.value(),
            'right': self.spin_right.value(),
            'mode': self.combo_mode.currentText()
        }