import os
import io
import math

from PIL import Image

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QComboBox,
    QDoubleSpinBox, QSpinBox, QGroupBox, QMessageBox,
    QRadioButton, QButtonGroup, QLineEdit
)
from PyQt6.QtCore import Qt


class LogoPageDialog(QDialog):
    """
    Диалог настройки размещения логотипа на страницах PDF.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Поместить лого")
        self.setMinimumWidth(500)
        self.setModal(True)

        self.logo_path = ""

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # ==========================================================
        # ЛОГОТИП
        # ==========================================================

        logo_group = QGroupBox("Логотип")
        logo_layout = QHBoxLayout(logo_group)

        self.logo_edit = QLineEdit()
        self.logo_edit.setReadOnly(True)
        self.logo_edit.setPlaceholderText("Логотип не выбран")

        self.btn_browse = QPushButton("Выбрать")
        self.btn_browse.clicked.connect(self.select_logo)

        logo_layout.addWidget(self.logo_edit)
        logo_layout.addWidget(self.btn_browse)

        main_layout.addWidget(logo_group)

        # ==========================================================
        # РАСПОЛОЖЕНИЕ
        # ==========================================================

        position_group = QGroupBox("Расположение")
        position_layout = QVBoxLayout(position_group)

        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "Верхний левый",
            "Верхний правый",
            "Нижний левый",
            "Нижний правый",
            "Центр",
            "Заполнить лист"
        ])

        self.position_combo.currentIndexChanged.connect(
            self.position_changed
        )

        position_layout.addWidget(self.position_combo)

        # ----------------------------------------------------------
        # Отступы
        # ----------------------------------------------------------

        margin_layout = QGridLayout()

        margin_layout.addWidget(QLabel("Отступ по горизонтали:"), 0, 0)

        self.margin_x = QDoubleSpinBox()
        self.margin_x.setRange(0, 1000)
        self.margin_x.setDecimals(2)
        self.margin_x.setValue(10)
        self.margin_x.setSuffix(" мм")

        margin_layout.addWidget(self.margin_x, 0, 1)

        margin_layout.addWidget(QLabel("Отступ по вертикали:"), 1, 0)

        self.margin_y = QDoubleSpinBox()
        self.margin_y.setRange(0, 1000)
        self.margin_y.setDecimals(2)
        self.margin_y.setValue(10)
        self.margin_y.setSuffix(" мм")

        margin_layout.addWidget(self.margin_y, 1, 1)

        position_layout.addLayout(margin_layout)

        # ----------------------------------------------------------
        # Количество логотипов при заполнении
        # ----------------------------------------------------------

        self.tile_group = QGroupBox("Заполнение листа")
        tile_layout = QGridLayout(self.tile_group)

        tile_layout.addWidget(
            QLabel("По горизонтали:"), 0, 0
        )

        self.tile_horizontal = QSpinBox()
        self.tile_horizontal.setRange(1, 100)
        self.tile_horizontal.setValue(3)

        tile_layout.addWidget(
            self.tile_horizontal, 0, 1
        )

        tile_layout.addWidget(
            QLabel("По вертикали:"), 1, 0
        )

        self.tile_vertical = QSpinBox()
        self.tile_vertical.setRange(1, 100)
        self.tile_vertical.setValue(3)

        tile_layout.addWidget(
            self.tile_vertical, 1, 1
        )

        position_layout.addWidget(self.tile_group)

        main_layout.addWidget(position_group)

        # ==========================================================
        # ПАРАМЕТРЫ ЛОГОТИПА
        # ==========================================================

        params_group = QGroupBox("Параметры логотипа")
        params_layout = QGridLayout(params_group)

        # Размер
        params_layout.addWidget(
            QLabel("Размер:"), 0, 0
        )

        self.logo_size = QDoubleSpinBox()
        self.logo_size.setRange(1, 1000)
        self.logo_size.setDecimals(2)
        self.logo_size.setValue(30)
        self.logo_size.setSuffix(" мм")

        params_layout.addWidget(
            self.logo_size, 0, 1
        )

        # Поворот
        params_layout.addWidget(
            QLabel("Повернуть:"), 1, 0
        )

        self.rotation = QDoubleSpinBox()
        self.rotation.setRange(-360, 360)
        self.rotation.setDecimals(1)
        self.rotation.setValue(0)
        self.rotation.setSuffix("°")

        params_layout.addWidget(
            self.rotation, 1, 1
        )

        # Прозрачность
        params_layout.addWidget(
            QLabel("Прозрачность:"), 2, 0
        )

        self.opacity = QSpinBox()
        self.opacity.setRange(1, 100)
        self.opacity.setValue(100)
        self.opacity.setSuffix(" %")

        params_layout.addWidget(
            self.opacity, 2, 1
        )

        main_layout.addWidget(params_group)

        # ==========================================================
        # СТРАНИЦЫ
        # ==========================================================

        pages_group = QGroupBox("Применить к")
        pages_layout = QHBoxLayout(pages_group)

        self.pages_combo = QComboBox()
        self.pages_combo.addItems([
            "Все страницы",
            "Текущая страница",
            "Четные страницы",
            "Нечетные страницы"
        ])

        pages_layout.addWidget(self.pages_combo)

        main_layout.addWidget(pages_group)

        # ==========================================================
        # КНОПКИ
        # ==========================================================

        buttons_layout = QHBoxLayout()

        buttons_layout.addStretch()

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.validate_and_accept)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_apply)

        main_layout.addLayout(buttons_layout)

        # Начальное состояние
        self.position_changed(0)

    # ==============================================================
    # ВЫБОР ЛОГОТИПА
    # ==============================================================

    def select_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите логотип",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;"
            "PNG (*.png);;"
            "JPEG (*.jpg *.jpeg);;"
            "Все файлы (*)"
        )

        if not file_path:
            return

        try:
            # Проверяем, что изображение действительно открывается
            with Image.open(file_path) as img:
                img.verify()

            self.logo_path = file_path
            self.logo_edit.setText(os.path.basename(file_path))

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть изображение:\n{e}"
            )

    # ==============================================================
    # ИЗМЕНЕНИЕ РАСПОЛОЖЕНИЯ
    # ==============================================================

    def position_changed(self, index):
        is_tile = index == 5

        self.tile_group.setEnabled(is_tile)

        # Отступы нужны только для четырёх углов.
        # Для центра и замощения они не используются.
        margins_enabled = index in (0, 1, 2, 3)

        self.margin_x.setEnabled(margins_enabled)
        self.margin_y.setEnabled(margins_enabled)

    # ==============================================================
    # ПРОВЕРКА
    # ==============================================================

    def validate_and_accept(self):

        if not self.logo_path:
            QMessageBox.warning(
                self,
                "Внимание",
                "Сначала выберите логотип."
            )
            return

        if not os.path.exists(self.logo_path):
            QMessageBox.warning(
                self,
                "Внимание",
                "Файл логотипа не найден."
            )
            return

        self.accept()

    # ==============================================================
    # НАСТРОЙКИ
    # ==============================================================

    def get_settings(self):

        positions = [
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
            "center",
            "tile"
        ]

        return {
            "logo_path": self.logo_path,

            "position": positions[
                self.position_combo.currentIndex()
            ],

            "margin_x": self.margin_x.value(),
            "margin_y": self.margin_y.value(),

            "tile_horizontal": self.tile_horizontal.value(),
            "tile_vertical": self.tile_vertical.value(),

            "logo_size": self.logo_size.value(),

            "rotation": self.rotation.value(),

            "opacity": self.opacity.value(),

            "range": self.pages_combo.currentText()
        }