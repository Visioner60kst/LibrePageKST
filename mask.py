from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QColor

# Кастомный QLabel для рисования прямоугольника мышью
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
            # Рисуем красную рамку для наглядности при выделении
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
            # Рисуем полупрозрачную белую заливку, чтобы было понятно, что мы скрываем
            painter.setBrush(QColor(255, 255, 255, 150))
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)

    def get_rect_ratio(self):
        """Возвращает координаты выделения в виде процентов от ширины/высоты (от 0.0 до 1.0)"""
        if not self.start_point or not self.end_point:
            return None
        rect = QRect(self.start_point, self.end_point).normalized()
        w = self.pixmap().width()
        h = self.pixmap().height()
        return (rect.x() / w, rect.y() / h, rect.width() / w, rect.height() / h)

class MaskPageDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ДОБАВИТЬ ПРЯМОУГОЛЬНИК")
        
        # Устанавливаем фиксированный размер окна программы
        self.setFixedSize(850, 700)
        
        layout = QVBoxLayout(self)
        
        # Инструкция
        info = QLabel("Выделите мышкой область, которую хотите скрыть (залить белым):")
        layout.addWidget(info)
        
        # Масштабируем изображение, чтобы оно всегда помещалось в наше окно
        # сохраняя пропорции и сглаживая качество
        max_w = 800
        max_h = 550
        scaled_pixmap = pixmap.scaled(
            max_w, max_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Виджет рисования (передаем уже отмасштабированный pixmap)
        self.label = DrawableLabel(scaled_pixmap)
        self.label.setCursor(Qt.CursorShape.CrossCursor)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Выбор страниц
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Скрыть на текущей странице", 
            "Скрыть на всех страницах"
        ])
        layout.addWidget(self.mode_combo)
        
        # Кнопки
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
            'rect_ratio': self.label.get_rect_ratio()
        }