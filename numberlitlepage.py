from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap
from PyQt6.QtCore import Qt

def add_number_to_pixmap(pixmap, page_number):
    """
    Накладывает номер страницы на QPixmap.
    """
    result_pixmap = pixmap.copy()
    painter = QPainter(result_pixmap)
    
    # Настройка шрифта: размер стал меньше (0.5 вместо 0.6)
    font_size = int(result_pixmap.height() * 0.5)
    font = QFont("Arial", font_size, QFont.Weight.Bold)
    painter.setFont(font)
    
    # Цвет: более темный и менее прозрачный
    # RGB(80, 80, 80) - темно-серый, почти черный
    # Альфа-канал 180 (из 255) - менее прозрачный, чем был раньше
    painter.setPen(QColor(80, 80, 80, 180))
    
    # Отрисовка текста по центру
    painter.drawText(result_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(page_number))
    
    painter.end()
    return result_pixmap