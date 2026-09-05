import sys
import fitz  # PyMuPDF
import subprocess
import os
import traceback
import tempfile
import platform
import shutil
from PIL import Image, ImageEnhance # Необходима для коррекции
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                             QSlider, QMessageBox, QFileDialog, QGridLayout,
                             QLineEdit, QSplitter, QSizePolicy, QMenu, QSplashScreen,
                             QDialog, QComboBox, QFrame, QTextEdit)
from PyQt6.QtCore import Qt, QRect, QPoint, QEvent, QMimeData, QTimer
from PyQt6.QtGui import QImage, QPixmap, QIntValidator, QDrag, QPainter, QPen, QColor

# Импортируем линейки из нашего нового модуля
from rulers import HorizontalRuler, VerticalRuler

# Импортируем новые модули
from PyQt6.QtCore import Qt, QRect, QPoint, QEvent, QMimeData, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap, QIntValidator, QDrag, QPainter, QPen, QColor, QIcon
from pagemouse import ThumbnailHandler
from pagezoom import PageZoom
from imagetopdf import ImageToPdfDialog
from files import FilesPanel
from booklet import BookletDialog
from booklet2 import Booklet2Dialog  # НОВЫЙ МОДУЛЬ: Буклет в 2 сгиба
from numberlitlepage import add_number_to_pixmap
from cancel import HistoryManager
from cutpage import CutPageDialog
from connectpage import merge_pdfs_dialog
from revers import reverse_pages_action
from Cheredov import cheredov_pages_action
from Rotatepage import RotatePageDialog
from numberpage import NumberPageDialog
from move import MovePageDialog
from mask import MaskPageDialog
from multiply import MultiplyDialog
from size import SizePageDialog
from crop import CropPageDialog
from SPUSK import SpuskDialog
from scale import ScalePageDialog
from export import ExportDialog
from background import BackgroundDialog
from convertcolor import ConvertColorDialog
from curves import CurvesDialog
from imageclone import ImageCloneDialog
from imageselect import ImageSelectionManager
from photocorrection import PhotoCorrectionDialog # НОВЫЙ МОДУЛЬ
from openeditphoto import ExternalEditorDialog # НОВЫЙ МОДУЛЬ
from fields import FieldsDialog # НОВЫЙ МОДУЛЬ: Поля+
from logopage import LogoPageDialog
from pdftransfer import PDFTransferDialog

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ИМПОРТ МОДУЛЯ ПЕЧАТИ (замените PrintDialog/start_print на то имя класс/функции, которое используется в print.py)
import print as print_module


# Кастомный виджет для отображения страницы с возможностью выделения и клика
class PageWidget(QWidget):

    def __init__(self, pixmap, page_index, callback, pixels_per_mm=1.0, show_rulers=True, page_w_mm=0, page_h_mm=0, zoom_factor=1.0, selection_manager=None):
        super().__init__()
        self.page_index = page_index
        self.callback = callback
        self.is_selected = False  # Для скролла
        self.is_active = False
        self.show_rulers = show_rulers # Флаг для контроля отображения линеек
        self.zoom_factor = zoom_factor
        self.selection_manager = selection_manager
        
        # Отрисовка синей рамки выделенного фото, если оно на этой странице
        if self.selection_manager and self.selection_manager.selected_page_index == self.page_index and self.selection_manager.selected_bbox:
            painter = QPainter(pixmap)
            pen = QPen(QColor(0, 0, 255)) # Синяя рамка
            pen.setWidth(3)
            painter.setPen(pen)
            
            bbox = self.selection_manager.selected_bbox
            # Переводим координаты из PDF points в пиксели QPixmap
            x = bbox.x0 * self.zoom_factor
            y = bbox.y0 * self.zoom_factor
            w = (bbox.x1 - bbox.x0) * self.zoom_factor
            h = (bbox.y1 - bbox.y0) * self.zoom_factor
            
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.end()

        # Настраиваем сетку для размещения линеек и изображения страницы
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Инициализируем линейки
        self.h_ruler = HorizontalRuler()
        self.v_ruler = VerticalRuler()
        self.h_ruler.set_zoom(pixels_per_mm)
        self.v_ruler.set_zoom(pixels_per_mm)

        # FIX: Передаем физический размер страницы в линейки
        if hasattr(self.h_ruler, 'set_page_size'):
            self.h_ruler.set_page_size(page_w_mm)
        if hasattr(self.v_ruler, 'set_page_size'):
            self.v_ruler.set_page_size(page_h_mm)
        
        # Изображение самого листа
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ==========================================
        # СЛОЙ ПРЕДПРОСМОТРА КАДРИРОВАНИЯ
        # ==========================================

        self.crop_overlay = CropPreviewOverlay(self.image_label)
        self.crop_overlay.set_page_size(
            page_w_mm,
            page_h_mm
        )

        self.crop_overlay.setGeometry(
            0,
            0,
            self.image_label.width(),
            self.image_label.height()
        )

        self.crop_overlay.hide()
        
        # Размещаем элементы: (0, 0) остается пустым (угол)
        # (0, 1) - гориз. линейка, (1, 0) - вертик. линейка, (1, 1) - сам лист
        self.layout.addWidget(self.h_ruler, 0, 1)
        self.layout.addWidget(self.v_ruler, 1, 0)
        self.layout.addWidget(self.image_label, 1, 1)
        
        self.update_style()

                # Размер PageWidget строго соответствует реальному размеру страницы
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )

        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )

    def update_style(self):
        # Рамка должна находиться только вокруг реального листа,
        # а не растягивать весь PageWidget до размера самой большой страницы.

        if self.is_active:
            self.image_label.setStyleSheet(
                "QLabel {"
                "border: 4px solid #0000FF;"
                "}"
            )
        elif self.is_selected:
            self.image_label.setStyleSheet(
                "QLabel {"
                "border: 2px solid blue;"
                "}"
            )
        else:
            self.image_label.setStyleSheet(
                "QLabel {"
                "border: 2px solid transparent;"
                "}"
            )

        rulers_active = self.is_active and self.show_rulers
        self.h_ruler.set_active(rulers_active)
        self.v_ruler.set_active(rulers_active)

    def set_selected(self, selected):
        if self.is_selected != selected:
            self.is_selected = selected
            self.update_style()

    def set_active(self, active):
        if self.is_active != active:
            self.is_active = active
            self.update_style()
            
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Вычисляем позицию клика относительно самой картинки (исключая линейки)
            pos_in_image = self.image_label.mapFrom(self, event.pos())
            if 0 <= pos_in_image.x() < self.image_label.width() and 0 <= pos_in_image.y() < self.image_label.height():
                self.callback(self.page_index, pos_in_image.x(), pos_in_image.y())
            else:
                self.callback(self.page_index)


# Вспомогательный класс для кликабельных эскизов
class ClickableThumbnail(QLabel):

    def __init__(self, page_index, callback, handler, main_window=None):
        super().__init__()

        self.page_index = page_index
        self.callback = callback
        self.handler = handler
        self.main_window = main_window

        self.is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()
        self.setAcceptDrops(True) # НОВОЕ: Разрешаем прием файлов Drag&Drop

    def update_style(self):
        if self.is_active:
            self.setStyleSheet("border: 3px solid #0000FF;")
        else:
            self.setStyleSheet("border: 2px solid transparent;")

    def set_active(self, active):
        if self.is_active != active:
            self.is_active = active
            self.update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos() # Запоминаем позицию для перетаскивания
            self.callback(self.page_index)
        elif event.button() == Qt.MouseButton.RightButton:
            self.handler.handle_context_menu(self, event.pos())

    # НОВОЕ: Обрабатываем перемещение мыши для старта Drag & Drop
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, 'drag_start_pos'):
            return
        # Проверяем, что курсор сместился достаточно для старта перетаскивания
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.page_index))
        drag.setMimeData(mime_data)
        
        # Создаем полупрозрачный эскиз для эффекта перетаскивания
        pixmap = self.pixmap()
        if pixmap:
            drag.setPixmap(pixmap.scaledToWidth(80, Qt.TransformationMode.SmoothTransformation))
            drag.setHotSpot(QPoint(drag.pixmap().width() // 2, drag.pixmap().height() // 2))
            
        drag.exec(Qt.DropAction.MoveAction)

    # НОВОЕ: Позволяем перетаскивать данные над этим виджетом
        # ==========================================================
    # ПРИЁМ СТРАНИЦ ИЗ МОДУЛЯ «ОБМЕН СТРАНИЦАМИ»
    # ==========================================================

    def dragEnterEvent(self, event):

        mime = event.mimeData()

        # Страница из pdftransfer.py
        if mime.hasFormat("application/x-librepage-pdf-page"):
            event.acceptProposedAction()
            return

        # Старый Drag & Drop внутри LibrePage
        if mime.hasText():
            event.acceptProposedAction()
            return

        event.ignore()


    def dragMoveEvent(self, event):

        mime = event.mimeData()

        # Страница из pdftransfer.py
        if mime.hasFormat("application/x-librepage-pdf-page"):
            event.acceptProposedAction()
            return

        # Старый Drag & Drop внутри LibrePage
        if mime.hasText():
            event.acceptProposedAction()
            return

        event.ignore()


    def dropEvent(self, event):

        mime = event.mimeData()

        # ======================================================
        # СТРАНИЦЫ ИЗ МОДУЛЯ «ОБМЕН СТРАНИЦАМИ»
        # ======================================================

        if mime.hasFormat("application/x-librepage-pdf-page"):

            try:

                payload = bytes(
                    mime.data(
                        "application/x-librepage-pdf-page"
                    )
                ).decode("utf-8")

                # Формат:
                # полный путь к PDF
                # номера страниц через запятую
                #
                # Например:
                # D:\test.pdf
                # 2,3,4,5

                source_path, source_pages_text = payload.split(
                    "\n",
                    1
                )

                source_path = os.path.abspath(source_path)

                # Получаем список страниц
                source_pages = [
                    int(x.strip())
                    for x in source_pages_text.split(",")
                    if x.strip()
                ]

            except Exception:

                traceback.print_exc()
                event.ignore()
                return

            # Передаём список страниц главному окну LibrePage
            main_window = self.main_window

            if main_window is not None:

                if main_window.handle_pdftransfer_drop(
                    source_path,
                    source_pages,
                    self.page_index
                ):

                    event.acceptProposedAction()
                    return

            event.ignore()
            return

        # ======================================================
        # СТАРЫЙ DRAG & DROP LIBREPAGE
        # ======================================================

        source_index_str = mime.text()

        if source_index_str.isdigit():

            source_index = int(source_index_str)
            target_index = self.page_index

            if source_index != target_index:

                if hasattr(
                    self.handler,
                    "handle_drag_drop"
                ):
                    self.handler.handle_drag_drop(
                        source_index,
                        target_index
                    )

                event.acceptProposedAction()
                return

        event.ignore()


# Диалоговое окно для подмены отсутствующих шрифтов
class MissingFontDialog(QDialog):
    def __init__(self, missing_font_name, system_fonts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Отсутствует шрифт!")
        self.setModal(True)
        self.resize(550, 150)
        self.result_action = "skip"
        self.selected_font_path = None
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(f"<b>Внимание!</b> При конвертации обнаружен отсутствующий шрифт:<br>"
                      f"<span style='color: #d32f2f; font-size: 14px;'><b>{missing_font_name}</b></span><br><br>"
                      f"Шрифт не встроен в PDF и отсутствует в вашей системе.<br>"
                      f"Выберите системный шрифт для замены, либо пропустите этот лист.", self)
        layout.addWidget(lbl)
        
        btn_layout = QHBoxLayout()
        
        # Левая часть (список и кнопка ЗАМЕНИТЬ)
        left_layout = QHBoxLayout()
        self.combo_fonts = QComboBox(self)
        self.combo_fonts.setMinimumWidth(200)
        for name, path in system_fonts.items():
            self.combo_fonts.addItem(name, path)
            
        btn_replace = QPushButton("ЗАМЕНИТЬ", self)
        btn_replace.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
        btn_replace.clicked.connect(self.on_replace)
        
        left_layout.addWidget(self.combo_fonts)
        left_layout.addWidget(btn_replace)
        
        # Правая часть (кнопка ПРОПУСТИТЬ ЛИСТ)
        btn_skip = QPushButton("ПРОПУСТИТЬ ЛИСТ", self)
        btn_skip.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
        btn_skip.clicked.connect(self.on_skip)
        
        btn_layout.addLayout(left_layout)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_skip)
        
        layout.addLayout(btn_layout)
        
    def on_replace(self):
        self.result_action = "replace"
        self.selected_font_path = self.combo_fonts.currentData()
        self.accept()
        
    def on_skip(self):
        self.result_action = "skip"
        self.accept()
        
    def on_skip(self):
        self.result_action = "skip"
        self.accept()

class LicenseViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Лицензия")
        self.setMinimumSize(400, 500)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        license_path = os.path.join(script_dir, "LICENSE.txt")
        if os.path.exists(license_path):
            with open(license_path, "r", encoding="utf-8") as f:
                self.text_edit.setPlainText(f.read())
        else:
            self.text_edit.setPlainText("Файл LICENSE.txt не найден.")
        layout.addWidget(QLabel("Лицензионное соглашение:"))
        layout.addWidget(self.text_edit)
        
        
class CropPreviewOverlay(QWidget):
    """
    Временный слой предварительного просмотра кадрирования.

    Показывает линии там, где будет выполнен срез.
    Ничего не изменяет в самой странице PDF.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground,
            True
        )

        self.top_mm = 0.0
        self.bottom_mm = 0.0
        self.left_mm = 0.0
        self.right_mm = 0.0

        self.page_width_mm = 0.0
        self.page_height_mm = 0.0

        self.setVisible(False)

    def set_page_size(self, width_mm, height_mm):
        """
        Передаём реальный размер страницы PDF в миллиметрах.
        """

        self.page_width_mm = float(width_mm)
        self.page_height_mm = float(height_mm)

        self.update()

    def set_crop_values(
        self,
        top,
        bottom,
        left,
        right
    ):
        """
        Устанавливает значения кадрирования.
        """

        self.top_mm = max(0.0, float(top))
        self.bottom_mm = max(0.0, float(bottom))
        self.left_mm = max(0.0, float(left))
        self.right_mm = max(0.0, float(right))

        has_lines = (
            self.top_mm > 0
            or self.bottom_mm > 0
            or self.left_mm > 0
            or self.right_mm > 0
        )

        self.setVisible(has_lines)

        self.raise_()
        self.update()

    def clear(self):
        """
        Полностью убрать линии.
        """

        self.top_mm = 0.0
        self.bottom_mm = 0.0
        self.left_mm = 0.0
        self.right_mm = 0.0

        self.setVisible(False)
        self.update()

    def paintEvent(self, event):

        if not self.isVisible():
            return

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            False
        )

        # Серый цвет линии
        pen = QPen(
            QColor(120, 120, 120)
        )

        # Толщина линии
        pen.setWidth(2)

        # Пунктир
        pen.setStyle(
            Qt.PenStyle.DashLine
        )

        painter.setPen(pen)

        width = self.width()
        height = self.height()

        # --------------------------------------------------
        # СВЕРХУ
        # --------------------------------------------------

        if (
            self.top_mm > 0
            and self.page_height_mm > 0
        ):

            y = (
                self.top_mm
                / self.page_height_mm
                * height
            )

            painter.drawLine(
                0,
                int(y),
                width,
                int(y)
            )

        # --------------------------------------------------
        # СНИЗУ
        # --------------------------------------------------

        if (
            self.bottom_mm > 0
            and self.page_height_mm > 0
        ):

            y = (
                height
                - (
                    self.bottom_mm
                    / self.page_height_mm
                    * height
                )
            )

            painter.drawLine(
                0,
                int(y),
                width,
                int(y)
            )

        # --------------------------------------------------
        # СЛЕВА
        # --------------------------------------------------

        if (
            self.left_mm > 0
            and self.page_width_mm > 0
        ):

            x = (
                self.left_mm
                / self.page_width_mm
                * width
            )

            painter.drawLine(
                int(x),
                0,
                int(x),
                height
            )

        # --------------------------------------------------
        # СПРАВА
        # --------------------------------------------------

        if (
            self.right_mm > 0
            and self.page_width_mm > 0
        ):

            x = (
                width
                - (
                    self.right_mm
                    / self.page_width_mm
                    * width
                )
            )

            painter.drawLine(
                int(x),
                0,
                int(x),
                height
            )

        painter.end()

class BaseImposingModule(QMainWindow):

    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1300, 800)
        self.current_zoom = 100


        self.open_docs = {}
        self.doc = None
        self.pages_in_row = 1
        self.current_file_path = None
        self.page_widgets = []
        self.thumb_widgets = []
        self.active_page_index = -1
        self.rulers_enabled = True

        # НОВОЕ: Менеджер выделения фото
        self.image_selection_manager = ImageSelectionManager()
        self.is_image_select_mode = False
        
        # НОВОЕ: Хранение пути к внешнему редактору
        self.external_editor_path = None
        
        # Инициализируем обработчик мыши
        self.mouse_handler = ThumbnailHandler(self)
        
        # Модуль отмены действий
        self.history_manager = HistoryManager(self)
        
        # Список кнопок для управления стилями
        self.mode_buttons = []
        
        # Основной виджет
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Верхняя панель (переделана в групповую раскладку)
        top_bar_container = QVBoxLayout()
        top_bar_container.setContentsMargins(5, 5, 5, 5)

        top_row1 = QHBoxLayout()
        top_row2 = QHBoxLayout()
        
        # Устанавливаем расстояние между группами (10px) - ровно в 2 раза больше расстояния между кнопками (5px)
        top_row1.setSpacing(20)
        top_row2.setSpacing(20)

        # Стили
        btn_style = "background-color: #e0e0e0; color: black; font-weight: bold; border: 1px solid #999999; border-radius: 6px; padding: 5px 10px;"
        style_light_gray = btn_style
        style_dark_gray = btn_style
        group_title_style = "font-weight: bold; color: #555; font-size: 11px;"

        def create_group_layout(title, buttons):
            group_layout = QVBoxLayout()
            group_layout.setSpacing(2)
            
            lbl = QLabel(title.upper()) # Имя группы большими буквами
            lbl.setStyleSheet(group_title_style)
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            group_layout.addWidget(lbl)

            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(5) # Расстояние между кнопками 5px
            for btn in buttons:
                btn_layout.addWidget(btn)
            group_layout.addLayout(btn_layout)
            return group_layout

        # === СОЗДАНИЕ КНОПОК ===
        
        # Стилизация кнопок истории (так как они создаются внутри HistoryManager)
        self.history_manager.btn_undo.setStyleSheet(btn_style)
        self.history_manager.btn_redo.setStyleSheet(btn_style)

        # --- Кнопки Файл ---
        self.btn_open = QPushButton()
        self.btn_open.setIcon(QIcon(resource_path("resources/icon/open.png"
        )))
        self.btn_open.setIconSize(QSize(23, 23))
        self.btn_open.setToolTip("Открыть файл")
        self.btn_open.setStyleSheet(style_light_gray)
        self.btn_open.clicked.connect(self.open_file)

        self.btn_save = QPushButton()
        self.btn_save.setIcon(QIcon(resource_path("resources/icon/save.png"
        )))
        self.btn_save.setIconSize(QSize(23, 23))
        self.btn_save.setToolTip("Сохранить файл")
        self.btn_save.setStyleSheet(style_light_gray)
        self.btn_save.clicked.connect(self.save_file)

        self.btn_close = QPushButton()
        self.btn_close.setIcon(QIcon(resource_path("resources/icon/close.png"
        )))
        self.btn_close.setIconSize(QSize(23, 23))
        self.btn_close.setToolTip("Закрыть документ")
        self.btn_close.setStyleSheet(style_light_gray)
        self.btn_close.clicked.connect(self.close_document)

        self.btn_export = QPushButton()
        self.btn_export.setIcon(QIcon(resource_path("resources/icon/export.png"
        )))
        self.btn_export.setIconSize(QSize(23, 23))
        self.btn_export.setToolTip("PDF в Image")
        self.btn_export.setStyleSheet(style_light_gray)
        self.btn_export.clicked.connect(self.open_export_module)

        # --- Image в PDF ---
        self.btn_image_to_pdf = QPushButton()
        self.btn_image_to_pdf.setIcon(QIcon(resource_path("resources/icon/imagetopdf.png"
        )))
        self.btn_image_to_pdf.setIconSize(QSize(23, 23))
        self.btn_image_to_pdf.setToolTip(
            "Объединить изображения в PDF и открыть его в LibrePage"
        )
        self.btn_image_to_pdf.setStyleSheet(style_light_gray)
        self.btn_image_to_pdf.clicked.connect(self.open_image_to_pdf)

        
        self.btn_print = QPushButton()
        self.btn_print.setIcon(QIcon(resource_path("resources/icon/print.png"
        )))

        self.btn_print.setIconSize(QSize(23, 23))
        self.btn_print.setToolTip("Печать")
        self.btn_print.setStyleSheet(style_light_gray)
        self.btn_print.clicked.connect(self.open_print_module)

        # --- Кнопки Страницы ---
        self.btn_cut = QPushButton()
        self.btn_cut.setIcon(QIcon(resource_path("resources/icon/cutpage.png"
        )))
        self.btn_cut.setIconSize(QSize(23, 23))
        self.btn_cut.setToolTip("Разрезать")
        self.btn_cut.setStyleSheet(style_dark_gray)
        self.btn_cut.clicked.connect(self.open_cutpage_module)

        self.btn_merge = QPushButton()
        self.btn_merge.setIcon(QIcon(resource_path("resources/icon/connectpage.png"
        )))
        self.btn_merge.setIconSize(QSize(23, 23))
        self.btn_merge.setToolTip("Склеить")
        self.btn_merge.setStyleSheet(style_dark_gray)
        self.btn_merge.clicked.connect(self.open_merge_module)

        self.btn_reverse = QPushButton()
        self.btn_reverse.setIcon(QIcon(resource_path("resources/icon/revers.png"
        )))
        self.btn_reverse.setIconSize(QSize(23, 23))
        self.btn_reverse.setToolTip("Реверс")
        self.btn_reverse.setStyleSheet(style_dark_gray)
        self.btn_reverse.clicked.connect(self.open_reverse_module)

        self.btn_cheredov = QPushButton()
        self.btn_cheredov.setIcon(QIcon(resource_path("resources/icon/cheredov.png"
        )))
        self.btn_cheredov.setIconSize(QSize(23, 23))
        self.btn_cheredov.setToolTip("Чередование")
        self.btn_cheredov.setStyleSheet(style_dark_gray)
        self.btn_cheredov.clicked.connect(self.open_cheredov_module)

        self.btn_rotate = QPushButton()
        self.btn_rotate.setIcon(QIcon(resource_path("resources/icon/rotatepage.png"
        )))
        self.btn_rotate.setIconSize(QSize(23, 23))
        self.btn_rotate.setToolTip("Поворот")
        self.btn_rotate.setStyleSheet(style_dark_gray)
        self.btn_rotate.clicked.connect(self.open_rotate_module)

        self.btn_move = QPushButton()
        self.btn_move.setIcon(QIcon(resource_path("resources/icon/move.png"
        )))
        self.btn_move.setIconSize(QSize(23, 23))
        self.btn_move.setToolTip("Сдвиг")
        self.btn_move.setStyleSheet(style_dark_gray)
        self.btn_move.clicked.connect(self.open_move_module)

        self.btn_crop = QPushButton()
        self.btn_crop.setIcon(QIcon(resource_path("resources/icon/crop.png"
        )))
        self.btn_crop.setIconSize(QSize(23, 23))
        self.btn_crop.setToolTip("Кадрировать")
        self.btn_crop.setStyleSheet(style_dark_gray)
        self.btn_crop.clicked.connect(self.open_crop_module)
        
        # Новая кнопка Поля+
        self.btn_fields = QPushButton()
        self.btn_fields.setIcon(QIcon(resource_path("resources/icon/fields.png"
        )))
        self.btn_fields.setIconSize(QSize(23, 23))
        self.btn_fields.setToolTip("Поля+")
        self.btn_fields.setStyleSheet(style_dark_gray)
        self.btn_fields.clicked.connect(self.open_fields_module)

        # Обмен страницами
        self.btn_pdftransfer = QPushButton()
        self.btn_pdftransfer.setIcon(QIcon(resource_path("resources/icon/pdftransfer.png"
        )))
        self.btn_pdftransfer.setIconSize(QSize(23, 23))
        self.btn_pdftransfer.setToolTip("Обмен страницами")
        self.btn_pdftransfer.setStyleSheet(style_dark_gray)
        self.btn_pdftransfer.clicked.connect(self.open_pdftransfer_module)

        # --- Кнопки Конвертировать ---
        self.btn_convert_color = QPushButton()
        self.btn_convert_color.setIcon(QIcon(resource_path("resources/icon/convertcolor.png"
        )))
        self.btn_convert_color.setIconSize(QSize(23, 23))
        self.btn_convert_color.setToolTip("Цвета")
        self.btn_convert_color.setStyleSheet(style_dark_gray)
        self.btn_convert_color.clicked.connect(self.open_convertcolor_module)

        self.btn_curves = QPushButton()
        self.btn_curves.setIcon(QIcon(resource_path("resources/icon/curves.png"
        )))
        self.btn_curves.setIconSize(QSize(23, 23))
        self.btn_curves.setToolTip("Текст в кривые")
        self.btn_curves.setStyleSheet(style_dark_gray)
        self.btn_curves.clicked.connect(self.open_curves_module)

        # Формируем 1-й ряд (Файл | Страницы | Конвертировать)
        file_group = create_group_layout("Файл", [
            self.history_manager.btn_undo, 
            self.history_manager.btn_redo, 
            self.btn_open, self.btn_save, self.btn_close, self.btn_export, self.btn_image_to_pdf, self.btn_print
        ])
        top_row1.addLayout(file_group)

        pages_group = create_group_layout("Страницы", [
            self.btn_cut, self.btn_merge, self.btn_reverse, self.btn_cheredov, 
            self.btn_rotate, self.btn_move, self.btn_crop, self.btn_fields, self.btn_pdftransfer
        ])
        top_row1.addLayout(pages_group)

        convert_group = create_group_layout("Конвертировать", [self.btn_convert_color, self.btn_curves])
        top_row1.addLayout(convert_group)
        top_row1.addStretch()

        # --- Кнопки Макет ---
        self.btn_booklet = QPushButton()
        self.btn_booklet.setIcon(QIcon(resource_path("resources/icon/booklet.png"
        )))
        self.btn_booklet.setIconSize(QSize(23, 23))
        self.btn_booklet.setToolTip("Буклет")
        self.btn_booklet.setStyleSheet(style_light_gray)
        self.btn_booklet.clicked.connect(self.open_booklet_module)

        self.btn_booklet2 = QPushButton()
        self.btn_booklet2.setIcon(QIcon(resource_path("resources/icon/booklet2.png"
        )))
        self.btn_booklet2.setIconSize(QSize(23, 23))
        self.btn_booklet2.setToolTip("Буклет в 2 сгиба")
        self.btn_booklet2.setStyleSheet(style_light_gray)
        self.btn_booklet2.clicked.connect(self.open_booklet2_module)

        self.btn_spusk = QPushButton()
        self.btn_spusk.setIcon(QIcon(resource_path("resources/icon/SPUSK.png"
        )))
        self.btn_spusk.setIconSize(QSize(23, 23))
        self.btn_spusk.setToolTip("Спуск полос")
        self.btn_spusk.setStyleSheet(style_light_gray)
        self.btn_spusk.clicked.connect(self.open_spusk_module)

        self.btn_multiply = QPushButton()
        self.btn_multiply.setIcon(QIcon(resource_path("resources/icon/multiply.png"
        )))
        self.btn_multiply.setIconSize(QSize(23, 23))
        self.btn_multiply.setToolTip("Размножить")
        self.btn_multiply.setStyleSheet(style_light_gray)
        self.btn_multiply.clicked.connect(self.open_multiply_module)

        self.btn_number = QPushButton()
        self.btn_number.setIcon(QIcon(resource_path("resources/icon/numberpage.png"
        )))
        self.btn_number.setIconSize(QSize(23, 23))
        self.btn_number.setToolTip("Нумерация")
        self.btn_number.setStyleSheet(style_light_gray)
        self.btn_number.clicked.connect(self.open_number_module)

        self.btn_mask = QPushButton()
        self.btn_mask.setIcon(QIcon(resource_path("resources/icon/mask.png"
        )))
        self.btn_mask.setIconSize(QSize(23, 23))
        self.btn_mask.setToolTip("Скрыть")
        self.btn_mask.setStyleSheet(style_light_gray)
        self.btn_mask.clicked.connect(self.open_mask_module)

        self.btn_bg = QPushButton()
        self.btn_bg.setIcon(QIcon(resource_path("resources/icon/background.png"
        )))
        self.btn_bg.setIconSize(QSize(23, 23))
        self.btn_bg.setToolTip("Фон")
        self.btn_bg.setStyleSheet(style_light_gray)
        self.btn_bg.clicked.connect(self.open_background_module)

        # --- Кнопки Размер ---
        self.btn_resize = QPushButton()
        self.btn_resize.setIcon(QIcon(resource_path("resources/icon/scale.png"
        )))
        self.btn_resize.setIconSize(QSize(23, 23))
        self.btn_resize.setToolTip("Размер листа")
        self.btn_resize.setStyleSheet(style_dark_gray)
        self.btn_resize.clicked.connect(self.open_size_module)

        self.btn_scale = QPushButton()
        self.btn_scale.setIcon(QIcon(resource_path("resources/icon/pagezoom.png"
        )))
        self.btn_scale.setIconSize(QSize(23, 23))
        self.btn_scale.setToolTip("Размер содержимого")
        self.btn_scale.setStyleSheet(style_dark_gray)
        self.btn_scale.clicked.connect(self.open_scale_module)

        # --- Кнопки Фото ---
        self.btn_select_image = QPushButton()
        self.btn_select_image.setIcon(QIcon(resource_path("resources/icon/imageselect.png"
        )))
        self.btn_select_image.setIconSize(QSize(23, 23))
        self.btn_select_image.setToolTip("Выбрать изображение")
        self.btn_select_image.setStyleSheet(style_light_gray)
        self.btn_select_image.setCheckable(True)
        self.btn_select_image.clicked.connect(self.toggle_image_select_mode)

        self.btn_imageclone = QPushButton()
        self.btn_imageclone.setIcon(QIcon(resource_path("resources/icon/imageclone.png"
        )))
        self.btn_imageclone.setIconSize(QSize(23, 23))
        self.btn_imageclone.setToolTip("Клонировать")
        self.btn_imageclone.setStyleSheet(style_light_gray)
        self.btn_imageclone.clicked.connect(self.open_imageclone_module)

        self.btn_photocorrection = QPushButton()
        self.btn_photocorrection.setIcon(QIcon(resource_path("resources/icon/photocorrection.png"
        )))
        self.btn_photocorrection.setIconSize(QSize(23, 23))
        self.btn_photocorrection.setToolTip("Коррекция")
        self.btn_photocorrection.setStyleSheet(style_light_gray)
        self.btn_photocorrection.clicked.connect(self.open_photocorrection_module)

        self.btn_openeditphoto = QPushButton()
        self.btn_openeditphoto.setIcon(QIcon(resource_path("resources/icon/openeditphoto.png"
        )))
        self.btn_openeditphoto.setIconSize(QSize(23, 23))
        self.btn_openeditphoto.setToolTip("Открыть в редакторе")
        self.btn_openeditphoto.setStyleSheet(style_light_gray)
        self.btn_openeditphoto.clicked.connect(self.open_edit_photo_module)

        # --- Кнопки ЗАЩИТА ---
        self.btn_logo = QPushButton()
        self.btn_logo.setIcon(QIcon(resource_path("resources/icon/logopage.png"
        )))
        self.btn_logo.setIconSize(QSize(23, 23))
        self.btn_logo.setToolTip("Поместить лого")
        self.btn_logo.setStyleSheet(style_light_gray)
        self.btn_logo.clicked.connect(self.open_logo_module)

        # Формируем 2-й ряд (Макет | Размер | Фото)
        layout_group = create_group_layout("Макет", [
            self.btn_booklet, self.btn_booklet2, self.btn_spusk, self.btn_multiply, 
            self.btn_number, self.btn_mask, self.btn_bg
        ])
        top_row2.addLayout(layout_group)

        size_group = create_group_layout("Размер", [self.btn_resize, self.btn_scale])
        top_row2.addLayout(size_group)

        photo_group = create_group_layout("Фото", [
            self.btn_select_image, self.btn_imageclone, 
            self.btn_photocorrection, self.btn_openeditphoto
        ])
        top_row2.addLayout(photo_group)
        
        # --- Группа ЗАЩИТА ---
        protection_group = create_group_layout("Защита", [
            self.btn_logo
        ])
        top_row2.addLayout(protection_group)

        top_row2.addStretch()

        # Собираем панель с отступом вместо разделителя
        top_bar_container.addLayout(top_row1)
        top_bar_container.addSpacing(10)
        top_bar_container.addLayout(top_row2)
        
        layout.addLayout(top_bar_container)

        # 2. Область предпросмотра
        middle_container = QWidget()
        middle_layout = QHBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        # Кнопка сайдбара (левая)
        self.btn_toggle_thumb = QPushButton("▶")
        self.btn_toggle_thumb.setFixedWidth(25)
        self.btn_toggle_thumb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.btn_toggle_thumb.clicked.connect(self.toggle_thumbnail_panel)
        self.btn_toggle_thumb.setStyleSheet("""
            QPushButton { font-weight: bold; background-color: #444; color: white; border: none; border-right: 1px solid #222; }
            QPushButton:hover { background-color: #555; }
        """)
        middle_layout.addWidget(self.btn_toggle_thumb)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель эскизов
        self.thumb_panel = QWidget()
        self.thumb_panel_layout = QVBoxLayout(self.thumb_panel)
        self.thumb_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb_panel_layout.setSpacing(0)
        
        self.btn_toggle_cols = QPushButton("Переключить в 1 колонку")
        self.btn_toggle_cols.setStyleSheet(btn_style)
        self.btn_toggle_cols.clicked.connect(self.toggle_thumb_columns)
        self.thumb_panel_layout.addWidget(self.btn_toggle_cols)
        
        self.thumb_scroll = QScrollArea()
        self.thumb_scroll.setStyleSheet("background-color: #333;")
        self.thumb_scroll.setWidgetResizable(True)
        
        self.thumb_container = QWidget()
        self.thumb_layout = QGridLayout(self.thumb_container)
        self.thumb_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.thumb_scroll.setWidget(self.thumb_container)
        self.thumb_panel_layout.addWidget(self.thumb_scroll)
        
        self.thumb_columns = 2
        self.thumb_panel.hide()
        self.splitter.addWidget(self.thumb_panel)
        
        # Область предпросмотра
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #555;")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.update_page_info)
        
        # Устанавливаем фильтр событий для перехвата колесика мыши в режиме одного листа
        self.scroll_area.viewport().installEventFilter(self)
        
        self.preview_container = QWidget()
        self.preview_layout = QGridLayout(self.preview_container)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll_area.setWidget(self.preview_container)
        
        self.splitter.addWidget(self.scroll_area)
        
        # Правая панель файлов
        self.files_panel = FilesPanel(self)
        self.files_panel.hide() # Изначально скрыта
        self.splitter.addWidget(self.files_panel)
        
        self.splitter.setSizes([200, 800, 150])
        middle_layout.addWidget(self.splitter)

        # Кнопка сайдбара (правая)
        self.btn_toggle_files = QPushButton("◀")
        self.btn_toggle_files.setFixedWidth(25)
        self.btn_toggle_files.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.btn_toggle_files.clicked.connect(self.toggle_files_panel)
        self.btn_toggle_files.setStyleSheet("""
            QPushButton { font-weight: bold; background-color: #444; color: white; border: none; border-left: 1px solid #222; }
            QPushButton:hover { background-color: #555; }
        """)
        middle_layout.addWidget(self.btn_toggle_files)
        
        layout.addWidget(middle_container)

        # 3. Нижняя панель
        bottom_bar = QHBoxLayout()
        
        # Переключатели режима прокрутки
        self.btn_scroll_cont = QPushButton("■ ■")
        self.btn_scroll_cont.setFixedSize(30, 25)
        self.btn_scroll_cont.setToolTip("Плавная прокрутка")
        self.btn_scroll_cont.clicked.connect(lambda: self.set_scroll_mode('continuous'))
        
        self.btn_scroll_page = QPushButton("█")
        self.btn_scroll_page.setFixedSize(30, 25)
        self.btn_scroll_page.setToolTip("Постраничный просмотр (появляется сразу новый)")
        self.btn_scroll_page.clicked.connect(lambda: self.set_scroll_mode('page'))
        
        bottom_bar.addWidget(self.btn_scroll_cont)
        bottom_bar.addWidget(self.btn_scroll_page)
        
        bottom_bar.addSpacing(10) # Отступ между группами кнопок
        
        # Переключатели линеек
        self.btn_rulers_on = QPushButton("📏 Вкл")
        self.btn_rulers_on.setFixedSize(65, 25)
        self.btn_rulers_on.setToolTip("Включить линейки")
        self.btn_rulers_on.clicked.connect(lambda: self.set_rulers_mode(True))
        
        self.btn_rulers_off = QPushButton("📏 Выкл")
        self.btn_rulers_off.setFixedSize(65, 25)
        self.btn_rulers_off.setToolTip("Выключить линейки")
        self.btn_rulers_off.clicked.connect(lambda: self.set_rulers_mode(False))
        
        bottom_bar.addWidget(self.btn_rulers_on)
        bottom_bar.addWidget(self.btn_rulers_off)
        
        bottom_bar.addSpacing(10)
        
        bottom_bar.addSpacing(15)  # расстояние между масштабом и "Размер"

        # Здесь теперь находится информация (перенесена с верхней панели)
        self.info_label = QLabel("Размер: 0x0 мм | Листов: 0")
        bottom_bar.addWidget(self.info_label)

        # Вертикальный разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setFixedHeight(22)

        bottom_bar.addSpacing(10)
        bottom_bar.addWidget(separator)
        bottom_bar.addSpacing(10)

        # Номер страницы
        bottom_bar.addWidget(QLabel("Стр:"))
        self.page_input = QLineEdit("0")
        self.page_input.setFixedWidth(50)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999))
        self.page_input.returnPressed.connect(self.go_to_page)
        bottom_bar.addWidget(self.page_input)
        
        # ВСТАВИТЬ СОЗДАНИЕ КНОПКИ СЕРДЕЧКА ЗДЕСЬ (строка ~472)
        self.btn_heart = QPushButton("❤")
        self.btn_heart.setFixedSize(30, 25)
        self.btn_heart.setStyleSheet("background-color: #e0e0e0; color: red; font-weight: bold; border-radius: 4px; border: 1px solid #aaa;")
        self.btn_heart.setToolTip("Лицензионное соглашение")
        self.btn_heart.clicked.connect(self.show_license)
        bottom_bar.addWidget(self.btn_heart)

        # ==========================================================
        # МАСШТАБ ЛИСТА
        # ==========================================================

        self.page_zoom = PageZoom(self)

        bottom_bar.addWidget(
            self.page_zoom
)
        
        # ==========================================================
        # КНОПКИ РЕЖИМА ОТОБРАЖЕНИЯ
        # ==========================================================

        # По высоте
        self.btn_height = QPushButton("По высоте")
        self.btn_height.clicked.connect(
            lambda: self.fit_to_height(self.btn_height)
        )

        # 1 лист
        self.btn_one = QPushButton("1 лист")
        self.btn_one.clicked.connect(
            lambda: self.set_page_count(1, self.btn_one)
        )

        # 2 листа
        self.btn_two = QPushButton("2 листа")
        self.btn_two.clicked.connect(
            lambda: self.set_page_count(2, self.btn_two)
        )

        # 3 листа
        self.btn_three = QPushButton("3 листа")
        self.btn_three.clicked.connect(
            lambda: self.set_page_count(3, self.btn_three)
        )

        # 5 листов
        self.btn_five = QPushButton("5 листов")
        self.btn_five.clicked.connect(
            lambda: self.set_page_count(5, self.btn_five)
        )

        # 7 листов
        self.btn_seven = QPushButton("7 листов")
        self.btn_seven.clicked.connect(
            lambda: self.set_page_count(7, self.btn_seven)
        )

        # Все кнопки режима
        self.mode_buttons = [
            self.btn_height,
            self.btn_one,
            self.btn_two,
            self.btn_three,
            self.btn_five,
            self.btn_seven
        ]

        # Базовый стиль
        inactive_style = (
            "background-color: #e0e0e0;"
            "color: black;"
            "font-weight: bold;"
            "border-radius: 4px;"
            "padding: 4px 8px;"
        )

        for btn in self.mode_buttons:
            btn.setStyleSheet(inactive_style)
            bottom_bar.addWidget(btn)

        
        layout.addLayout(bottom_bar)
        
        # Устанавливаем дефолтный режим прокрутки
        self.scroll_mode = 'continuous'
        self.set_scroll_mode('continuous')
        
        # Устанавливаем дефолтный режим линеек
        self.set_rulers_mode(True)

        # --- Drag & Drop PDF файлов ---
        self.setAcceptDrops(True)

# ВСТАВИТЬ МЕТОД SHOW_LICENSE ЗДЕСЬ (строка ~526)
    def show_license(self):
        dialog = LicenseViewer(self)
        dialog.exec()
        
        
    def toggle_image_select_mode(self):
        """Включение/выключение режима выбора фото"""

        # Если PDF еще не открыт
        if self.doc is None:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            self.btn_select_image.setChecked(False)
            self.is_image_select_mode = False
            return

        self.is_image_select_mode = self.btn_select_image.isChecked()

        if self.is_image_select_mode:
            # Сделаем активное состояние темно-серым, чтобы выделялось при нажатии
            self.btn_select_image.setStyleSheet(
                "background-color: #888888; color: white; font-weight: bold; border: 2px solid black; border-radius: 6px; padding: 3px 8px;"
            )
        else:
            # Возвращаем стандартный цвет группы 5 (светло-серый)
            self.btn_select_image.setStyleSheet(
                "background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 6px; padding: 5px 10px;"
            )
            self.image_selection_manager.clear_selection()
            self.render_pages()

    def get_ghostscript_path_local(self):
        """
        Ищет исполняемый файл Ghostscript.
        Учитываем новую структуру с папкой resources/ghostscript...
        """
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        candidates = []
        
        # Новая структура с папкой resources
        gs_root = os.path.join(base_dir, "resources", "ghostscript")
        
        # 1. Если внутри resources/ghostscript/ есть папка с версией (например, gs10.07.1)
        if os.path.exists(gs_root) and os.path.isdir(gs_root):
            for item in os.listdir(gs_root):
                sub_dir = os.path.join(gs_root, item)
                if os.path.isdir(sub_dir):
                    candidates.append(os.path.join(sub_dir, "bin", "gswin64c.exe"))
                    candidates.append(os.path.join(sub_dir, "bin", "gswin32c.exe"))

        # 2. Если bin лежит прямо внутри resources/ghostscript/
        candidates.append(os.path.join(gs_root, "bin", "gswin64c.exe"))
        candidates.append(os.path.join(gs_root, "bin", "gswin32c.exe"))

        for path in candidates:
            if os.path.exists(path):
                return path
        
        return None

    def open_export_module(self):
        """Открытие модуля экспорта"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        dialog = ExportDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_export(settings)

    def apply_export(self, settings):
        """Логика экспорта страниц в JPG или TIFF"""
        try:
            out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения экспортированных файлов")
            if not out_dir:
                return

            fmt = settings['format'].lower()
            color_space = settings['color']
            mode = settings['range']

            if color_space == "CMYK":
                cs = fitz.csCMYK
            elif color_space == "GRAY":
                cs = fitz.csGRAY
            else:
                cs = fitz.csRGB

            pages_to_process = []
            if mode == "Все страницы":
                pages_to_process = range(len(self.doc))
            elif mode == "Текущая страница":
                current_idx = self.active_page_index if self.active_page_index != -1 else 0
                pages_to_process = [current_idx]
            elif mode == "Четные страницы":
                pages_to_process = [i for i in range(len(self.doc)) if (i + 1) % 2 == 0]
            elif mode == "Нечетные страницы":
                pages_to_process = [i for i in range(len(self.doc)) if (i + 1) % 2 != 0]

            for i in pages_to_process:
                page = self.doc.load_page(i)
                pix = page.get_pixmap(colorspace=cs, dpi=300)
                out_path = os.path.join(out_dir, f"page_{i+1}.{fmt}")
                pix.save(out_path)

            QMessageBox.information(self, "Успех", f"Успешно экспортировано {len(pages_to_process)} страниц в {out_dir}")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить экспорт:\n{e}")

    def open_background_module(self):
        """Открытие модуля настройки фона"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        dialog = BackgroundDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self.apply_background(settings)

    def apply_background(self, settings):
        """Добавление фона позади элементов страницы"""
        try:
            mode = settings['range']
            bg_type = settings['bg_type']

            new_doc = fitz.open()

            # Если фон из PDF, откроем его один раз
            bg_doc = None
            if bg_type == 'pdf':
                bg_doc = fitz.open(settings['file_path'])

            for i in range(len(self.doc)):
                apply = False
                if mode == "Все страницы":
                    apply = True
                elif mode == "Текущая страница" and i == self.active_page_index:
                    apply = True
                elif mode == "Четные страницы" and (i + 1) % 2 == 0:
                    apply = True
                elif mode == "Нечетные страницы" and (i + 1) % 2 != 0:
                    apply = True

                old_page = self.doc.load_page(i)
                page_rect = old_page.rect

                # Создаем новую страницу такого же размера
                new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)

                if apply:
                    # Сначала рисуем фон (он будет позади всех элементов)
                    if bg_type == 'color':
                        # Заливаем лист цветом без обводки
                        new_page.draw_rect(new_page.rect, color=None, fill=settings['color_value'])
                    elif bg_type == 'jpg':
                        # Вставляем JPG с растягиванием (keep_proportion=False)
                        new_page.insert_image(new_page.rect, filename=settings['file_path'], keep_proportion=False)
                    elif bg_type == 'pdf' and bg_doc and len(bg_doc) > 0:
                        # Вставляем PDF с растягиванием
                        new_page.show_pdf_page(new_page.rect, bg_doc, 0, keep_proportion=False)

                # Затем накладываем содержимое оригинальной страницы
                new_page.show_pdf_page(new_page.rect, self.doc, i)

            if bg_doc:
                bg_doc.close()

            if self.doc:
                self.doc.close()

            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            QMessageBox.information(self, "Успех", "Фон успешно применен.")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить фон:\n{e}")

    def open_convertcolor_module(self):
        """Открытие модуля конвертации цветов"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        dialog = ConvertColorDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_convertcolor(settings)

    def apply_convertcolor(self, settings):
        """Применение конвертации цветов через Ghostscript (исправленная версия)"""
        try:
            mode = settings['range']
            target = settings['target']
            profile = settings.get('profile', '')

            # БЕРЕМ ПУТЬ К GHOSTSCRIPT СТРОГО ИЗ НАСТРОЕК ДИАЛОГА (КРОССПЛАТФОРМЕННО)
            gs_exec = settings.get('gs_path')

            # Запасной вариант на случай, если настройки пустые
            if not gs_exec:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
                if platform.system() == "Windows":
                    gs_exec = os.path.join(bin_dir, "gswin64c.exe")
                else:
                    local_gs = os.path.join(bin_dir, "gs")
                    gs_exec = local_gs if os.path.exists(local_gs) else (shutil.which("gs") or "gs")

            # Проверяем существование файла (для абсолютных путей)
            if gs_exec and os.path.isabs(gs_exec) and not os.path.exists(gs_exec):
                if platform.system() != "Windows":
                    gs_exec = "gs"

            if not gs_exec:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не найден Ghostscript!"
                )
                return

            temp_in = os.path.join(tempfile.gettempdir(), "librepage_color_in.pdf")
            temp_out = os.path.join(tempfile.gettempdir(), "librepage_color_out.pdf")

            self.doc.save(temp_in)

            # Ghostscript 10.x требует корректные параметры моделей.
            if target == "cmyk":
                color_strategy = "CMYK"
                process_model = "DeviceCMYK"
            elif target == "rgb":
                color_strategy = "RGB"
                process_model = "DeviceRGB"
            elif target in ("grey"):
                color_strategy = "Gray"
                process_model = "DeviceGray"
            else:
                color_strategy = "RGB"
                process_model = "DeviceRGB"

            cmd = [
                gs_exec,
                "-dNOPAUSE",
                "-dBATCH",
                "-dSAFER",
                "-sDEVICE=pdfwrite",
                f"-sColorConversionStrategy={color_strategy}",
                f"-sProcessColorModel={process_model}",
                "-dAutoRotatePages=/None",
                f"-sOutputFile={temp_out}"
            ]

            # ICC профиль добавляем только если Ghostscript сможет его применить.
            if profile and os.path.exists(profile):
                cmd.append(f"-sDefaultRGBProfile={profile}" if target == "rgb" else
                           f"-sDefaultCMYKProfile={profile}" if target == "cmyk" else
                           f"-sDefaultGrayProfile={profile}")

            cmd.append(temp_in)

            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as err:
                # Если профиль вызвал ошибку — повторяем без ICC.
                cmd = [
                    gs_exec,
                    "-dNOPAUSE",
                    "-dBATCH",
                    "-dSAFER",
                    "-sDEVICE=pdfwrite",
                    f"-sColorConversionStrategy={color_strategy}",
                    f"-sProcessColorModel={process_model}",
                    "-dAutoRotatePages=/None",
                    f"-sOutputFile={temp_out}",
                    temp_in
                ]

                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            conv_doc = fitz.open(temp_out)
            new_doc = fitz.open()

            for i in range(len(self.doc)):
                apply = False

                if mode == "Все страницы":
                    apply = True
                elif mode == "Текущая страница" and i == self.active_page_index:
                    apply = True
                elif mode == "Четные страницы" and (i + 1) % 2 == 0:
                    apply = True
                elif mode == "Нечетные страницы" and (i + 1) % 2 != 0:
                    apply = True

                if apply:
                    new_doc.insert_pdf(conv_doc, from_page=i, to_page=i)
                else:
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)

            conv_doc.close()

            if self.doc:
                self.doc.close()

            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            if os.path.exists(temp_in):
                os.remove(temp_in)
            if os.path.exists(temp_out):
                os.remove(temp_out)

            QMessageBox.information(
                self,
                "Успех",
                "Цветовое пространство успешно изменено!"
            )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось применить конвертацию цветов:\n{e}"
            )

    def open_curves_module(self):
        """Открытие модуля перевода текста в кривые"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        dialog = CurvesDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_curves(settings)

    def apply_curves(self, settings):
        """Применение перевода текста в кривые через Ghostscript (постранично)"""
        try:
            mode = settings['range']
            custom_pages_str = settings.get('custom_pages', '')
            
            # БЕРЕМ ПУТЬ К GHOSTSCRIPT СТРОГО ИЗ НАСТРОЕК ДИАЛОГА (КРОССПЛАТФОРМЕННО)
            gs_exec = settings.get('gs_path')

            # Запасной вариант на случай, если настройки пустые
            if not gs_exec:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
                if platform.system() == "Windows":
                    gs_exec = os.path.join(bin_dir, "gswin64c.exe")
                else:
                    local_gs = os.path.join(bin_dir, "gs")
                    gs_exec = local_gs if os.path.exists(local_gs) else (shutil.which("gs") or "gs")

            # Проверяем существование файла (для абсолютных путей)
            if gs_exec and os.path.isabs(gs_exec) and not os.path.exists(gs_exec):
                if platform.system() != "Windows":
                    gs_exec = "gs"

            if not gs_exec:
                QMessageBox.critical(self, "Ошибка", "Не найден Ghostscript!")
                return

            total_pages = len(self.doc)
            pages_to_process = []

            if mode == "Все страницы":
                pages_to_process = list(range(total_pages))
            elif mode == "Текущая страница":
                current_idx = self.active_page_index if self.active_page_index != -1 else 0
                pages_to_process = [current_idx]
            elif mode == "Четные страницы":
                pages_to_process = [i for i in range(total_pages) if (i + 1) % 2 == 0]
            elif mode == "Нечетные страницы":
                pages_to_process = [i for i in range(total_pages) if (i + 1) % 2 != 0]
            elif mode == "Указанные страницы":
                try:
                    for part in custom_pages_str.replace(" ", "").split(","):
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            pages_to_process.extend(range(start - 1, end))
                        else:
                            pages_to_process.append(int(part) - 1)
                    pages_to_process = [p for p in set(pages_to_process) if 0 <= p < total_pages]
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", "Некорректный формат указанных страниц.")
                    return

            if not pages_to_process:
                QMessageBox.warning(self, "Внимание", "Нет страниц для обработки.")
                return

            new_doc = fitz.open()
            main_temp_dir = tempfile.mkdtemp(prefix="librepage_curves_")
            system_fonts = None

            # Обрабатываем листы по одному
            for i in range(total_pages):
                if i not in pages_to_process:
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    continue
                
                # --- ВИЗУАЛИЗАЦИЯ: "Листы будут бегать" ---
                self.handle_page_click(i)
                row = i // self.pages_in_row
                col = i % self.pages_in_row
                item = self.preview_layout.itemAtPosition(row, col)
                if item and item.widget():
                    self.scroll_area.ensureWidgetVisible(item.widget(), 50, 50)
                QApplication.processEvents()
                # ------------------------------------------
                
                temp_page_in = os.path.join(main_temp_dir, f"page_{i}_in.pdf")
                temp_page_out = os.path.join(main_temp_dir, f"page_{i}_out.pdf")
                
                single_page_doc = fitz.open()
                single_page_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                single_page_doc.save(temp_page_in)
                single_page_doc.close()

                # ХОЛОСТОЙ ПРОГОН (Dry Run): Ищем отсутствующие шрифты
                cmd_dry = [
                    gs_exec, "-dNOPAUSE", "-dBATCH", "-dSAFER",
                    "-sDEVICE=nullpage",
                    temp_page_in
                ]
                
                result_dry = subprocess.run(cmd_dry, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logs = result_dry.stderr.decode('utf-8', errors='ignore') + "\n" + result_dry.stdout.decode('utf-8', errors='ignore')
                
                missing_fonts = []
                for line in logs.split('\n'):
                    if "Substituting font" in line:
                        try:
                            font_name = line.split("font")[1].split("for")[0].strip()
                            if font_name not in missing_fonts:
                                missing_fonts.append(font_name)
                        except:
                            pass
                
                skip_page = False
                fontmap_dir = None
                
                # ЕСЛИ ШРИФТА НЕТ В СИСТЕМЕ
                if missing_fonts:
                    if system_fonts is None:
                        system_fonts = {}
                        if platform.system() == "Windows":
                            font_dirs = [os.environ.get('WINDIR', 'C:\\Windows') + '\\Fonts']
                        else:
                            font_dirs = ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts')]
                            
                        for d in font_dirs:
                            if os.path.exists(d):
                                for root, dirs, files in os.walk(d):
                                    for f in files:
                                        if f.lower().endswith(('.ttf', '.otf', '.ttc')):
                                            name = os.path.splitext(f)[0]
                                            system_fonts[name] = os.path.join(root, f)
                    
                    fontmap_dir = os.path.join(main_temp_dir, f"fontmap_{i}")
                    os.makedirs(fontmap_dir, exist_ok=True)
                    fontmap_path = os.path.join(fontmap_dir, "Fontmap")
                    
                    for m_font in missing_fonts:
                        dialog = MissingFontDialog(m_font, system_fonts, self)
                        dialog.exec()
                        
                        if dialog.result_action == "skip":
                            skip_page = True
                            break
                        else:
                            with open(fontmap_path, "a", encoding="utf-8") as fm:
                                gs_path_font = dialog.selected_font_path.replace("\\", "/")
                                fm.write(f"/{m_font} ({gs_path_font}) ;\n")
                
                if skip_page:
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    continue

                # ФИНАЛЬНАЯ КОНВЕРТАЦИЯ СТРАНИЦЫ
                cmd_real = [
                    gs_exec, "-dNOPAUSE", "-dBATCH", "-dSAFER",
                    "-sDEVICE=pdfwrite",
                    "-dNoOutputFonts",
                    "-dAutoRotatePages=/None",
                    f"-sOutputFile={temp_page_out}"
                ]
                
                if fontmap_dir and os.path.exists(os.path.join(fontmap_dir, "Fontmap")):
                    cmd_real.append(f"-I{fontmap_dir}")
                    
                cmd_real.append(temp_page_in)
                
                try:
                    subprocess.run(cmd_real, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    conv_page_doc = fitz.open(temp_page_out)
                    new_doc.insert_pdf(conv_page_doc, from_page=0, to_page=0)
                    conv_page_doc.close()
                except Exception as e:
                    print(f"Ошибка при конвертации страницы {i+1}: {e}")
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)

            # --- Завершение ---
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            shutil.rmtree(main_temp_dir, ignore_errors=True)
            QMessageBox.information(self, "Успех", "Текст переведен в кривые!")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось перевести текст в кривые:\n{e}")

    def open_imageclone_module(self):
        """Открытие модуля клонирования фото"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        page_index = self.active_page_index if self.active_page_index != -1 else 0
        page = self.doc.load_page(page_index)
        
        # Увеличим для лучшего качества выделения в диалоге
        zoom = 2.0 
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        dialog = ImageCloneDialog(pixmap, self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings and settings.get('rect_ratio'):
                self.apply_imageclone(settings['rect_ratio'], page_index)
            else:
                QMessageBox.warning(self, "Внимание", "Вы не выделили область для клонирования.")

    # --- ДОБАВЛЕНО: МОДУЛЬ КОРРЕКЦИЯ ФОТО ---
    def open_photocorrection_module(self):
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        # Проверка, что фото выбрано
        if not self.image_selection_manager.selected_bbox:
            QMessageBox.warning(self, "Внимание", "Сначала выберите фото инструментом 'Выбрать'.")
            return

        dialog = PhotoCorrectionDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_photocorrection(settings)

    def apply_photocorrection(self, settings):
        try:
            page_index = self.image_selection_manager.selected_page_index
            bbox = self.image_selection_manager.selected_bbox
            page = self.doc.load_page(page_index)

            # Получаем растр выбранной области
            pix = page.get_pixmap(clip=bbox, dpi=300)
            
            # Конвертируем в PIL
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")

            # Применяем настройки
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(settings['brightness'])
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(settings['contrast'])
            
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(settings['saturation'])

            # Сохраняем во временный буфер для вставки
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            
            # Вставляем назад в PDF
            # Сначала закрываем область белым (аналогично клонированию)
            page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
            page.insert_image(bbox, stream=buf.getvalue())
            
            self.render_all()
            self.history_manager.save_state()
            QMessageBox.information(self, "Успех", "Коррекция применена.")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить коррекцию: {e}")
    # ----------------------------------------

    # --- ДОБАВЛЕНО: МОДУЛЬ ОТКРЫТЬ В РЕДАКТОРЕ ---
    def open_edit_photo_module(self):
        """Открытие выбранного фото во внешнем редакторе"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return

        if not self.image_selection_manager.selected_bbox:
            QMessageBox.warning(self, "Внимание", "Сначала выберите фото инструментом 'Выбрать'.")
            return

        # ИЗМЕНЕНИЕ: Вся логика извлечения, запуска и ожидания перенесена в main.py
        # Это гарантирует, что файл сохранится как .png (решает проблему с Photoshop)
        # И ставит код на паузу (решает проблему с GIMP/Krita, когда изменения не появлялись)

        page_index = self.image_selection_manager.selected_page_index
        bbox = self.image_selection_manager.selected_bbox
        page = self.doc.load_page(page_index)

        try:
            # Извлекаем растр
            pix = page.get_pixmap(clip=bbox, dpi=300)
            img_data = pix.tobytes("png")

            # Сохраняем во временный файл с явным расширением .png
            temp_file_path = os.path.join(tempfile.gettempdir(), "librepage_edit_photo.png")
            with open(temp_file_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось извлечь фото:\n{e}")
            return

        # Запрашиваем путь к редактору, если он еще не выбран
        if not self.external_editor_path or not os.path.exists(self.external_editor_path):
            editor_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите программу для редактирования (Photoshop, GIMP, Krita...)",
                "",
                "Исполняемые файлы (*.exe *.app *.sh *.bat);;Все файлы (*.*)"
            )
            if not editor_path:
                return
            self.external_editor_path = editor_path

        # Открываем редактор
        try:
            safe_file_path = os.path.normpath(temp_file_path)
            safe_editor_path = os.path.normpath(self.external_editor_path)

            if platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", safe_editor_path, safe_file_path])
            else:
                subprocess.Popen([safe_editor_path, safe_file_path])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить редактор:\n{e}")
            return

        # Важно! Приостанавливаем выполнение, чтобы дождаться пока пользователь сохранит файл
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Ожидание редактора")
        msg_box.setText("Изображение открыто во внешнем редакторе.\n\n1. Внесите изменения в открывшемся редакторе.\n2. Сохраните файл (Перезапишите текущий файл, не выбирайте 'Сохранить как').\n3. Вернитесь в эту программу и нажмите 'Применить изменения'.\n\nЕсли хотите выбрать другой редактор в будущем, просто перезапустите LibrePage.")
        btn_apply = msg_box.addButton("Применить изменения", QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = msg_box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        if msg_box.clickedButton() == btn_apply:
            try:
                # Обновляем страницу. Вставляем поверх белого прямоугольника
                page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                page.insert_image(bbox, filename=temp_file_path)

                self.render_all()
                self.history_manager.save_state()
                QMessageBox.information(self, "Успех", "Изображение успешно обновлено!")
            except Exception as e:
                traceback.print_exc()
                QMessageBox.critical(self, "Ошибка", f"Не удалось применить изменения:\n{e}")
    # ----------------------------------------

    def apply_imageclone(self, rect_ratio, page_index):
        """Логика клонирования: получение растра области, белая подложка на 0.5 мм больше, вставка растра"""
        try:
            rx, ry, rw, rh = rect_ratio
            page = self.doc.load_page(page_index)
            
            # Получаем координаты текущей страницы в PDF
            pw = page.rect.width
            ph = page.rect.height
            
            x0 = page.rect.x0 + rx * pw
            y0 = page.rect.y0 + ry * ph
            x1 = x0 + rw * pw
            y1 = y0 + rh * ph
            
            target_rect = fitz.Rect(x0, y0, x1, y1)
            
            # Получаем растр клонируемой области с хорошим разрешением (300 dpi)
            clip_pix = page.get_pixmap(clip=target_rect, dpi=300)
            
            # Рассчитываем 0.5 мм в пунктах для расширения белого прямоугольника
            mm_to_pts = 72 / 25.4
            offset = 0.5 * mm_to_pts
            
            white_rect = fitz.Rect(x0 - offset, y0 - offset, x1 + offset, y1 + offset)
            
            # Накладываем белый прямоугольник для скрытия старого фото и фона
            page.draw_rect(white_rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Вставляем склонированное изображение поверх белого прямоугольника на те же координаты
            page.insert_image(target_rect, pixmap=clip_pix)
            
            self.render_all()
            self.history_manager.save_state()
            
            QMessageBox.information(self, "Успех", "Фото успешно клонировано!")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось клонировать фото:\n{e}")

    def open_scale_module(self):
        """Открытие модуля изменения масштаба содержимого страниц"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        dialog = ScalePageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_scale(settings)

    def apply_scale(self, settings):
        """Масштабирование содержимого страниц: растяжение по осям независимо"""
        try:
            # Преобразуем проценты в коэффициенты
            gen = settings['general'] / 100.0
            h_sc = settings['horiz'] / 100.0
            v_sc = settings['vert'] / 100.0

            # Итоговые коэффициенты масштабирования для каждой оси
            scale_x = gen * h_sc
            scale_y = gen * v_sc

            mode = settings['mode']

            new_doc = fitz.open()

            for i in range(len(self.doc)):
                apply = False
                if mode == "Все страницы":
                    apply = True
                elif mode == "Текущая страница" and i == self.active_page_index:
                    apply = True
                elif mode == "Четные страницы" and (i + 1) % 2 == 0:
                    apply = True
                elif mode == "Нечетные страницы" and (i + 1) % 2 != 0:
                    apply = True

                old_page = self.doc.load_page(i)
                page_rect = old_page.rect

                new_page = new_doc.new_page(
                    width=page_rect.width,
                    height=page_rect.height
                )

                if apply:
                    # Рассчитываем размеры контента независимо для каждой оси
                    content_w = page_rect.width * scale_x
                    content_h = page_rect.height * scale_y

                    # Центрируем контент: 
                    x = (page_rect.width - content_w) / 2
                    y = (page_rect.height - content_h) / 2

                    target_rect = fitz.Rect(
                        x,
                        y,
                        x + content_w,
                        y + content_h
                    )

                    # show_pdf_page с параметром keep_proportion=False позволяет
                    # растянуть контент строго в заданный прямоугольник target_rect
                    new_page.show_pdf_page(
                        target_rect,
                        self.doc,
                        i,
                        keep_proportion=False 
                    )
                else:
                    # Обычное копирование без изменений
                    new_page.show_pdf_page(
                        page_rect,
                        self.doc,
                        i
                    )

            if self.doc:
                self.doc.close()

            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            QMessageBox.information(
                self,
                "Успех",
                "Масштаб содержимого изменён (растяжение по осям)."
            )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось масштабировать содержимое:\n{e}"
            )

    def open_logo_module(self):
        """Открытие модуля размещения логотипа"""

        if not self.doc:
            QMessageBox.warning(
                self,
                "Внимание",
                "Сначала откройте PDF файл."
            )
            return

        dialog = LogoPageDialog(self)

        if dialog.exec():
            settings = dialog.get_settings()

            if settings:
                self.apply_logo(settings)

    def apply_logo(self, settings):
        """
        Накладывает логотип на страницы PDF.

        Логотип добавляется непосредственно в PDF,
        без растрирования всей страницы.
        """

        try:
            logo_path = settings["logo_path"]
            position = settings["position"]
            margin_x = settings["margin_x"]
            margin_y = settings["margin_y"]
            logo_size_mm = settings["logo_size"]
            rotation = settings["rotation"]
            opacity = settings["opacity"]

            tile_horizontal = settings["tile_horizontal"]
            tile_vertical = settings["tile_vertical"]

            mode = settings["range"]

            if not os.path.exists(logo_path):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Файл логотипа не найден."
                )
                return

            # ------------------------------------------------------
            # Определяем страницы
            # ------------------------------------------------------

            total_pages = len(self.doc)

            pages_to_process = []

            if mode == "Все страницы":
                pages_to_process = list(range(total_pages))

            elif mode == "Текущая страница":
                current_idx = (
                    self.active_page_index
                    if self.active_page_index != -1
                    else 0
                )
                pages_to_process = [current_idx]

            elif mode == "Четные страницы":
                pages_to_process = [
                    i for i in range(total_pages)
                    if (i + 1) % 2 == 0
                ]

            elif mode == "Нечетные страницы":
                pages_to_process = [
                    i for i in range(total_pages)
                    if (i + 1) % 2 != 0
                ]

            if not pages_to_process:
                QMessageBox.warning(
                    self,
                    "Внимание",
                    "Нет страниц для обработки."
                )
                return

            # ------------------------------------------------------
            # Подготовка изображения
            # ------------------------------------------------------

            with Image.open(logo_path) as source_img:

                # Переводим в RGBA для прозрачности
                source_img = source_img.convert("RGBA")

                original_w, original_h = source_img.size

                if original_w <= 0 or original_h <= 0:
                    raise ValueError(
                        "Некорректный размер изображения."
                    )

                # --------------------------------------------------
                # Размер логотипа.
                #
                # Пользователь задаёт ширину в мм.
                # Высота рассчитывается автоматически.
                # --------------------------------------------------

                mm_to_px = 96 / 25.4

                target_w_px = max(
                    1,
                    int(logo_size_mm * mm_to_px)
                )

                ratio = original_h / original_w

                target_h_px = max(
                    1,
                    int(target_w_px * ratio)
                )

                logo_img = source_img.resize(
                    (target_w_px, target_h_px),
                    Image.Resampling.LANCZOS
                )

                # --------------------------------------------------
                # Прозрачность
                # --------------------------------------------------

                if opacity < 100:

                    alpha = logo_img.getchannel("A")

                    alpha = alpha.point(
                        lambda value:
                        int(value * opacity / 100)
                    )

                    logo_img.putalpha(alpha)

                # --------------------------------------------------
                # Поворот
                # --------------------------------------------------

                if abs(rotation) > 0.01:

                    logo_img = logo_img.rotate(
                        -rotation,
                        expand=True,
                        resample=Image.Resampling.BICUBIC
                    )

                # --------------------------------------------------
                # PNG в памяти
                # --------------------------------------------------

                logo_buffer = io.BytesIO()

                logo_img.save(
                    logo_buffer,
                    format="PNG"
                )

                logo_bytes = logo_buffer.getvalue()

                # Размер логотипа в PDF points
                # 1 мм = 72 / 25.4 points
                mm_to_pts = 72 / 25.4

                logo_w_pts = (
                    logo_size_mm * mm_to_pts
                )

                # Сохраняем пропорции
                logo_h_pts = (
                    logo_w_pts
                    * logo_img.height
                    / logo_img.width
                )

            # ------------------------------------------------------
            # НОВЫЙ PDF
            # ------------------------------------------------------

            new_doc = fitz.open()

            for page_index in range(total_pages):

                old_page = self.doc.load_page(page_index)

                page_rect = old_page.rect

                # Создаём страницу того же размера
                new_page = new_doc.new_page(
                    width=page_rect.width,
                    height=page_rect.height
                )

                # Сначала копируем оригинальную страницу
                new_page.show_pdf_page(
                    new_page.rect,
                    self.doc,
                    page_index
                )

                # Если эту страницу обрабатывать не надо —
                # оставляем её без логотипа.
                if page_index not in pages_to_process:
                    continue

                # --------------------------------------------------
                # ПОЛОЖЕНИЕ
                # --------------------------------------------------

                if position == "top_left":

                    x = margin_x * mm_to_pts
                    y = margin_y * mm_to_pts

                    rect = fitz.Rect(
                        x,
                        y,
                        x + logo_w_pts,
                        y + logo_h_pts
                    )

                    new_page.insert_image(
                        rect,
                        stream=logo_bytes,
                        keep_proportion=False,
                        overlay=True
                    )

                elif position == "top_right":

                    x = (
                        page_rect.width
                        - margin_x * mm_to_pts
                        - logo_w_pts
                    )

                    y = margin_y * mm_to_pts

                    rect = fitz.Rect(
                        x,
                        y,
                        x + logo_w_pts,
                        y + logo_h_pts
                    )

                    new_page.insert_image(
                        rect,
                        stream=logo_bytes,
                        keep_proportion=False,
                        overlay=True
                    )

                elif position == "bottom_left":

                    x = margin_x * mm_to_pts

                    y = (
                        page_rect.height
                        - margin_y * mm_to_pts
                        - logo_h_pts
                    )

                    rect = fitz.Rect(
                        x,
                        y,
                        x + logo_w_pts,
                        y + logo_h_pts
                    )

                    new_page.insert_image(
                        rect,
                        stream=logo_bytes,
                        keep_proportion=False,
                        overlay=True
                    )

                elif position == "bottom_right":

                    x = (
                        page_rect.width
                        - margin_x * mm_to_pts
                        - logo_w_pts
                    )

                    y = (
                        page_rect.height
                        - margin_y * mm_to_pts
                        - logo_h_pts
                    )

                    rect = fitz.Rect(
                        x,
                        y,
                        x + logo_w_pts,
                        y + logo_h_pts
                    )

                    new_page.insert_image(
                        rect,
                        stream=logo_bytes,
                        keep_proportion=False,
                        overlay=True
                    )

                elif position == "center":

                    x = (
                        page_rect.width
                        - logo_w_pts
                    ) / 2

                    y = (
                        page_rect.height
                        - logo_h_pts
                    ) / 2

                    rect = fitz.Rect(
                        x,
                        y,
                        x + logo_w_pts,
                        y + logo_h_pts
                    )

                    new_page.insert_image(
                        rect,
                        stream=logo_bytes,
                        keep_proportion=False,
                        overlay=True
                    )

                elif position == "tile":

                    # ------------------------------------------------
                    # ЗАМОЩЕНИЕ
                    #
                    # Логотипы располагаются сеткой.
                    # Сетка центрируется относительно страницы.
                    #
                    # Если логотипы выходят за границу страницы,
                    # PDF автоматически обрежет их по краю листа.
                    # ------------------------------------------------

                    total_w = (
                        tile_horizontal * logo_w_pts
                    )

                    total_h = (
                        tile_vertical * logo_h_pts
                    )

                    start_x = (
                        page_rect.width - total_w
                    ) / 2

                    start_y = (
                        page_rect.height - total_h
                    ) / 2

                    for row in range(tile_vertical):

                        y = (
                            start_y
                            + row * logo_h_pts
                        )

                        for col in range(tile_horizontal):

                            x = (
                                start_x
                                + col * logo_w_pts
                            )

                            rect = fitz.Rect(
                                x,
                                y,
                                x + logo_w_pts,
                                y + logo_h_pts
                            )

                            new_page.insert_image(
                                rect,
                                stream=logo_bytes,
                                keep_proportion=False,
                                overlay=True
                            )

            # ------------------------------------------------------
            # Заменяем текущий документ
            # ------------------------------------------------------

            old_doc = self.doc

            self.doc = new_doc

            self.open_docs[
                self.current_file_path
            ] = self.doc

            try:
                old_doc.close()
            except Exception:
                pass

            # ------------------------------------------------------
            # Обновляем интерфейс
            # ------------------------------------------------------

            self.render_all()

            # Сохраняем состояние для Undo
            self.history_manager.save_state()

            QMessageBox.information(
                self,
                "Успех",
                "Логотип успешно помещён на страницы."
            )

        except Exception as e:

            import traceback
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось поместить логотип:\n\n{e}"
            )

    def open_spusk_module(self):
        """Открытие модуля Спуска полос"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return

        dialog = SpuskDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings is not None:
                self.apply_spusk(settings)

    def apply_spusk(self, settings):
        """Логика обработки формулы (shuffle) и N-up размещения"""
        try:
            mm_to_pts = 72 / 25.4
            target_w_pts = settings['target_w'] * mm_to_pts
            target_h_pts = settings['target_h'] * mm_to_pts
            cols = settings['cols']
            rows = settings['rows']
            group_size = settings['group_size']
            formula = settings['formula']

            if cols <= 0 or rows <= 0 or group_size <= 0:
                QMessageBox.warning(self, "Ошибка", "Параметры спуска должны быть больше нуля.")
                return

            # Этап 1: Парсинг формулы перетасовки
            formula_parts = formula.split()
            placement_list = []

            for i in range(0, len(self.doc), group_size):
                for token in formula_parts:
                    rot = 0
                    is_blank = False
                    idx_offset = 0

                    if token.upper() == 'X':
                        is_blank = True
                    else:
                        if token.endswith('*'):
                            rot = 180
                            token_num = token[:-1]
                        elif token.endswith('/'):
                            rot = 90
                            token_num = token[:-1]
                        elif token.endswith('\\'):
                            rot = 270  # поворот против часовой на 90
                            token_num = token[:-1]
                        else:
                            token_num = token

                        try:
                            idx_offset = int(token_num) - 1
                        except ValueError:
                            is_blank = True

                    src_idx = i + idx_offset
                    placement_list.append({
                        'is_blank': is_blank,
                        'index': src_idx,
                        'rot': rot
                    })

            # Этап 2: Размещение N-up на новом листе
            new_doc = fitz.open()
            pages_per_sheet = cols * rows
            cell_w = target_w_pts / cols
            cell_h = target_h_pts / rows

            for page_idx in range(0, len(placement_list), pages_per_sheet):
                sheet_items = placement_list[page_idx : page_idx + pages_per_sheet]
                new_page = new_doc.new_page(width=target_w_pts, height=target_h_pts)

                for j, item in enumerate(sheet_items):
                    if item['is_blank']:
                        continue

                    src_idx = item['index']
                    if src_idx < len(self.doc):
                        c = j % cols
                        r = j // cols
                        x0 = c * cell_w
                        y0 = r * cell_h
                        rect = fitz.Rect(x0, y0, x0 + cell_w, y0 + cell_h)
                        
                        # Метод show_pdf_page поддерживает поворот, 
                        # пропорции (keep_proportion=True) применяются автоматически
                        new_page.show_pdf_page(rect, self.doc, src_idx, rotate=item['rot'])

            # Заменяем старый документ на новый
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.active_page_index = 0
            self.render_all()
            self.history_manager.save_state()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить спуск полос:\n{e}")
            
    def update_crop_preview(
        self,
        top,
        bottom,
        left,
        right,
        mode
    ):
        """
        Обновляет линии предварительного кадрирования.
        """

        # Если пришёл сигнал очистки
        if top < 0:
            self.clear_crop_preview()
            return

        if not self.page_widgets:
            return

        # ------------------------------------------
        # Какую страницу показываем
        # ------------------------------------------

        page_index = self.active_page_index

        if page_index < 0:
            page_index = 0

        # ------------------------------------------
        # Получаем активный PageWidget
        # ------------------------------------------

        page_widget = self.page_widgets[page_index]

        if not hasattr(page_widget, "crop_overlay"):
            return

        # ------------------------------------------
        # Пока показываем линии только
        # на активной странице
        # ------------------------------------------

        # Все остальные overlay скрываем
        for widget in self.page_widgets:

            if hasattr(widget, "crop_overlay"):

                if widget is page_widget:

                    widget.crop_overlay.set_crop_values(
                        top,
                        bottom,
                        left,
                        right
                    )

                    widget.crop_overlay.setGeometry(
                        widget.image_label.rect()
                    )

                    widget.crop_overlay.raise_()

                else:

                    widget.crop_overlay.hide()
                    
    def clear_crop_preview(self):
        """
        Убирает все линии предварительного кадрирования.
        """

        for widget in self.page_widgets:

            if hasattr(widget, "crop_overlay"):

                widget.crop_overlay.clear()

    def open_crop_module(self):
        """Открытие модуля кадрирования"""

        if not self.doc:
            QMessageBox.warning(
                self,
                "Внимание",
                "Сначала откройте PDF файл."
            )
            return

        # ------------------------------------------
        # Находим активную страницу
        # ------------------------------------------

        page_index = self.active_page_index

        if page_index < 0:
            page_index = 0

        if page_index >= len(self.page_widgets):
            return

        page_widget = self.page_widgets[page_index]

        # ------------------------------------------
        # Открываем окно кадрирования
        # ------------------------------------------

        dialog = CropPageDialog(self)

        # ------------------------------------------
        # При каждом изменении значения
        # сразу показываем линии
        # ------------------------------------------

        dialog.preview_changed.connect(
            lambda top, bottom, left, right, mode:
                self.update_crop_preview(
                    top,
                    bottom,
                    left,
                    right,
                    mode
                )
        )

        # ------------------------------------------
        # Открываем окно
        # ------------------------------------------

        result = dialog.exec()

        # ------------------------------------------
        # На всякий случай убираем линии
        # после закрытия окна
        # ------------------------------------------

        self.clear_crop_preview()

        # ------------------------------------------
        # Если нажали ПРИМЕНИТЬ
        # ------------------------------------------

        if result:

            settings = dialog.get_settings()

            self.apply_crop(settings)


    def open_pdftransfer_module(self):
        """Открывает окно «Обмен страницами» для копирования страниц из внешнего PDF."""

        if not self.doc:
            QMessageBox.warning(
                self,
                "Внимание",
                "Сначала откройте PDF файл."
            )
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF для обмена страницами",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_name:
            return

        try:
            dialog = PDFTransferDialog(self, file_name)

            dialog.show()
            dialog.raise_()
            dialog.activateWindow()

            # Храним открытые окна, чтобы Python их не удалил
            if not hasattr(self, "_pdftransfer_dialogs"):
                self._pdftransfer_dialogs = []

            self._pdftransfer_dialogs.append(dialog)

            def cleanup(_obj=None, dlg=dialog):
                try:
                    self._pdftransfer_dialogs.remove(dlg)
                except (ValueError, AttributeError):
                    pass

            dialog.destroyed.connect(cleanup)

        except Exception as e:
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть PDF в модуле «Обмен страницами»:\n\n{e}"
            )
            
    def open_fields_module(self):
        """Открытие модуля добавления полей (Поля+)"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        dialog = FieldsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_fields(settings)

    def apply_fields(self, settings):
        """Логика добавления полей вокруг страницы"""
        try:
            mm_to_pts = 72 / 25.4
            top_pts = settings['top'] * mm_to_pts
            bottom_pts = settings['bottom'] * mm_to_pts
            left_pts = settings['left'] * mm_to_pts
            right_pts = settings['right'] * mm_to_pts
            
            mode = settings['mode']
            new_doc = fitz.open()
            
            for i in range(len(self.doc)):
                should_apply = False
                if mode == "Все страницы": should_apply = True
                elif mode == "Четные страницы" and (i + 1) % 2 == 0: should_apply = True
                elif mode == "Нечетные страницы" and (i + 1) % 2 != 0: should_apply = True
                elif mode == "Текущая страница" and i == self.active_page_index: should_apply = True
                
                old_page = self.doc.load_page(i)
                old_rect = old_page.rect
                
                if should_apply:
                    # Размер нового листа = размер старого + нужные поля
                    new_w = old_rect.width + left_pts + right_pts
                    new_h = old_rect.height + top_pts + bottom_pts
                    
                    new_page = new_doc.new_page(width=new_w, height=new_h)
                    
                    # Прямоугольник для вставки старой страницы, смещенный на размер левого и верхнего полей
                    target_rect = fitz.Rect(left_pts, top_pts, left_pts + old_rect.width, top_pts + old_rect.height)
                    
                    # Вставляем содержимое старой страницы
                    new_page.show_pdf_page(target_rect, self.doc, i)
                else:
                    # Просто копируем страницу без изменений
                    new_page = new_doc.new_page(width=old_rect.width, height=old_rect.height)
                    new_page.show_pdf_page(new_page.rect, self.doc, i)
                    
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            
            self.render_all()
            self.history_manager.save_state()
            QMessageBox.information(self, "Успех", "Поля успешно добавлены.")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить поля:\n{e}")

    def apply_crop(self, settings):
        """Применение кадрирования к страницам"""
        try:
            mm_to_pts = 72 / 25.4
            top_pts = settings['top'] * mm_to_pts
            bottom_pts = settings['bottom'] * mm_to_pts
            left_pts = settings['left'] * mm_to_pts
            right_pts = settings['right'] * mm_to_pts
            
            mode = settings['mode']
            
            for i in range(len(self.doc)):
                should_apply = False
                if mode == "Все страницы": should_apply = True
                elif mode == "Четные страницы" and (i + 1) % 2 == 0: should_apply = True
                elif mode == "Нечетные страницы" and (i + 1) % 2 != 0: should_apply = True
                elif mode == "Текущая страница" and i == self.active_page_index: should_apply = True
                
                if should_apply:
                    page = self.doc.load_page(i)
                    rect = page.rect
                    # Уменьшаем размер страницы (сдвигаем координаты прямоугольника внутрь)
                    # Уменьшаем размер страницы
                    new_rect = fitz.Rect(
                        rect.x0 + left_pts,
                        rect.y0 + bottom_pts,
                        rect.x1 - right_pts,
                        rect.y1 - top_pts
)
                    
                    if new_rect.width > 0 and new_rect.height > 0:
                        page.set_cropbox(new_rect)
                        page.set_mediabox(new_rect)
                    else:
                        QMessageBox.warning(self, "Ошибка", f"Некорректные значения для обрезки на странице {i+1} (обрезано больше размера самого листа).")
                        return
            
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось обрезать страницы:\n{e}")

    def open_size_module(self):
        """Открытие модуля изменения размера"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        # Получаем размеры текущей страницы
        current_page = self.doc[self.active_page_index]
        cur_w_mm = current_page.rect.width / 2.83465
        cur_h_mm = current_page.rect.height / 2.83465

        # Вызываем диалог с правильными параметрами
        dialog = SizePageDialog(self, cur_w_mm, cur_h_mm)
        
        # Запускаем диалоговое окно и передаем настройки в apply_resize, если нажали APPLY
        if dialog.exec():
            settings = dialog.get_settings()
            
            # Проверяем, включено ли пропорциональное масштабирование (новый параметр из size.py)
            # Если галочки нет (старое поведение), можно временно переключить логику или передать дальше
            self.apply_resize(settings)

    def apply_resize(self, settings):
        """Изменяет размер страниц и масштабирует содержимое под новый формат."""
        try:
            mm_to_pts = 72 / 25.4
            new_w = settings['w_mm'] * mm_to_pts
            new_h = settings['h_mm'] * mm_to_pts

            new_doc = fitz.open()

            pages_to_process = (
                set(range(len(self.doc)))
                if settings['all']
                else {self.active_page_index}
            )

            # Сохраняем старый документ, пока новый полностью не создан
            old_doc = self.doc

            for i in range(len(old_doc)):
                if i in pages_to_process:
                    old_page = old_doc.load_page(i)

                    # Создаём страницу нового размера
                    new_page = new_doc.new_page(
                        width=new_w,
                        height=new_h
                    )

                    # ВАЖНО:
                    # scale=True  -> сохраняем пропорции
                    # scale=False -> растягиваем содержимое точно на новый лист
                    keep_proportion = settings.get('scale', True)

                    new_page.show_pdf_page(
                        new_page.rect,
                        old_doc,
                        i,
                        keep_proportion=keep_proportion
                    )

                else:
                    # Остальные страницы оставляем без изменений
                    new_doc.insert_pdf(
                        old_doc,
                        from_page=i,
                        to_page=i
                    )

            # Закрываем старый документ только после полного копирования
            old_doc.close()

            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            QMessageBox.information(
                self,
                "Успех",
                "Размер страниц изменен."
            )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось изменить размер:\n{e}"
            )

    def open_print_module(self):
        """Запуск модуля печати с сохранением текущих изменений"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        # 1. Сохраняем временный файл в системную папку temp
        temp_dir = tempfile.gettempdir()
        temp_print_path = os.path.join(temp_dir, "temp_print_job.pdf")
        
        try:
            self.doc.save(temp_print_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подготовить файл к печати: {e}")
            return
            
        # 2. Вызываем печать напрямую через импортированный модуль
        try:
            page_to_print = self.active_page_index if self.active_page_index != -1 else 0
            
            # Импортируем модуль печати
            import print as print_module
            
            # Вызываем функцию печати из модуля print.py
            # Передаем путь к временному PDF и номер страницы (1-based)
            print_module.start_print(temp_print_path, page_to_print + 1)

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Ошибка печати", 
                f"Не удалось вызывать модуль печати:\n{e}\n\n{traceback.format_exc()}"
            )

    def open_multiply_module(self):
        """Открытие модуля размножения страниц"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        dialog = MultiplyDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_multiply(settings)

    def apply_multiply(self, settings):
        """Логика размещения копий оригинальных страниц на новом холсте"""
        try:
            mm_to_pts = 72 / 25.4
            target_w_pts = settings['target_width_mm'] * mm_to_pts
            target_h_pts = settings['target_height_mm'] * mm_to_pts
            
            cols = settings['cols']
            rows = settings['rows']
            spacing_pts = settings['spacing_mm'] * mm_to_pts
            crop_marks = settings.get('crop_marks', False)
            crop_top = settings.get('crop_offset_top_mm', 0) * mm_to_pts
            crop_bottom = settings.get('crop_offset_bottom_mm', 0) * mm_to_pts
            crop_left = settings.get('crop_offset_left_mm', 0) * mm_to_pts
            crop_right = settings.get('crop_offset_right_mm', 0) * mm_to_pts
            
            if target_w_pts <= 0 or target_h_pts <= 0:
                QMessageBox.warning(self, "Ошибка", "Неверно заданы размеры листа.")
                return

            new_doc = fitz.open()

            for i in range(len(self.doc)):
                orig_page = self.doc.load_page(i)
                orig_w = orig_page.rect.width
                orig_h = orig_page.rect.height

                new_page = new_doc.new_page(width=target_w_pts, height=target_h_pts)

                grid_total_w = cols * orig_w + (cols - 1) * spacing_pts
                grid_total_h = rows * orig_h + (rows - 1) * spacing_pts

                start_x = (target_w_pts - grid_total_w) / 2
                start_y = (target_h_pts - grid_total_h) / 2

                # --- ЭТАП 1: Размещаем все страницы ---
                for r in range(rows):
                    for c in range(cols):
                        x0 = start_x + c * (orig_w + spacing_pts)
                        y0 = start_y + r * (orig_h + spacing_pts)
                        rect = fitz.Rect(x0, y0, x0 + orig_w, y0 + orig_h)
                        new_page.show_pdf_page(rect, self.doc, i)

                # --- ЭТАП 2: Рисуем все метки реза ---
                if crop_marks:
                    # Задаем параметры меток
                    mark_len = 3 * mm_to_pts
                    gap_pts = 1 * mm_to_pts  # Зазор 1 мм, чтобы не доходило до угла
                    color = (0, 0, 0)
                    line_w = 0.5

                    for r in range(rows):
                        for c in range(cols):
                            x0 = start_x + c * (orig_w + spacing_pts)
                            y0 = start_y + r * (orig_h + spacing_pts)

                            cut_x0 = x0 + crop_left
                            cut_y0 = y0 + crop_top
                            cut_x1 = x0 + orig_w - crop_right
                            cut_y1 = y0 + orig_h - crop_bottom

                            # Верхний левый угол
                            # Сдвигаем на gap_pts от угла (cut_x0, cut_y0)
                            new_page.draw_line(
                                fitz.Point(cut_x0 - mark_len - gap_pts, cut_y0),
                                fitz.Point(cut_x0 - gap_pts, cut_y0),
                                color=color, width=line_w
                            )
                            new_page.draw_line(
                                fitz.Point(cut_x0, cut_y0 - mark_len - gap_pts),
                                fitz.Point(cut_x0, cut_y0 - gap_pts),
                                color=color, width=line_w
                            )

                            # Верхний правый угол
                            new_page.draw_line(
                                fitz.Point(cut_x1 + gap_pts, cut_y0),
                                fitz.Point(cut_x1 + mark_len + gap_pts, cut_y0),
                                color=color, width=line_w
                            )
                            new_page.draw_line(
                                fitz.Point(cut_x1, cut_y0 - mark_len - gap_pts),
                                fitz.Point(cut_x1, cut_y0 - gap_pts),
                                color=color, width=line_w
                            )

                            # Нижний левый угол
                            new_page.draw_line(
                                fitz.Point(cut_x0 - mark_len - gap_pts, cut_y1),
                                fitz.Point(cut_x0 - gap_pts, cut_y1),
                                color=color, width=line_w
                            )
                            new_page.draw_line(
                                fitz.Point(cut_x0, cut_y1 + gap_pts),
                                fitz.Point(cut_x0, cut_y1 + mark_len + gap_pts),
                                color=color, width=line_w
                            )

                            # Нижний правый угол
                            new_page.draw_line(
                                fitz.Point(cut_x1 + gap_pts, cut_y1),
                                fitz.Point(cut_x1 + mark_len + gap_pts, cut_y1),
                                color=color, width=line_w
                            )
                            new_page.draw_line(
                                fitz.Point(cut_x1, cut_y1 + gap_pts),
                                fitz.Point(cut_x1, cut_y1 + mark_len + gap_pts),
                                color=color, width=line_w
                            )
                            
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.active_page_index = 0
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось размножить страницы:\n{e}")

    def open_mask_module(self):
        """Открытие модуля скрытия (наложения прямоугольника)"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
            
        page_index = self.active_page_index if self.active_page_index != -1 else 0
        page = self.doc.load_page(page_index)
        
        zoom = 1.0 # Базовый масштаб для окна настройки
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        dialog = MaskPageDialog(pixmap, self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings['rect_ratio']:
                self.apply_mask(settings)
            else:
                QMessageBox.warning(self, "Внимание", "Вы не выделили область для скрытия.")

    def apply_mask(self, settings):
        """Применяет белый прямоугольник к выбранным страницам"""
        ratio_x, ratio_y, ratio_w, ratio_h = settings['rect_ratio']
        mode = settings['mode']
        
        pages_to_process = []
        if mode == "Скрыть на текущей странице":
            current_index = self.active_page_index if self.active_page_index != -1 else 0
            pages_to_process = [current_index]
        else:
            pages_to_process = range(len(self.doc))
            
        for i in pages_to_process:
            page = self.doc.load_page(i)
            pw = page.rect.width
            ph = page.rect.height
            
            x0 = page.rect.x0 + ratio_x * pw
            y0 = page.rect.y0 + ratio_y * ph
            x1 = x0 + ratio_w * pw
            y1 = y0 + ratio_h * ph
            
            rect = fitz.Rect(x0, y0, x1, y1)
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            
        self.render_all()
        self.history_manager.save_state()

    def open_move_module(self):
        """Открытие модуля сдвига страниц"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        dialog = MovePageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_move(settings)

    def apply_move(self, settings):
        """Применение сдвига содержимого страниц без изменения размера страницы"""
        try:
            mm_to_pts = 72 / 25.4
            dx = settings['dx'] * mm_to_pts
            dy = settings['dy'] * mm_to_pts

            mode = settings['mode']

            # Сохраняем старый документ
            old_doc = self.doc

            # Создаём новый документ
            new_doc = fitz.open()

            for i in range(len(old_doc)):
                should_apply = False

                if mode == "Все страницы":
                    should_apply = True
                elif mode == "Четные страницы" and (i + 1) % 2 == 0:
                    should_apply = True
                elif mode == "Нечетные страницы" and (i + 1) % 2 != 0:
                    should_apply = True
                elif mode == "Текущая страница" and i == self.active_page_index:
                    should_apply = True

                old_page = old_doc.load_page(i)
                old_rect = old_page.rect

                # Создаём страницу ТОГО ЖЕ РАЗМЕРА,
                # который она имеет сейчас.
                new_page = new_doc.new_page(
                    width=old_rect.width,
                    height=old_rect.height
                )

                if should_apply:
                    # Сдвигаем содержимое внутри страницы.
                    target_rect = fitz.Rect(
                    dx,
                    -dy,
                    old_rect.width + dx,
                    old_rect.height - dy
                    )

                    new_page.show_pdf_page(
                        target_rect,
                        old_doc,
                        i
                    )
                else:
                    # Страница без сдвига остаётся как была.
                    new_page.show_pdf_page(
                        new_page.rect,
                        old_doc,
                        i
                    )

            # Заменяем документ
            old_doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось выполнить сдвиг:\n{e}"
            )

    def open_cutpage_module(self):
        """Открытие модуля разрезки"""
        if not self.current_file_path:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        dialog = CutPageDialog(self.current_file_path, self)
        dialog.exec()

    def open_merge_module(self):
        """Открытие модуля склейки"""
        merged_file_path = merge_pdfs_dialog(self)
        if merged_file_path:
            self.load_document(merged_file_path)

    def open_reverse_module(self):
        """Открытие модуля реверса страниц"""
        reverse_pages_action(self)

    def open_cheredov_module(self):
        """Открытие модуля чередования"""
        cheredov_pages_action(self)

    def open_rotate_module(self):
        """Открытие модуля поворота страниц"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        dialog = RotatePageDialog(self)
        dialog.exec()

    def open_number_module(self):
        """Открытие модуля нумерации страниц"""
        if not self.current_file_path:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        dialog = NumberPageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_numeration(settings)

    def apply_numeration(self, settings):
        """Применение нумерации к страницам PDF"""
        try:
            mm_to_pts = 72 / 25.4
            
            for i in range(len(self.doc)):
                page = self.doc.load_page(i)
                page_w = page.rect.width
                page_h = page.rect.height
                
                x_pts = settings['offset_x'] * mm_to_pts
                y_pts = settings['offset_y'] * mm_to_pts
                
                if settings['position'] == 'Снизу':
                    y_pts = page_h - y_pts
                    
                r = settings['color'].red() / 255
                g = settings['color'].green() / 255
                b = settings['color'].blue() / 255
                
                text = str(i + 1)
                p = fitz.Point(x_pts, y_pts)
                
                try:
                    page.insert_text(p, text, fontname=settings['font_family'], fontsize=settings['font_size'], color=(r, g, b), rotate=settings['angle'])
                except Exception:
                    page.insert_text(p, text, fontname="helv", fontsize=settings['font_size'], color=(r, g, b), rotate=settings['angle'])
                    
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить нумерацию:\n{e}")

    def load_document(self, file_name):
        """Обобщенная функция загрузки PDF-документа в интерфейс"""
        if file_name and file_name not in self.open_docs:
            doc = fitz.open(file_name)
            self.open_docs[file_name] = doc
            self.current_file_path = file_name
            self.doc = doc
            
            self.history_manager.history = [self.doc.write()]
            self.history_manager.index = 0
            
            self.active_page_index = 0
            self.fit_to_height() 
            self.render_thumbnails()
            self.update_page_info()
            self.page_input.setText("1")
            self.files_panel.refresh(self.open_docs)
        elif file_name in self.open_docs:
            self.switch_active_doc(file_name)

    def apply_booklet(self, settings):
        """Мультибуклет: разбивка на тетради (signatures)"""
        # ИСПРАВЛЕНО: Теперь используем self.doc, а не открываем файл заново
        if not self.doc:
            QMessageBox.critical(self, "Ошибка", "Нет открытого документа.")
            return

        try:
            # Работаем с текущим объектом self.doc
            N = len(self.doc)
            page_w = self.doc.load_page(0).rect.width
            page_h = self.doc.load_page(0).rect.height
            
            sig_size = settings.get('pages', N) if settings.get('type') == "many" else N
            mm_to_pts = 72 / 25.4
            inner_mm = settings.get('inner_offset', 0)
            outer_mm = settings.get('outer_offset', 0)
            
            shift_pts = (inner_mm - outer_mm) * mm_to_pts
            
            new_doc = fitz.open()
            
            for i in range(0, N, sig_size):
                chunk = list(range(i, min(i + sig_size, N)))
                while len(chunk) % 4 != 0:
                    chunk.append(-1)
                    
                num_sheets = len(chunk) // 4
                
                for s in range(num_sheets):
                    # Лицевая сторона листа
                    page_f = new_doc.new_page(width=page_w * 2, height=page_h)
                    left_f = chunk[-(1 + 2 * s)]
                    right_f = chunk[0 + 2 * s]
                    
                    if left_f != -1:
                        x0 = shift_pts 
                        rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                        page_f.show_pdf_page(rect, self.doc, left_f)
                    if right_f != -1:
                        x0 = page_w - shift_pts 
                        rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                        page_f.show_pdf_page(rect, self.doc, right_f)
                    
                    # Оборотная сторона листа
                    page_b = new_doc.new_page(width=page_w * 2, height=page_h)
                    left_b = chunk[1 + 2 * s]
                    right_b = chunk[-(2 + 2 * s)]
                    
                    if left_b != -1:
                        x0 = shift_pts
                        rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                        page_b.show_pdf_page(rect, self.doc, left_b)
                    if right_b != -1:
                        x0 = page_w - shift_pts
                        rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                        page_b.show_pdf_page(rect, self.doc, right_b)
            
            # Закрываем старый и подставляем новый
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.active_page_index = 0
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать буклет:\n{e}")

    def open_booklet_module(self):
        """Открытие модуля буклета"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        dialog = BookletDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_booklet(settings)

    # --- ДОБАВЛЕНО: МОДУЛЬ БУКЛЕТ В 2 СГИБА ---
    def open_booklet2_module(self):
        """Открытие модуля буклета в 2 сгиба"""
        if not self.doc:
            QMessageBox.warning(self, "Внимание", "Сначала откройте PDF файл.")
            return
        
        dialog = Booklet2Dialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self.apply_booklet2(settings)

    def apply_booklet2(self, settings):
        """Создание буклета в 2 сгиба (по 3 страницы на лист)"""
        if not self.doc:
            return

        try:
            N = len(self.doc)
            page_w = self.doc.load_page(0).rect.width
            page_h = self.doc.load_page(0).rect.height
            
            mm_to_pts = 72 / 25.4
            inner_pts = settings['inner_offset'] * mm_to_pts
            outer_pts = settings['outer_offset'] * mm_to_pts
            # Итоговый сдвиг крайних листов
            shift_pts = inner_pts - outer_pts
            
            # Переводим из 1-based в 0-based индексы для массива
            front_order = [x - 1 for x in settings['front']] 
            back_order = [x - 1 for x in settings['back']]   
            
            new_doc = fitz.open()
            
            # Обрабатываем документ блоками по 6 страниц
            for i in range(0, N, 6):
                # Собираем индексы текущего блока, отсутствующие заменяем на -1
                chunk = []
                for j in range(6):
                    chunk.append(i + j if i + j < N else -1)
                
                # --- Лицевая сторона (ширина 3 страниц) ---
                page_f = new_doc.new_page(width=page_w * 3, height=page_h)
                
                # Левая панель (сдвигается вправо при положительном shift)
                p_idx = front_order[0]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_f.show_pdf_page(rect, self.doc, chunk[p_idx])
                    
                # Правая панель (сдвигается влево при положительном shift)
                # Отрисовываем правую и левую ДО центральной, 
                # чтобы при сильном смещении центральная (неподвижная) страница скрывала под собой излишки
                p_idx = front_order[2]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w * 2 - shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_f.show_pdf_page(rect, self.doc, chunk[p_idx])

                # Центральная панель (ВСЕГДА стоит на месте - смещение не применяется)
                p_idx = front_order[1]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_f.show_pdf_page(rect, self.doc, chunk[p_idx])
                
                # --- Оборотная сторона ---
                page_b = new_doc.new_page(width=page_w * 3, height=page_h)
                
                # Левая панель
                p_idx = back_order[0]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_b.show_pdf_page(rect, self.doc, chunk[p_idx])
                    
                # Правая панель
                p_idx = back_order[2]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w * 2 - shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_b.show_pdf_page(rect, self.doc, chunk[p_idx])

                # Центральная панель (ВСЕГДА стоит на месте)
                p_idx = back_order[1]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_b.show_pdf_page(rect, self.doc, chunk[p_idx])
                    
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.active_page_index = 0
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать буклет в 2 сгиба:\n{e}")
    # ----------------------------------------

    def switch_active_doc(self, file_path):
        """Переключение на другой открытый документ"""
        if file_path in self.open_docs:
            self.current_file_path = file_path
            self.doc = self.open_docs[file_path]
            self.history_manager.history = [self.doc.write()]
            self.history_manager.index = 0
            
            self.active_page_index = 0
            self.fit_to_height()
            self.render_thumbnails()
            self.update_page_info()
            self.page_input.setText("1")

    def toggle_files_panel(self):
        is_visible = self.files_panel.isVisible()
        self.files_panel.setVisible(not is_visible)
        self.btn_toggle_files.setText("▶" if not is_visible else "◀")

    def close_specific_document(self, file_path):
        """Закрывает конкретный документ"""
        if file_path in self.open_docs:
            doc = self.open_docs[file_path]
            if doc:
                doc.close()
            if self.current_file_path == file_path:
                self.doc = None
            del self.open_docs[file_path]
            
            if self.current_file_path == file_path:
                if self.open_docs:
                    new_path = list(self.open_docs.keys())[0]
                    self.switch_active_doc(new_path)
                else:
                    self.clear_interface()
            self.files_panel.refresh(self.open_docs)

    def close_document(self):
        """Закрывает текущий активный документ."""

        # Нормальный сохранённый документ
        if self.current_file_path:
            self.close_specific_document(self.current_file_path)
            return

        # Документ из ImageToPDF, который ещё не сохранён
        if self.doc is not None:
            try:
                self.doc.close()
            except Exception:
                pass

            self.clear_interface()

    def clear_interface(self):
        """Полная очистка интерфейса если документов нет"""
        self.doc = None
        self.current_file_path = None
        self.active_page_index = -1
        self.history_manager.history = []
        self.history_manager.index = -1
        
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
                    
        self.page_widgets = []
        self.thumb_widgets = []
        self.info_label.setText("Размер: 0x0 мм | Листов: 0")
        self.page_input.setText("0")

    def save_file(self):
        """Сохраняет текущий PDF.
        
        Если документ уже был открыт из файла и сохраняется под тем же именем,
        сначала создаётся временный PDF, а затем он заменяет оригинал.
        """

        if not self.doc:
            QMessageBox.warning(
                self,
                "Внимание",
                "Нет открытого документа для сохранения."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить PDF",
            self.current_file_path if self.current_file_path else "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Добавляем .pdf, если пользователь его не написал
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        try:
            import os
            import tempfile

            old_path = self.current_file_path

            # -------------------------------------------------
            # СЛУЧАЙ 1:
            # сохраняем поверх уже открытого файла
            # -------------------------------------------------
            if old_path and os.path.abspath(file_path) == os.path.abspath(old_path):

                directory = os.path.dirname(os.path.abspath(file_path))

                fd, temp_path = tempfile.mkstemp(
                    suffix=".pdf",
                    dir=directory
                )
                os.close(fd)

                try:
                    # Сначала сохраняем во временный файл
                    self.doc.save(
                        temp_path,
                        garbage=4,
                        deflate=True
                    )

                    # Закрываем текущий объект, чтобы освободить старый файл
                    # перед заменой
                    old_doc = self.doc

                    # Удаляем старую запись из open_docs
                    if old_path in self.open_docs:
                        del self.open_docs[old_path]

                    try:
                        old_doc.close()
                    except Exception:
                        pass

                    # Заменяем старый PDF новым
                    os.replace(temp_path, file_path)

                    # Открываем уже сохранённый PDF заново
                    new_doc = fitz.open(file_path)

                    self.doc = new_doc
                    self.current_file_path = file_path
                    self.open_docs[file_path] = new_doc

                finally:
                    # Если временный файл остался после ошибки
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

            # -------------------------------------------------
            # СЛУЧАЙ 2:
            # сохраняем под новым именем
            # -------------------------------------------------
            else:

                # Если такое имя уже существует — удаляем старую
                # временную версию перед записью
                if os.path.exists(file_path):
                    os.remove(file_path)

                # Сохраняем текущий документ
                self.doc.save(
                    file_path,
                    garbage=4,
                    deflate=True
                )

                # Если старый документ был открыт под другим путём,
                # удаляем старую связь
                if old_path and old_path != file_path:
                    if old_path in self.open_docs:
                        del self.open_docs[old_path]

                # Регистрируем новый путь
                self.current_file_path = file_path
                self.open_docs[file_path] = self.doc

            # Обновляем панель документов
            self.files_panel.refresh(self.open_docs)

            # Обновляем информацию
            self.update_page_info()

            QMessageBox.information(
                self,
                "Успех",
                f"Файл успешно сохранён:\n{file_path}"
            )

        except Exception as e:
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить PDF:\n\n{e}"
            )
        
    def delete_page(self, page_index):
        if not self.doc or len(self.doc) <= 1: return
        self.doc.delete_page(page_index)
        self.active_page_index = min(page_index, len(self.doc) - 1)
        self.render_all()
        self.history_manager.save_state()

    def insert_empty_page(self, page_index):
        if not self.doc: return
        ref_idx = page_index if page_index < len(self.doc) else page_index - 1
        if ref_idx < 0: ref_idx = 0
        ref_page = self.doc.load_page(ref_idx)
        w, h = ref_page.rect.width, ref_page.rect.height
        
        self.doc.new_page(page_index, width=w, height=h)
        self.active_page_index = page_index
        self.render_all()
        self.history_manager.save_state()

    def duplicate_page(self, page_index):
        """Дублирование страницы"""
        if not self.doc:
            return

        try:
            page_count_before = len(self.doc)

            # Создаем копию страницы в конец документа
            self.doc.fullcopy_page(page_index)

            # Индекс новой страницы
            new_index = page_count_before

            # Перемещаем копию сразу после оригинала
            self.doc.move_page(new_index, page_index + 1)

            self.active_page_index = page_index + 1

            self.render_all()
            self.history_manager.save_state()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось дублировать страницу:\n{e}"
            )

    def move_page(self, source_idx, target_idx):
        if not self.doc or source_idx == target_idx: return
        
        # ИСПРАВЛЕНИЕ: Обход особенности PyMuPDF. При сдвиге на 1 шаг вниз (idx -> idx+1), 
        # библиотека ничего не делает из-за сдвига индексов. Решение - сдвигать нижний лист наверх.
        if target_idx == source_idx + 1:
            self.doc.move_page(target_idx, source_idx)
        else:
            self.doc.move_page(source_idx, target_idx)
            
        self.active_page_index = target_idx
        self.render_all()
        self.history_manager.save_state()

    def handle_pdftransfer_drop(
        self,
        source_path,
        source_page_indexes,
        target_page_index
    ):
        """
        Копирует одну или несколько страниц из PDF
        окна «Обмен страницами» в текущий документ.

        source_page_indexes — список индексов страниц
        исходного PDF.

        Страницы вставляются ПЕРЕД страницей,
        на которую выполнено перетаскивание.
        """

        if not self.doc:

            QMessageBox.warning(
                self,
                "Внимание",
                "Сначала откройте PDF файл."
            )

            return False

        try:

            # --------------------------------------------------
            # Нормализуем список
            # --------------------------------------------------

            if isinstance(
                source_page_indexes,
                int
            ):
                source_page_indexes = [
                    source_page_indexes
                ]

            source_page_indexes = sorted(
                set(
                    int(x)
                    for x in source_page_indexes
                )
            )

            if not source_page_indexes:
                return False

            # --------------------------------------------------
            # Ищем окно «Обмен страницами»
            # --------------------------------------------------

            source_dialog = None

            for dlg in getattr(
                self,
                "_pdftransfer_dialogs",
                []
            ):

                dlg_path = os.path.abspath(
                    getattr(
                        dlg,
                        "file_path",
                        ""
                    )
                )

                if (
                    dlg_path == source_path
                    and getattr(
                        dlg,
                        "source_doc",
                        None
                    ) is not None
                ):

                    if not dlg.source_doc.is_closed:

                        source_dialog = dlg
                        break

            # --------------------------------------------------

            if source_dialog is None:

                QMessageBox.warning(
                    self,
                    "Обмен страницами",
                    "Не удалось определить исходный PDF."
                )

                return False

            source_doc = source_dialog.source_doc

            # --------------------------------------------------
            # Проверяем страницы
            # --------------------------------------------------

            valid_pages = []

            for page_index in source_page_indexes:

                if (
                    0 <= page_index < len(source_doc)
                ):

                    valid_pages.append(
                        page_index
                    )

            if not valid_pages:
                return False

            # --------------------------------------------------
            # Место вставки
            #
            # Вставляем ПЕРЕД страницей,
            # на которую бросили.
            # --------------------------------------------------

            insert_at = max(
                0,
                min(
                    int(target_page_index),
                    len(self.doc)
                )
            )

            # --------------------------------------------------
            # КОПИРУЕМ СТРАНИЦЫ ПО ОДНОЙ
            #
            # Это важно!
            #
            # Нельзя сделать один insert_pdf() от первой
            # до последней страницы, потому что между ними
            # могут находиться невыбранные страницы.
            # --------------------------------------------------

            for page_index in valid_pages:

                self.doc.insert_pdf(
                    source_doc,
                    from_page=page_index,
                    to_page=page_index,
                    start_at=insert_at
                )

                # Следующая выбранная страница должна
                # попасть сразу после предыдущей.
                insert_at += 1

            # --------------------------------------------------
            # Выбираем последнюю вставленную страницу
            # --------------------------------------------------

            self.active_page_index = insert_at - 1

            # --------------------------------------------------
            # Обновляем интерфейс
            # --------------------------------------------------

            self.render_all()

            # --------------------------------------------------
            # Сохраняем одно состояние Undo
            # для всей операции
            # --------------------------------------------------

            self.history_manager.save_state()

            self.page_input.setText(
                str(self.active_page_index + 1)
            )

            return True

        except Exception as e:

            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось скопировать страницы:\n\n{e}"
            )

            return False

    def render_all(self):
        if not self.doc: return
        self.render_thumbnails()
        self.render_pages()
        self.update_page_info()
        self.handle_page_click(self.active_page_index)

    def set_rulers_mode(self, enabled):
        self.rulers_enabled = enabled
        active_style = "background-color: #0078d7; color: white; font-weight: bold; font-size: 10px; border-radius: 4px; padding: 4px 8px;"
        inactive_style = "background-color: #e0e0e0; color: black; font-size: 10px; border-radius: 4px; padding: 4px 8px;"
        
        if enabled:
            self.btn_rulers_on.setStyleSheet(active_style)
            self.btn_rulers_off.setStyleSheet(inactive_style)
        else:
            self.btn_rulers_on.setStyleSheet(inactive_style)
            self.btn_rulers_off.setStyleSheet(active_style)
            
        show_rulers_flag = (self.pages_in_row == 1) and self.rulers_enabled
        for widget in self.page_widgets:
            widget.show_rulers = show_rulers_flag
            widget.update_style()

    def set_scroll_mode(self, mode):
        self.scroll_mode = mode
        active_style = "background-color: #0078d7; color: white; font-weight: bold; font-size: 10px; border-radius: 4px; padding: 4px;"
        inactive_style = "background-color: #e0e0e0; color: black; font-size: 10px; border-radius: 4px; padding: 4px;"
        
        if mode == 'continuous':
            self.btn_scroll_cont.setStyleSheet(active_style)
            self.btn_scroll_page.setStyleSheet(inactive_style)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.btn_scroll_cont.setStyleSheet(inactive_style)
            self.btn_scroll_page.setStyleSheet(active_style)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

   # ==========================================================
    # DRAG & DROP PDF ФАЙЛОВ ИЗ ПРОВОДНИКА
    # ==========================================================

    def dragEnterEvent(self, event):
        """Разрешаем перетаскивание PDF файлов в окно LibrePage."""

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return

        event.ignore()


    def dragMoveEvent(self, event):
        """Разрешаем перемещение PDF над окном."""

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return

        event.ignore()


    def dropEvent(self, event):
        """Открываем PDF после сброса файла."""

        if not event.mimeData().hasUrls():
            event.ignore()
            return

        opened = False

        for url in event.mimeData().urls():

            if not url.isLocalFile():
                continue

            file_path = url.toLocalFile()

            if not file_path.lower().endswith(".pdf"):
                continue

            try:
                self.load_document(file_path)
                opened = True

            except Exception as e:
                traceback.print_exc()

                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось открыть PDF:\n\n{file_path}\n\n{e}"
                )

        if opened:
            event.acceptProposedAction()
        else:
            event.ignore()


    def eventFilter(self, obj, event):

        if (
            obj == self.scroll_area.viewport()
            and event.type() == QEvent.Type.Wheel
        ):

            # ==================================================
            # ОБЫЧНОЕ КОЛЕСО
            # ==================================================

            if self.scroll_mode == 'page':

                delta = event.angleDelta().y()

                if delta > 0:
                    self.navigate_page(-1)

                elif delta < 0:
                    self.navigate_page(1)

                return True

        return super().eventFilter(obj, event)

    def navigate_page(self, direction):
        if not self.doc: return
        current = self.active_page_index if self.active_page_index != -1 else 0
        new_page_index = current + direction
        if 0 <= new_page_index < len(self.doc):
            self.page_input.setText(str(new_page_index + 1))
            self.go_to_page()

    def handle_page_click(self, page_index, pos_x=None, pos_y=None):
        # 1. Логика выделения страницы
        self.active_page_index = page_index
        self.page_input.setText(str(page_index + 1))
        
        for widget in self.page_widgets:
            widget.set_active(widget.page_index == self.active_page_index)
            
        for thumb in self.thumb_widgets:
            thumb.set_active(thumb.page_index == self.active_page_index)

        # 2. Логика выбора изображения, если включен режим
        if self.is_image_select_mode and pos_x is not None and pos_y is not None:
            # Переводим из пикселей экрана в PDF points
            zoom_factor = self.current_zoom / 100.0
            pdf_x = pos_x / zoom_factor
            pdf_y = pos_y / zoom_factor
            
            page = self.doc.load_page(page_index)
            # Пробуем выделить фото по координатам
            self.image_selection_manager.select_image_at(page, page_index, pdf_x, pdf_y)
            # Перерисовываем страницы, чтобы обновить синюю рамку выделения
            self.render_pages()

    def center_page_in_view(self):
        best_candidate = None
        for widget in self.page_widgets:
            if widget.is_active or widget.is_selected:
                best_candidate = widget
                break
        
        if not best_candidate and self.page_widgets:
            best_candidate = self.page_widgets[0]
            
        if best_candidate:
            QApplication.processEvents() 
            viewport_h = self.scroll_area.viewport().height()
            widget_center_y = best_candidate.geometry().center().y()
            self.scroll_area.verticalScrollBar().setValue(widget_center_y - (viewport_h // 2))

    def update_button_styles(self, active_btn):
        active_style = "background-color: #0078d7; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;"
        inactive_style = "background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 4px; padding: 4px 8px;"
        
        for btn in self.mode_buttons:
            if btn == active_btn:
                btn.setStyleSheet(active_style)
            else:
                btn.setStyleSheet(inactive_style)

    def toggle_thumbnail_panel(self):
        is_visible = self.thumb_panel.isVisible()
        self.thumb_panel.setVisible(not is_visible)
        self.btn_toggle_thumb.setText("◀" if not is_visible else "▶")

    def toggle_thumb_columns(self):
        if self.thumb_columns == 2:
            self.thumb_columns = 1
            self.btn_toggle_cols.setText("Переключить в 2 колонки")
        else:
            self.thumb_columns = 2
            self.btn_toggle_cols.setText("Переключить в 1 колонку")
        self.render_thumbnails()

    def thumbnail_clicked(self, page_index):
        self.handle_page_click(page_index)
        row = page_index // self.pages_in_row
        col = page_index % self.pages_in_row
        item = self.preview_layout.itemAtPosition(row, col)
        if item and item.widget():
            self.scroll_area.ensureWidgetVisible(item.widget(), 10, 10)

    def set_page_count(self, count, sender_btn=None):
        """
        Устанавливает количество страниц в одном ряду.

        1, 2 страницы  -> подгонка по высоте.
        3, 5, 7 страниц -> подгонка по ширине окна.
        """

        if not self.doc:
            return

        # --------------------------------------------------
        # Устанавливаем количество страниц в ряду
        # --------------------------------------------------

        self.pages_in_row = count

        if sender_btn:
            self.update_button_styles(sender_btn)

        # --------------------------------------------------
        # 1 и 2 страницы:
        # выравниваем по высоте
        # --------------------------------------------------

        if count in (1, 2):

            self.fit_to_height()

        # --------------------------------------------------
        # 3, 5 и 7 страниц:
        # все страницы должны полностью
        # помещаться по ширине окна
        # --------------------------------------------------

        elif count in (3, 5, 7):

            self.fit_to_width()

        # --------------------------------------------------
        # Линейки показываем только при одном листе
        # --------------------------------------------------

        show_rulers_flag = (
            self.pages_in_row == 1
            and self.rulers_enabled
        )

        for widget in self.page_widgets:

            widget.show_rulers = show_rulers_flag
            widget.update_style()

        # --------------------------------------------------
        # Обновляем отображение
        # --------------------------------------------------

        self.render_pages()

        self.center_page_in_view()

    def fit_to_width(self, margin=20, sender_btn=None):
        """
        Автоматически подгоняет страницы текущего ряда
        по ширине окна.

        Используется для 3, 5 и 7 страниц в ряду.
        """

        if not self.doc:
            return

        if sender_btn:
            self.update_button_styles(sender_btn)

        # --------------------------------------------------
        # Видимая область
        # --------------------------------------------------

        viewport = self.scroll_area.viewport()

        view_w = viewport.width()

        if view_w <= 0:
            return

        # --------------------------------------------------
        # Реальные отступы layout
        # --------------------------------------------------

        layout = self.preview_layout

        margins = layout.contentsMargins()

        left_margin = margins.left()
        right_margin = margins.right()

        spacing = layout.horizontalSpacing()

        if spacing < 0:
            spacing = 0

        # --------------------------------------------------
        # Доступная ширина
        # --------------------------------------------------

        available_w = view_w

        available_w -= left_margin
        available_w -= right_margin

        # Безопасный запас слева и справа
        available_w -= margin * 2

        # Промежутки между листами
        if self.pages_in_row > 1:

            available_w -= (
                spacing *
                (self.pages_in_row - 1)
            )

        # --------------------------------------------------
        # Защита
        # --------------------------------------------------

        if available_w <= 0:
            return

        # --------------------------------------------------
        # Находим максимальную ширину страницы
        # в текущем ряду
        # --------------------------------------------------

        start_page = (
            self.active_page_index
            if self.active_page_index >= 0
            else 0
        )

        # Начало ряда
        row_start = (
            start_page // self.pages_in_row
        ) * self.pages_in_row

        max_page_width = 0

        for i in range(self.pages_in_row):

            page_index = row_start + i

            if page_index >= len(self.doc):
                break

            page = self.doc.load_page(page_index)

            page_width = page.rect.width

            if page_width > max_page_width:
                max_page_width = page_width

        # --------------------------------------------------
        # Защита
        # --------------------------------------------------

        if max_page_width <= 0:
            return

        # --------------------------------------------------
        # Ширина, которую может занимать один лист
        # --------------------------------------------------

        page_display_width = (
            available_w /
            self.pages_in_row
        )

        # Для 5 и 7 листов немного уменьшаем размер,
        # чтобы последний лист гарантированно помещался.
        if self.pages_in_row == 5:
            page_display_width *= 0.96

        elif self.pages_in_row == 7:
            page_display_width *= 0.94

        # --------------------------------------------------
        # Рассчитываем реальный PDF zoom
        # --------------------------------------------------

        self.current_zoom = int(
            (
                page_display_width /
                max_page_width
            ) * 100
        )

        if self.current_zoom < 10:
            self.current_zoom = 10

        # --------------------------------------------------
        # Рендер
        # --------------------------------------------------

        self.render_pages()

        self.center_page_in_view()

    def get_page_size_mm(self, page):
        width_mm = page.rect.width * 25.4 / 72
        height_mm = page.rect.height * 25.4 / 72
        return width_mm, height_mm

    def update_page_info(self):
        if not self.doc: return
        
        viewport = self.scroll_area.viewport()
        viewport_y = self.scroll_area.verticalScrollBar().value()
        viewport_rect = QRect(0, viewport_y, viewport.width(), viewport.height())
        
        best_candidate = None
        max_intersection_area = 0
        
        for widget in self.page_widgets:
            widget_pos = widget.mapTo(self.preview_container, QPoint(0, 0))
            widget_rect = QRect(widget_pos, widget.size())
            
            intersection = viewport_rect.intersected(widget_rect)
            intersection_area = intersection.width() * intersection.height()
            
            if self.pages_in_row == 1:
                widget.set_selected(False)
            
            if self.pages_in_row == 1:
                widget_total_area = widget.width() * widget.height()
                if widget_total_area > 0:
                    ratio = intersection_area / widget_total_area
                    if ratio > 0.5:
                        if intersection_area > max_intersection_area:
                            max_intersection_area = intersection_area
                            best_candidate = widget
        
        if self.pages_in_row == 1 and best_candidate:
            best_candidate.set_selected(True)
            
            if self.active_page_index != best_candidate.page_index and self.scroll_mode == 'continuous':
                self.handle_page_click(best_candidate.page_index)
                
            widget_total_area = best_candidate.width() * best_candidate.height()
            if widget_total_area > 0:
                ratio = max_intersection_area / widget_total_area
                if ratio > 0.9 and self.scroll_mode == 'continuous':
                    if not viewport_rect.contains(best_candidate.geometry().center()):
                        self.scroll_area.ensureWidgetVisible(best_candidate, 0, 50)

        pos = viewport_y
        total_pages = len(self.doc)
        current_page = 1
        for i in range(total_pages):
            row = i // self.pages_in_row
            col = i % self.pages_in_row
            item = self.preview_layout.itemAtPosition(row, col)
            if item and item.widget():
                if item.widget().geometry().y() + (item.widget().geometry().height() / 2) >= pos:
                    current_page = i + 1
                    break
        page_index = max(0, min(current_page - 1, total_pages - 1))
        current_page_obj = self.doc.load_page(page_index)
        w, h = self.get_page_size_mm(current_page_obj)
        # Обновленный текст (без стр)
        self.info_label.setText(f"Размер: {w:.1f}x{h:.1f} мм | Листов: {total_pages}")
        if not self.page_input.hasFocus():
            self.page_input.setText(str(min(current_page, total_pages)))

    def go_to_page(self):
        if not self.doc: return
        try:
            target_page = int(self.page_input.text())
            total_pages = len(self.doc)
            if target_page < 1: target_page = 1
            elif target_page > total_pages: target_page = total_pages
            self.handle_page_click(target_page - 1)
            row = (target_page - 1) // self.pages_in_row
            col = (target_page - 1) % self.pages_in_row
            item = self.preview_layout.itemAtPosition(row, col)
            if item and item.widget():
                self.scroll_area.ensureWidgetVisible(item.widget(), 10, 10)
        except ValueError: pass 

      
    def fit_to_height(self, sender_btn=None):
        if not self.doc:
            return

        if sender_btn:
            self.update_button_styles(sender_btn)

        # Используем ТЕКУЩУЮ активную страницу,
        # а не всегда первую страницу документа
        page_index = self.active_page_index

        if page_index < 0 or page_index >= len(self.doc):
            page_index = 0

        page = self.doc.load_page(page_index)
        page_h = page.rect.height

        view_h = self.scroll_area.viewport().height()

        if self.pages_in_row == 1 and self.rulers_enabled:
            view_h -= 40

        if page_h <= 0:
            return

        # --------------------------------------------------
        # Реальный технический масштаб PDF.
        #
        # Этот размер считается за 100%
        # в новом "МАСШТАБ ЛИСТА".
        # --------------------------------------------------

        self.current_zoom = int(
            (view_h / page_h) * 100
        )

        if self.current_zoom < 10:
            self.current_zoom = 10

        # Новый масштаб листа:
        # размер "По высоте" = 100%
        if hasattr(self, "page_zoom"):
            self.page_zoom.set_100_percent()

        self.render_pages()
        self.center_page_in_view()

    
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть PDF", "", "PDF Files (*.pdf)")
        if file_name:
            self.load_document(file_name)

    def open_image_to_pdf(self):
        """Открывает модуль Image в PDF."""

        dialog = ImageToPdfDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.created_doc is not None:
                self.open_created_pdf(dialog.created_doc)

    def open_created_pdf(self, new_doc):
        """Открывает PDF, созданный модулем Image в PDF."""

        try:
            # Если был открыт старый документ без сохранённых изменений —
            # просто оставляем его в списке открытых документов.
            if self.doc is not None and self.current_file_path:
                self.open_docs[self.current_file_path] = self.doc

            # Новый документ становится активным
            self.doc = new_doc

            # Пока он не сохранён
            self.current_file_path = None

            # Первая страница
            self.active_page_index = 0

            # Сбрасываем историю
            self.history_manager.history = [self.doc.write()]
            self.history_manager.index = 0

            # Обновляем отображение
            self.fit_to_height()
            self.render_thumbnails()
            self.update_page_info()

            self.page_input.setText("1")

            # Обновляем список документов
            self.files_panel.refresh(self.open_docs)

            self.update()

        except Exception as e:
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть созданный PDF:\n\n{e}"
        
            )

    def render_thumbnails(self):
        if not self.doc:
            return

        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self.thumb_widgets = []

        # Фиксированная ширина миниатюры.
        # Высота будет рассчитываться отдельно для каждой страницы
        # по её реальным пропорциям.
        THUMB_WIDTH = 100

        zoom_factor = 1.5

        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)

            # Рендерим КАЖДУЮ страницу в её собственном размере
            pix = page.get_pixmap(
                matrix=fitz.Matrix(zoom_factor, zoom_factor),
                alpha=False
            )

            img = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888
            )

            pixmap = QPixmap.fromImage(img)

            # Номер страницы
            pixmap = add_number_to_pixmap(
                pixmap,
                page_num + 1
            )

            # --------------------------------------------------
            # ВАЖНО:
            # высота рассчитывается по реальному соотношению
            # ширины и высоты ИМЕННО ЭТОЙ страницы.
            # --------------------------------------------------
            if pixmap.width() > 0:
                thumb_height = round(
                    THUMB_WIDTH * pixmap.height() / pixmap.width()
                )
            else:
                thumb_height = 140

            pixmap = pixmap.scaled(
                THUMB_WIDTH,
                thumb_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # Контейнер конкретной миниатюры
            container = QWidget()

            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(0, 0, 0, 0)
            v_layout.setSpacing(0)

            label = ClickableThumbnail(
                page_num,
                self.thumbnail_clicked,
                self.mouse_handler,
                self
            )

            label.setPixmap(pixmap)

            if page_num == self.active_page_index:
                label.set_active(True)

            self.thumb_widgets.append(label)

            v_layout.addWidget(
                label,
                alignment=Qt.AlignmentFlag.AlignCenter
            )

            self.thumb_layout.addWidget(
                container,
                page_num // self.thumb_columns,
                page_num % self.thumb_columns
            )

    def render_pages(self):
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item and item.widget(): item.widget().deleteLater()
        
        self.page_widgets = []
        zoom_factor = self.current_zoom / 100.0
        
        show_rulers_flag = (self.pages_in_row == 1) and self.rulers_enabled
        
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            
            w_mm, h_mm = self.get_page_size_mm(page)
            pixels_per_mm = pix.width / w_mm if w_mm > 0 else 1.0
            
            # Добавлены новые аргументы zoom_factor и image_selection_manager
            label = PageWidget(QPixmap.fromImage(img), page_num, self.handle_page_click, pixels_per_mm, show_rulers_flag, w_mm, h_mm, zoom_factor, self.image_selection_manager)
            
            if page_num == self.active_page_index:
                label.set_active(True)
            
            self.preview_layout.addWidget(
                label,
                page_num // self.pages_in_row,
                page_num % self.pages_in_row,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            )
            self.page_widgets.append(label)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Определяем путь к изображению в той же папке, что и main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    splash_image_path = os.path.join(base_dir, "logostart.png")
    
    # Загружаем картинку
    if os.path.exists(splash_image_path):
        splash_pixmap = QPixmap(splash_image_path)
        # Создаем окно заставки без рамок и всегда поверх других окон
        splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        # Обязательный флаг для поддержки прозрачности (альфа-канала) картинки
        splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        splash.show()
        # Отрисовываем заставку до начала других вычислений
        app.processEvents()
    else:
        splash = None
    
    # Инициализируем главное окно (но пока не показываем)
    window = BaseImposingModule("LibrePageKST v.0.5")
    
    # Функция для скрытия заставки и показа главного окна
    def show_main_window():
        if splash: splash.finish(window) # Передаем фокус главному окну
        window.show()
        
    # Запускаем функцию show_main_window ровно через 4 секунды (4000 мс)
    QTimer.singleShot(4000, show_main_window)
    
    sys.exit(app.exec())