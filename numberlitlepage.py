from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap
from PyQt6.QtCore import Qt

def add_number_to_pixmap(pixmap, page_number):
    """
    Overlays the page number on QPixmap.
    """
    result_pixmap = pixmap.copy()
    painter = QPainter(result_pixmap)
    
    # Font settings: size has become smaller (0.5 instead of 0.6)
    font_size = int(result_pixmap.height() * 0.5)
    font = QFont("Arial", font_size, QFont.Weight.Bold)
    painter.setFont(font)
    
    # Color: darker and less transparent
    # RGB(80, 80, 80) - dark gray, almost black
    # Alpha channel 180 (from 255) - less transparent than it was before
    painter.setPen(QColor(80, 80, 80, 180))
    
    # Drawing text in the center
    painter.drawText(result_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(page_number))
    
    painter.end()
    return result_pixmap