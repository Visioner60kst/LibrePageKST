import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt

class BaseRuler(QWidget):
    def __init__(self, orientation, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.zoom_factor = 1.0  # Pixels per millimeter
        self.is_active = False  # Draw flag (for active sheet)
        self.page_size_mm = 0   # Page size in mm
        
        # Set a fixed ruler thickness
        if self.orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(20)
        else:
            self.setFixedWidth(20)

    def set_zoom(self, pixels_per_mm):
        self.zoom_factor = pixels_per_mm
        self.update()

    def set_active(self, state):
        self.is_active = state
        self.update()

    def set_page_size(self, size_mm):
        """Method to set actual page size in mm"""
        self.page_size_mm = size_mm
        self.update()

    def paintEvent(self, event):
        # If the page is not active, we don't draw anything, 
        # but the widget takes its place so that the layout does not jump.
        if not self.is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.zoom_factor <= 0:
            return

        # CALCULATING THE BORDER FOR BACKGROUND AND FRAME
        # If the page size is specified, draw the background only up to it
        if self.page_size_mm > 0:
            # Converting page size to pixels
            bg_extent = int(self.page_size_mm * self.zoom_factor)
        else:
            bg_extent = self.width() if self.orientation == Qt.Orientation.Horizontal else self.height()

        # RULER BACKGROUND (We draw only within bg_extent)
        if self.orientation == Qt.Orientation.Horizontal:
            painter.fillRect(0, 0, bg_extent, self.height(), QColor("#f0f0f0"))
        else:
            painter.fillRect(0, 0, self.width(), bg_extent, QColor("#f0f0f0"))
        
        # FRAME (We draw only to the edge of the page, and not to the edge of the entire widget)
        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1))
        if self.orientation == Qt.Orientation.Horizontal:
            painter.drawLine(0, self.height() - 1, bg_extent, self.height() - 1)
        else:
            painter.drawLine(self.width() - 1, 0, self.width() - 1, bg_extent)

        # Pen and font settings for tick marks
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        font = QFont("Arial", 6)
        painter.setFont(font)

        # Calculating the limit for drawing marks
        if self.page_size_mm > 0:
            limit_mm = int(self.page_size_mm)
        else:
            max_px = self.width() if self.orientation == Qt.Orientation.Horizontal else self.height()
            limit_mm = int(max_px / self.zoom_factor)

        # Drawing risks and numbers
        for mm in range(0, limit_mm + 1):
            pos = int(mm * self.zoom_factor)
            
            # Check not to draw outside bg_extent
            if pos > bg_extent:
                break
            
            if self.orientation == Qt.Orientation.Horizontal:
                if mm % 10 == 0:  # Centimeters
                    painter.drawLine(pos, 0, pos, self.height())
                    # The text should not go beyond bg_extent
                    if pos + 2 < bg_extent:
                        painter.drawText(pos + 2, 10, str(mm))
                elif mm % 5 == 0:  # Half a centimeter (5 mm)
                    painter.drawLine(pos, self.height() // 2, pos, self.height())
                else:  # Millimeters
                    painter.drawLine(pos, self.height() - 5, pos, self.height())
            else:
                if mm % 10 == 0:
                    painter.drawLine(0, pos, self.width(), pos)
                    # The text should not go beyond bg_extent
                    if pos + 8 < bg_extent:
                        painter.drawText(2, pos + 8, str(mm))
                elif mm % 5 == 0:
                    painter.drawLine(self.width() // 2, pos, self.width(), pos)
                else:
                    painter.drawLine(self.width() - 5, pos, self.width(), pos)

class HorizontalRuler(BaseRuler):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)

class VerticalRuler(BaseRuler):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)