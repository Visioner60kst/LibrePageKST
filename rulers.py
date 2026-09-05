import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt

class BaseRuler(QWidget):
    def __init__(self, orientation, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.zoom_factor = 1.0  # Пикселей на миллиметр
        self.is_active = False  # Флаг отрисовки (для активного листа)
        self.page_size_mm = 0   # Размер страницы в мм
        
        # Задаем фиксированную толщину линеек
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
        """Метод для установки реального размера страницы в мм"""
        self.page_size_mm = size_mm
        self.update()

    def paintEvent(self, event):
        # Если страница не активна, мы ничего не рисуем, 
        # но виджет занимает свое место, чтобы верстка не прыгала.
        if not self.is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.zoom_factor <= 0:
            return

        # ВЫЧИСЛЕНИЕ ГРАНИЦЫ ДЛЯ ПОДЛОЖКИ И РАМКИ
        # Если задан размер страницы, рисуем подложку только до него
        if self.page_size_mm > 0:
            # Преобразуем размер страницы в пиксели
            bg_extent = int(self.page_size_mm * self.zoom_factor)
        else:
            bg_extent = self.width() if self.orientation == Qt.Orientation.Horizontal else self.height()

        # ФОН ЛИНЕЙКИ (Рисуем только в пределах bg_extent)
        if self.orientation == Qt.Orientation.Horizontal:
            painter.fillRect(0, 0, bg_extent, self.height(), QColor("#f0f0f0"))
        else:
            painter.fillRect(0, 0, self.width(), bg_extent, QColor("#f0f0f0"))
        
        # РАМКА (Рисуем только до края страницы, а не до края всего виджета)
        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1))
        if self.orientation == Qt.Orientation.Horizontal:
            painter.drawLine(0, self.height() - 1, bg_extent, self.height() - 1)
        else:
            painter.drawLine(self.width() - 1, 0, self.width() - 1, bg_extent)

        # Настройки пера и шрифта для делений
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        font = QFont("Arial", 6)
        painter.setFont(font)

        # Вычисляем предел отрисовки рисок
        if self.page_size_mm > 0:
            limit_mm = int(self.page_size_mm)
        else:
            max_px = self.width() if self.orientation == Qt.Orientation.Horizontal else self.height()
            limit_mm = int(max_px / self.zoom_factor)

        # Рисуем риски и цифры
        for mm in range(0, limit_mm + 1):
            pos = int(mm * self.zoom_factor)
            
            # Проверка, чтобы не рисовать за пределами bg_extent
            if pos > bg_extent:
                break
            
            if self.orientation == Qt.Orientation.Horizontal:
                if mm % 10 == 0:  # Сантиметры
                    painter.drawLine(pos, 0, pos, self.height())
                    # Текст не должен вылезать за пределы bg_extent
                    if pos + 2 < bg_extent:
                        painter.drawText(pos + 2, 10, str(mm))
                elif mm % 5 == 0:  # Половина сантиметра (5 мм)
                    painter.drawLine(pos, self.height() // 2, pos, self.height())
                else:  # Миллиметры
                    painter.drawLine(pos, self.height() - 5, pos, self.height())
            else:
                if mm % 10 == 0:
                    painter.drawLine(0, pos, self.width(), pos)
                    # Текст не должен вылезать за пределы bg_extent
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