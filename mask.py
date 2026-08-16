from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QColor

# Custom QLabel to draw a rectangle with the mouse
class DrawableLabel(QLabel):
    def __init__(self, pixmap):
        super().__init__()
        self.setPixmap(pixmap)
        self.drawing = False
        self.start_point = None
        self.end_point = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self.end_point = event.pos()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.start_point and self.end_point:
            painter = QPainter(self)
            # Draw a red frame for clarity when selecting
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
            # Draw a translucent white fill to make it clear what we are hiding
            painter.setBrush(QColor(255, 255, 255, 150))
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)

    def get_rect_ratio(self):
        """Returns the coordinates of the selection as a percentage of the width/heights (from 0.0 to 1.0)"""
        if not self.start_point or not self.end_point:
            return None
        rect = QRect(self.start_point, self.end_point).normalized()
        w = self.pixmap().width()
        h = self.pixmap().height()
        return (rect.x() / w, rect.y() / h, rect.width() / w, rect.height() / h)

class MaskPageDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ADD RECTANGLE")
        
        # Set a fixed size of the program window
        self.setFixedSize(850, 700)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel("Select with your mouse the area you want to hide (fill with white):")
        layout.addWidget(info)
        
        # We scale the image so that it always fits in our window
        # maintaining proportions and smoothing quality
        max_w = 800
        max_h = 550
        scaled_pixmap = pixmap.scaled(
            max_w, max_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Drawing widget (we transmit the already scaled one pixmap)
        self.label = DrawableLabel(scaled_pixmap)
        self.label.setCursor(Qt.CursorShape.CrossCursor)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Selecting pages
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Hide on current page", 
            "Hide on all pages"
        ])
        layout.addWidget(self.mode_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Apply")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_settings(self):
        return {
            'mode': self.mode_combo.currentText(),
            'rect_ratio': self.label.get_rect_ratio()
        }