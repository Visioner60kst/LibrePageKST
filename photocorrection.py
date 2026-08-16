from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt

class PhotoCorrectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Photo correction")
        self.setModal(True)
        self.resize(300, 200)

        layout = QVBoxLayout(self)

        # Brightness
        layout.addWidget(QLabel("Brightness:"))
        self.slider_bright = self.create_slider()
        layout.addWidget(self.slider_bright)

        # Contrast
        layout.addWidget(QLabel("Contrast:"))
        self.slider_contrast = self.create_slider()
        layout.addWidget(self.slider_contrast)

        # Saturation
        layout.addWidget(QLabel("Saturation:"))
        self.slider_saturation = self.create_slider()
        layout.addWidget(self.slider_saturation)

        # Apply button
        self.btn_apply = QPushButton("APPLY")
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
        # Converting the slider values (-100..100) into odds (0..2.0)
        # 0 -> 1.0 (original), -100 -> 0.0 (minimum), 100 -> 2.0 (maximum)
        return {
            "brightness": 1.0 + (self.slider_bright.value() / 100.0),
            "contrast": 1.0 + (self.slider_contrast.value() / 100.0),
            "saturation": 1.0 + (self.slider_saturation.value() / 100.0)
        }