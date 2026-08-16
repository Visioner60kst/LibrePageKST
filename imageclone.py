from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor

class CloneLabel(QLabel):
    def __init__(self, pixmap):
        super().__init__()
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        
        # Set the cursor in the form of a cross
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False
        self.selected_rect = QRect()
        
        # Drawing pixmap taking into account the initial scale
        self.update_pixmap()

    def update_pixmap(self):
        if self.original_pixmap.isNull():
            return
        
        # Calculate the new size
        new_w = int(self.original_pixmap.width() * self.scale_factor)
        new_h = int(self.original_pixmap.height() * self.scale_factor)
        
        if new_w == 0 or new_h == 0:
            return

        scaled_pixmap = self.original_pixmap.scaled(
            new_w, new_h, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        self.resize(scaled_pixmap.size())
        
        # Reset selection when zooming, 
        # to avoid visual problems with coordinate mismatch
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.selected_rect = QRect()
        self.is_drawing = False
        self.update()

    def set_scale(self, factor):
        self.scale_factor = factor
        self.update_pixmap()
        
    def get_scale(self):
        return self.scale_factor

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.end_point = event.pos()
            self.is_drawing = False
            self.selected_rect = QRect(self.start_point, self.end_point).normalized()
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Setting the highlight line style
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        if self.is_drawing:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)
        elif not self.selected_rect.isNull():
            painter.drawRect(self.selected_rect)

    def get_normalized_rect(self):
        if self.selected_rect.isNull():
            return None
        w = self.pixmap().width()
        h = self.pixmap().height()
        
        # Returning relative coordinates (from 0 to 1)
        # Since the width and height are taken from the current (scaled) pixmap,
        # the coordinates will always be correct relative to the original image
        rx = self.selected_rect.x() / w
        ry = self.selected_rect.y() / h
        rw = self.selected_rect.width() / w
        rh = self.selected_rect.height() / h
        return (rx, ry, rw, rh)


class ImageCloneDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Photo cloning")
        self.resize(900, 700)
        self.rect_ratio = None

        layout = QVBoxLayout(self)
        
        inst_label = QLabel("Hold down the left mouse button and select the area with the photo to clone.")
        inst_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(inst_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.clone_label = CloneLabel(pixmap)
        self.scroll_area.setWidget(self.clone_label)
        layout.addWidget(self.scroll_area)
        
        # Automatically adjust the scale so that the page fits in the window when opened
        if not pixmap.isNull():
            w_avail = 850.0  # Available window width including padding
            h_avail = 550.0  # Available window height taking into account indents
            scale_w = w_avail / pixmap.width()
            scale_h = h_avail / pixmap.height()
            
            initial_scale = min(scale_w, scale_h)
            # If the sheet is small, do not stretch it further 100% (the original)
            initial_scale = min(1.0, initial_scale)
            self.clone_label.set_scale(initial_scale)

        btn_layout = QHBoxLayout()
        
        # Zoom buttons + And -
        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedSize(30, 30)
        self.btn_zoom_out.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(30, 30)
        self.btn_zoom_in.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        self.btn_apply = QPushButton("Clone selection")
        self.btn_apply.setStyleSheet("background-color: #009688; color: white; font-weight: bold; font-size: 14px; padding: 5px;")
        self.btn_apply.clicked.connect(self.on_apply)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        # Button Layout
        btn_layout.addWidget(self.btn_zoom_out)
        btn_layout.addWidget(self.btn_zoom_in)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def zoom_in(self):
        current_scale = self.clone_label.get_scale()
        # Limiting the maximum approach
        if current_scale < 5.0:
            self.clone_label.set_scale(current_scale * 1.2)

    def zoom_out(self):
        current_scale = self.clone_label.get_scale()
        # Limiting the minimum distance
        if current_scale > 0.1:
            self.clone_label.set_scale(current_scale / 1.2)

    def on_apply(self):
        self.rect_ratio = self.clone_label.get_normalized_rect()
        self.accept()

    def get_settings(self):
        return {
            'rect_ratio': self.rect_ratio
        }