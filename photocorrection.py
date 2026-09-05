from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt

class PhotoCorrectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Коррекция фото")
        self.setModal(True)
        self.resize(300, 200)

        layout = QVBoxLayout(self)

        # Яркость
        layout.addWidget(QLabel("Яркость:"))
        self.slider_bright = self.create_slider()
        layout.addWidget(self.slider_bright)

        # Контрастность
        layout.addWidget(QLabel("Контрастность:"))
        self.slider_contrast = self.create_slider()
        layout.addWidget(self.slider_contrast)

        # Насыщенность
        layout.addWidget(QLabel("Насыщенность:"))
        self.slider_saturation = self.create_slider()
        layout.addWidget(self.slider_saturation)

        # Кнопка Применить
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

        self.settings = {"brightness": 1.0, "contrast": 1.0, "saturation": 1.0}

    def create_slider(self):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-100, 100)
        slider.setValue(0)
        return slider

    def get_settings(self):
        # Преобразуем значения ползунков (-100..100) в коэффициенты (0..2.0)
        # 0 -> 1.0 (оригинал), -100 -> 0.0 (минимум), 100 -> 2.0 (максимум)
        return {
            "brightness": 1.0 + (self.slider_bright.value() / 100.0),
            "contrast": 1.0 + (self.slider_contrast.value() / 100.0),
            "saturation": 1.0 + (self.slider_saturation.value() / 100.0)
        }