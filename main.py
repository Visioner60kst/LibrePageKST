import sys
import fitz  # PyMuPDF
import subprocess
import os
import traceback
import tempfile
import platform
import shutil
from PIL import Image, ImageEnhance # Needed for correction
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                             QSlider, QMessageBox, QFileDialog, QGridLayout,
                             QLineEdit, QSplitter, QSizePolicy, QMenu, QSplashScreen,
                             QDialog, QComboBox, QFrame, QTextEdit)
from PyQt6.QtCore import Qt, QRect, QPoint, QEvent, QMimeData, QTimer
from PyQt6.QtGui import QImage, QPixmap, QIntValidator, QDrag, QPainter, QPen, QColor

# Importing rulers from our new module
from rulers import HorizontalRuler, VerticalRuler

# Importing new modules
from pagemouse import ThumbnailHandler
from imagetopdf import ImageToPdfDialog
from files import FilesPanel
from booklet import BookletDialog
from booklet2 import Booklet2Dialog  # NEW MODULE: Booklet in 2 fold
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
from photocorrection import PhotoCorrectionDialog # NEW MODULE
from openeditphoto import ExternalEditorDialog # NEW MODULE
from fields import FieldsDialog # NEW MODULE: Fields+

# IMPORTING PRINT MODULE (replace PrintDialog/start_print class for that name/function that is used in print.py)
import print as print_module


# Custom widget for displaying a page with the ability to select and click
class PageWidget(QWidget):

    def __init__(self, pixmap, page_index, callback, pixels_per_mm=1.0, show_rulers=True, page_w_mm=0, page_h_mm=0, zoom_factor=1.0, selection_manager=None):
        super().__init__()
        self.page_index = page_index
        self.callback = callback
        self.is_selected = False  # For scrolling
        self.is_active = False
        self.show_rulers = show_rulers # Flag to control display of rulers
        self.zoom_factor = zoom_factor
        self.selection_manager = selection_manager
        
        # Drawing a blue frame for the selected photo if it is on this page
        if self.selection_manager and self.selection_manager.selected_page_index == self.page_index and self.selection_manager.selected_bbox:
            painter = QPainter(pixmap)
            pen = QPen(QColor(0, 0, 255)) # Blue frame
            pen.setWidth(3)
            painter.setPen(pen)
            
            bbox = self.selection_manager.selected_bbox
            # Converting coordinates from PDF points in pixels QPixmap
            x = bbox.x0 * self.zoom_factor
            y = bbox.y0 * self.zoom_factor
            w = (bbox.x1 - bbox.x0) * self.zoom_factor
            h = (bbox.y1 - bbox.y0) * self.zoom_factor
            
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.end()

        # Setting up a grid for placing rulers and page images
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Initializing the rulers
        self.h_ruler = HorizontalRuler()
        self.v_ruler = VerticalRuler()
        self.h_ruler.set_zoom(pixels_per_mm)
        self.v_ruler.set_zoom(pixels_per_mm)

        # FIX: Passing the physical page size to the rulers
        if hasattr(self.h_ruler, 'set_page_size'):
            self.h_ruler.set_page_size(page_w_mm)
        if hasattr(self.v_ruler, 'set_page_size'):
            self.v_ruler.set_page_size(page_h_mm)
        
        # Image of the leaf itself
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Placing elements: (0, 0) remains empty (corner)
        # (0, 1) - horizon ruler, (1, 0) - vertical ruler, (1, 1) - the sheet itself
        self.layout.addWidget(self.h_ruler, 0, 1)
        self.layout.addWidget(self.v_ruler, 1, 0)
        self.layout.addWidget(self.image_label, 1, 1)
        
        self.update_style()

    def update_style(self):
        # If active (selected for printing) - bold blue frame
        # If simply selected by scroll - a regular blue frame
        if self.is_active:
            self.image_label.setStyleSheet("border: 4px solid #0000FF;")
        elif self.is_selected:
            self.image_label.setStyleSheet("border: 2px solid blue;")
        else:
            self.image_label.setStyleSheet("border: 2px solid transparent;")
            
        # Activate/deactivable ambulances (are drawn only on the active sheet And if allowed by the mode)
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
            # Calculate the position of the click relative to the image itself (excluding rulers)
            pos_in_image = self.image_label.mapFrom(self, event.pos())
            if 0 <= pos_in_image.x() < self.image_label.width() and 0 <= pos_in_image.y() < self.image_label.height():
                self.callback(self.page_index, pos_in_image.x(), pos_in_image.y())
            else:
                self.callback(self.page_index)


# Helper class for clickable thumbnails
class ClickableThumbnail(QLabel):

    def __init__(self, page_index, callback, handler):
        super().__init__()
        self.page_index = page_index
        self.callback = callback
        self.handler = handler
        self.is_active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()
        self.setAcceptDrops(True) # NEW: Allow receiving files Drag&Drop

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
            self.drag_start_pos = event.pos() # Remember the position for dragging
            self.callback(self.page_index)
        elif event.button() == Qt.MouseButton.RightButton:
            self.handler.handle_context_menu(self, event.pos())

    # NEW: Handle mouse movement for start Drag & Drop
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, 'drag_start_pos'):
            return
        # Checking that the cursor has moved enough to start dragging
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.page_index))
        drag.setMimeData(mime_data)
        
        # Create a semi-transparent sketch for a drag effect
        pixmap = self.pixmap()
        if pixmap:
            drag.setPixmap(pixmap.scaledToWidth(80, Qt.TransformationMode.SmoothTransformation))
            drag.setHotSpot(QPoint(drag.pixmap().width() // 2, drag.pixmap().height() // 2))
            
        drag.exec(Qt.DropAction.MoveAction)

    # NEW: Allow you to drag and drop data above this widget
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    # NEW: CRITICAL for dragging backwards (up/left).
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    # NEW: Handle draggable page reset
    def dropEvent(self, event):
        source_index_str = event.mimeData().text()
        if source_index_str.isdigit():
            source_index = int(source_index_str)
            target_index = self.page_index
            if source_index != target_index:
                if hasattr(self.handler, 'handle_drag_drop'):
                    self.handler.handle_drag_drop(source_index, target_index)
                event.acceptProposedAction()


# Dialog box for replacing missing fonts
class MissingFontDialog(QDialog):
    def __init__(self, missing_font_name, system_fonts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing font!")
        self.setModal(True)
        self.resize(550, 150)
        self.result_action = "skip"
        self.selected_font_path = None
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(f"<b>Attention!</b> Missing font detected during conversion:<br>"
                      f"<span style='color: #d32f2f; font-size: 14px;'><b>{missing_font_name}</b></span><br><br>"
                      f"The font is not embedded in PDF and is missing from your system.<br>"
                      f"Select the system font to replace, or skip this sheet.", self)
        layout.addWidget(lbl)
        
        btn_layout = QHBoxLayout()
        
        # Left side (list and REPLACE button)
        left_layout = QHBoxLayout()
        self.combo_fonts = QComboBox(self)
        self.combo_fonts.setMinimumWidth(200)
        for name, path in system_fonts.items():
            self.combo_fonts.addItem(name, path)
            
        btn_replace = QPushButton("REPLACE", self)
        btn_replace.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
        btn_replace.clicked.connect(self.on_replace)
        
        left_layout.addWidget(self.combo_fonts)
        left_layout.addWidget(btn_replace)
        
        # Right side (SKIP SHEET button)
        btn_skip = QPushButton("SKIP THE LETTER", self)
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
        self.setWindowTitle("License")
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
            self.text_edit.setPlainText("File LICENSE.txt not found.")
        layout.addWidget(QLabel("License Agreement:"))
        layout.addWidget(self.text_edit)

class BaseImposingModule(QMainWindow):

    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1300, 800)
        self.current_zoom = 100
        
        self.open_docs = {} # Dictionary {path: doc}
        self.doc = None
        self.pages_in_row = 1
        self.current_file_path = None  # We store the path to the open file
        self.page_widgets = [] # List for page widgets
        self.thumb_widgets = [] # List for thumbnail widgets
        self.active_page_index = -1 # Index of the page selected for printing
        self.rulers_enabled = True # Status of inclusion of rulers

        # NEW: Photo Selection Manager
        self.image_selection_manager = ImageSelectionManager()
        self.is_image_select_mode = False
        
        # NEW: Storing path to external editor
        self.external_editor_path = None
        
        # Initializing the mouse handler
        self.mouse_handler = ThumbnailHandler(self)
        
        # Undo module
        self.history_manager = HistoryManager(self)
        
        # List of buttons for managing styles
        self.mode_buttons = []
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top panel (converted to group layout)
        top_bar_container = QVBoxLayout()
        top_bar_container.setContentsMargins(5, 5, 5, 5)

        top_row1 = QHBoxLayout()
        top_row2 = QHBoxLayout()
        
        # Setting the distance between groups (10px) - exactly at 2 times the distance between the buttons (5px)
        top_row1.setSpacing(20)
        top_row2.setSpacing(20)

        # Style
        btn_style = "background-color: #e0e0e0; color: black; font-weight: bold; border: 1px solid #999999; border-radius: 6px; padding: 5px 10px;"
        style_light_gray = btn_style
        style_dark_gray = btn_style
        group_title_style = "font-weight: bold; color: #555; font-size: 11px;"

        def create_group_layout(title, buttons):
            group_layout = QVBoxLayout()
            group_layout.setSpacing(2)
            
            lbl = QLabel(title.upper()) # Group name in capital letters
            lbl.setStyleSheet(group_title_style)
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            group_layout.addWidget(lbl)

            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(5) # Distance between buttons 5px
            for btn in buttons:
                btn_layout.addWidget(btn)
            group_layout.addLayout(btn_layout)
            return group_layout

        # === CREATING BUTTONS ===
        
        # Styling History Buttons (since they are created internally HistoryManager)
        self.history_manager.btn_undo.setStyleSheet(btn_style)
        self.history_manager.btn_redo.setStyleSheet(btn_style)

        # --- File buttons ---
        self.btn_open = QPushButton("Open")
        self.btn_open.setStyleSheet(style_light_gray)
        self.btn_open.clicked.connect(self.open_file)

        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet(style_light_gray)
        self.btn_save.clicked.connect(self.save_file)

        self.btn_close = QPushButton("Close")
        self.btn_close.setStyleSheet(style_light_gray)
        self.btn_close.clicked.connect(self.close_document)

        self.btn_export = QPushButton("Export")
        self.btn_export.setStyleSheet(style_light_gray)
        self.btn_export.clicked.connect(self.open_export_module)

        # --- Image V PDF ---
        self.btn_image_to_pdf = QPushButton("Image to PDF")
        self.btn_image_to_pdf.setStyleSheet(style_light_gray)
        self.btn_image_to_pdf.setToolTip(
            "Merge images into PDF and open it in LibrePage"
        )
        self.btn_image_to_pdf.clicked.connect(self.open_image_to_pdf)

        self.btn_print = QPushButton("Print")
        self.btn_print.setStyleSheet(style_light_gray)
        self.btn_print.clicked.connect(self.open_print_module)

        # --- Page Buttons ---
        self.btn_cut = QPushButton("Cut")
        self.btn_cut.setStyleSheet(style_dark_gray)
        self.btn_cut.clicked.connect(self.open_cutpage_module)

        self.btn_merge = QPushButton("Merge")
        self.btn_merge.setStyleSheet(style_dark_gray)
        self.btn_merge.clicked.connect(self.open_merge_module)

        self.btn_reverse = QPushButton("Reverse")
        self.btn_reverse.setStyleSheet(style_dark_gray)
        self.btn_reverse.clicked.connect(self.open_reverse_module)

        self.btn_cheredov = QPushButton("Alternation")
        self.btn_cheredov.setStyleSheet(style_dark_gray)
        self.btn_cheredov.clicked.connect(self.open_cheredov_module)

        self.btn_rotate = QPushButton("Rotate")
        self.btn_rotate.setStyleSheet(style_dark_gray)
        self.btn_rotate.clicked.connect(self.open_rotate_module)

        self.btn_move = QPushButton("Shift")
        self.btn_move.setStyleSheet(style_dark_gray)
        self.btn_move.clicked.connect(self.open_move_module)

        self.btn_crop = QPushButton("Crop")
        self.btn_crop.setStyleSheet(style_dark_gray)
        self.btn_crop.clicked.connect(self.open_crop_module)
        
        # New Fields button+
        self.btn_fields = QPushButton("Margins+")
        self.btn_fields.setStyleSheet(style_dark_gray)
        self.btn_fields.clicked.connect(self.open_fields_module)

        # --- Buttons Convert ---
        self.btn_convert_color = QPushButton("Colors")
        self.btn_convert_color.setStyleSheet(style_dark_gray)
        self.btn_convert_color.clicked.connect(self.open_convertcolor_module)

        self.btn_curves = QPushButton("Text to curves")
        self.btn_curves.setStyleSheet(style_dark_gray)
        self.btn_curves.clicked.connect(self.open_curves_module)

        # Forming 1-and row (File | Pages | Convert)
        file_group = create_group_layout("File", [
            self.history_manager.btn_undo, 
            self.history_manager.btn_redo, 
            self.btn_open, self.btn_save, self.btn_close, self.btn_export, self.btn_image_to_pdf, self.btn_print
        ])
        top_row1.addLayout(file_group)

        pages_group = create_group_layout("Pages", [
            self.btn_cut, self.btn_merge, self.btn_reverse, self.btn_cheredov, 
            self.btn_rotate, self.btn_move, self.btn_crop, self.btn_fields
        ])
        top_row1.addLayout(pages_group)

        convert_group = create_group_layout("Convert", [self.btn_convert_color, self.btn_curves])
        top_row1.addLayout(convert_group)
        top_row1.addStretch()

        # --- Buttons Layout ---
        self.btn_booklet = QPushButton("Booklet")
        self.btn_booklet.setStyleSheet(style_light_gray)
        self.btn_booklet.clicked.connect(self.open_booklet_module)

        self.btn_booklet2 = QPushButton("Booklet in 2 fold")
        self.btn_booklet2.setStyleSheet(style_light_gray)
        self.btn_booklet2.clicked.connect(self.open_booklet2_module)

        self.btn_spusk = QPushButton("Page Imposition")
        self.btn_spusk.setStyleSheet(style_light_gray)
        self.btn_spusk.clicked.connect(self.open_spusk_module)

        self.btn_multiply = QPushButton("Step and Repeat")
        self.btn_multiply.setStyleSheet(style_light_gray)
        self.btn_multiply.clicked.connect(self.open_multiply_module)

        self.btn_number = QPushButton("Page Numbering")
        self.btn_number.setStyleSheet(style_light_gray)
        self.btn_number.clicked.connect(self.open_number_module)

        self.btn_mask = QPushButton("Whiteout")
        self.btn_mask.setStyleSheet(style_light_gray)
        self.btn_mask.clicked.connect(self.open_mask_module)

        self.btn_bg = QPushButton("Page Background")
        self.btn_bg.setStyleSheet(style_light_gray)
        self.btn_bg.clicked.connect(self.open_background_module)

        # --- Button Size ---
        self.btn_resize = QPushButton("Sheet size")
        self.btn_resize.setStyleSheet(style_dark_gray)
        self.btn_resize.clicked.connect(self.open_size_module)

        self.btn_scale = QPushButton("Content Size")
        self.btn_scale.setStyleSheet(style_dark_gray)
        self.btn_scale.clicked.connect(self.open_scale_module)

        # --- Photo Buttons ---
        self.btn_select_image = QPushButton("🟦 ↗ Choose")
        self.btn_select_image.setStyleSheet(style_light_gray)
        self.btn_select_image.setCheckable(True)
        self.btn_select_image.clicked.connect(self.toggle_image_select_mode)

        self.btn_imageclone = QPushButton("Clone")
        self.btn_imageclone.setStyleSheet(style_light_gray)
        self.btn_imageclone.clicked.connect(self.open_imageclone_module)

        self.btn_photocorrection = QPushButton("Correction")
        self.btn_photocorrection.setStyleSheet(style_light_gray)
        self.btn_photocorrection.clicked.connect(self.open_photocorrection_module)

        self.btn_openeditphoto = QPushButton("Open in editor")
        self.btn_openeditphoto.setStyleSheet(style_light_gray)
        self.btn_openeditphoto.clicked.connect(self.open_edit_photo_module)

        # Forming 2-and row (Layout | Size | Photo)
        layout_group = create_group_layout("Layout", [
            self.btn_booklet, self.btn_booklet2, self.btn_spusk, self.btn_multiply, 
            self.btn_number, self.btn_mask, self.btn_bg
        ])
        top_row2.addLayout(layout_group)

        size_group = create_group_layout("Size", [self.btn_resize, self.btn_scale])
        top_row2.addLayout(size_group)

        photo_group = create_group_layout("Photo", [
            self.btn_select_image, self.btn_imageclone, 
            self.btn_photocorrection, self.btn_openeditphoto
        ])
        top_row2.addLayout(photo_group)
        top_row2.addStretch()

        # Assembling a panel with an indent instead of a separator
        top_bar_container.addLayout(top_row1)
        top_bar_container.addSpacing(10)
        top_bar_container.addLayout(top_row2)
        
        layout.addLayout(top_bar_container)

        # 2. Preview area
        middle_container = QWidget()
        middle_layout = QHBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        # Sidebar button (left)
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
        
        # Left thumbnail panel
        self.thumb_panel = QWidget()
        self.thumb_panel_layout = QVBoxLayout(self.thumb_panel)
        self.thumb_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb_panel_layout.setSpacing(0)
        
        self.btn_toggle_cols = QPushButton("Switch to 1 column")
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
        
        # Preview area
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #555;")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.update_page_info)
        
        # Set up an event filter to intercept the mouse wheel in single sheet mode
        self.scroll_area.viewport().installEventFilter(self)
        
        self.preview_container = QWidget()
        self.preview_layout = QGridLayout(self.preview_container)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll_area.setWidget(self.preview_container)
        
        self.splitter.addWidget(self.scroll_area)
        
        # Right file pane
        self.files_panel = FilesPanel(self)
        self.files_panel.hide() # Initially hidden
        self.splitter.addWidget(self.files_panel)
        
        self.splitter.setSizes([200, 800, 150])
        middle_layout.addWidget(self.splitter)

        # Sidebar button (right)
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

        # 3. Bottom panel
        bottom_bar = QHBoxLayout()
        
        # Scroll mode switches
        self.btn_scroll_cont = QPushButton("■ ■")
        self.btn_scroll_cont.setFixedSize(30, 25)
        self.btn_scroll_cont.setToolTip("Smooth scrolling")
        self.btn_scroll_cont.clicked.connect(lambda: self.set_scroll_mode('continuous'))
        
        self.btn_scroll_page = QPushButton("█")
        self.btn_scroll_page.setFixedSize(30, 25)
        self.btn_scroll_page.setToolTip("Page view (a new one appears immediately)")
        self.btn_scroll_page.clicked.connect(lambda: self.set_scroll_mode('page'))
        
        bottom_bar.addWidget(self.btn_scroll_cont)
        bottom_bar.addWidget(self.btn_scroll_page)
        
        bottom_bar.addSpacing(10) # Space between button groups
        
        # Ruler switches
        self.btn_rulers_on = QPushButton("📏 incl")
        self.btn_rulers_on.setFixedSize(50, 25)
        self.btn_rulers_on.setToolTip("Enable rulers")
        self.btn_rulers_on.clicked.connect(lambda: self.set_rulers_mode(True))
        
        self.btn_rulers_off = QPushButton("📏 Off")
        self.btn_rulers_off.setFixedSize(50, 25)
        self.btn_rulers_off.setToolTip("Turn off rulers")
        self.btn_rulers_off.clicked.connect(lambda: self.set_rulers_mode(False))
        
        bottom_bar.addWidget(self.btn_rulers_on)
        bottom_bar.addWidget(self.btn_rulers_off)
        
        bottom_bar.addSpacing(10)
        
        bottom_bar.addWidget(QLabel("Scale:"))
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.sliderReleased.connect(self.on_zoom_changed)
        bottom_bar.addWidget(self.zoom_slider)

        # Here is the information now (moved from the top panel)
        self.info_label = QLabel("Size: 0x0 mm | Sheets: 0")
        bottom_bar.addWidget(self.info_label)

        bottom_bar.addWidget(QLabel("p:"))
        self.page_input = QLineEdit("0")
        self.page_input.setFixedWidth(50)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999))
        self.page_input.returnPressed.connect(self.go_to_page)
        bottom_bar.addWidget(self.page_input)
        self.page_input.returnPressed.connect(self.go_to_page)
        bottom_bar.addWidget(self.page_input)
        
        # INSERT CREATE HEART BUTTON HERE (line ~472)
        self.btn_heart = QPushButton("❤")
        self.btn_heart.setFixedSize(30, 25)
        self.btn_heart.setStyleSheet("background-color: #e0e0e0; color: red; font-weight: bold; border-radius: 4px; border: 1px solid #aaa;")
        self.btn_heart.setToolTip("License Agreement")
        self.btn_heart.clicked.connect(self.show_license)
        bottom_bar.addWidget(self.btn_heart)
        
        
        # Initializing mode buttons
        self.btn_height = QPushButton("By height")
        self.btn_height.clicked.connect(lambda: self.fit_to_height(self.btn_height))
        
        self.btn_width = QPushButton("Width")
        self.btn_width.clicked.connect(lambda: self.fit_to_width(40, self.btn_width))
        
        self.btn_one = QPushButton("1 sheet")
        self.btn_one.clicked.connect(lambda: self.set_mode(1, 'height', self.btn_one))
        
        self.btn_two = QPushButton("2 sheet")
        self.btn_two.clicked.connect(lambda: self.set_mode(2, 'height', self.btn_two))
        
        self.btn_three = QPushButton("3 sheet")
        self.btn_three.clicked.connect(lambda: self.set_mode(3, 'width', self.btn_three))

        self.btn_seven = QPushButton("7 sheets")
        self.btn_seven.clicked.connect(lambda: self.set_mode(7, 'width', self.btn_seven, 150))
        
        self.mode_buttons = [self.btn_height, self.btn_width, self.btn_one, self.btn_two, self.btn_three, self.btn_seven]
        
        # Set the basic style for the buttons on the bottom panel
        inactive_style = "background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 4px; padding: 4px 8px;"
        for btn in self.mode_buttons:
            btn.setStyleSheet(inactive_style)
            bottom_bar.addWidget(btn)
        
        layout.addLayout(bottom_bar)
        
        # Setting the default scrolling mode
        self.scroll_mode = 'continuous'
        self.set_scroll_mode('continuous')
        
        # Set the default ruler mode
        self.set_rulers_mode(True)
# INSERT METHOD SHOW_LICENSE HERE (line ~526)
    def show_license(self):
        dialog = LicenseViewer(self)
        dialog.exec()

    def toggle_image_select_mode(self):
        """Enable/turning off photo selection mode"""

        # If PDF not yet open
        if self.doc is None:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            self.btn_select_image.setChecked(False)
            self.is_image_select_mode = False
            return

        self.is_image_select_mode = self.btn_select_image.isChecked()

        if self.is_image_select_mode:
            # Let's make the active state dark gray so that it stands out when pressed.
            self.btn_select_image.setStyleSheet(
                "background-color: #888888; color: white; font-weight: bold; border: 2px solid black; border-radius: 6px; padding: 3px 8px;"
            )
        else:
            # Returning the standard group color 5 (light gray)
            self.btn_select_image.setStyleSheet(
                "background-color: #e0e0e0; color: black; font-weight: bold; border-radius: 6px; padding: 5px 10px;"
            )
            self.image_selection_manager.clear_selection()
            self.render_pages()

    def get_ghostscript_path_local(self):
        """
        Searches for an executable file Ghostscript.
        Taking into account the new folder structure resources/ghostscript...
        """
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        candidates = []
        
        # New folder structure resources
        gs_root = os.path.join(base_dir, "resources", "ghostscript")
        
        # 1. If inside resources/ghostscript/ there is a folder with the version (For example, gs10.07.1)
        if os.path.exists(gs_root) and os.path.isdir(gs_root):
            for item in os.listdir(gs_root):
                sub_dir = os.path.join(gs_root, item)
                if os.path.isdir(sub_dir):
                    candidates.append(os.path.join(sub_dir, "bin", "gswin64c.exe"))
                    candidates.append(os.path.join(sub_dir, "bin", "gswin32c.exe"))

        # 2. If bin lies right inside resources/ghostscript/
        candidates.append(os.path.join(gs_root, "bin", "gswin64c.exe"))
        candidates.append(os.path.join(gs_root, "bin", "gswin32c.exe"))

        for path in candidates:
            if os.path.exists(path):
                return path
        
        return None

    def open_export_module(self):
        """Opening the export module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        dialog = ExportDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_export(settings)

    def apply_export(self, settings):
        """Logic for exporting pages to JPG or TIFF"""
        try:
            out_dir = QFileDialog.getExistingDirectory(self, "Select a folder to save the exported files")
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
            if mode == "All pages":
                pages_to_process = range(len(self.doc))
            elif mode == "Current page":
                current_idx = self.active_page_index if self.active_page_index != -1 else 0
                pages_to_process = [current_idx]
            elif mode == "Even pages":
                pages_to_process = [i for i in range(len(self.doc)) if (i + 1) % 2 == 0]
            elif mode == "Odd pages":
                pages_to_process = [i for i in range(len(self.doc)) if (i + 1) % 2 != 0]

            for i in pages_to_process:
                page = self.doc.load_page(i)
                pix = page.get_pixmap(colorspace=cs, dpi=300)
                out_path = os.path.join(out_dir, f"page_{i+1}.{fmt}")
                pix.save(out_path)

            QMessageBox.information(self, "Success", f"Successfully exported {len(pages_to_process)} pages in {out_dir}")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Export failed:\n{e}")

    def open_background_module(self):
        """Opening the background customizer"""
        if not self.doc:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Open first PDF file."))
            return
            
        dialog = BackgroundDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self.apply_background(settings)

    def open_background_module(self):
        """Opening the background customizer"""
        if not self.doc:
            QMessageBox.warning(self, self.tr("Attention"), self.tr("Open first PDF file."))
            return
            
        dialog = BackgroundDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self.apply_background(settings)

    def apply_background(self, settings):
        """Adding a background behind page elements"""
        try:
            mode = str(settings['range']).lower() if settings.get('range') else ""
            bg_type = settings['bg_type']

            new_doc = fitz.open()

            # If the background is from PDF, let's open it once
            bg_doc = None
            if bg_type == 'pdf':
                bg_doc = fitz.open(settings['file_path'])

            for i in range(len(self.doc)):
                apply = False
                if mode in ("all", "all pages", "все страницы"):
                    apply = True
                elif mode in ("current", "current page", "текущая страница") and i == self.active_page_index:
                    apply = True
                elif mode in ("even", "even pages", "четные страницы", "чётные страницы") and (i + 1) % 2 == 0:
                    apply = True
                elif mode in ("odd", "odd pages", "нечетные страницы", "нечётные страницы") and (i + 1) % 2 != 0:
                    apply = True

                old_page = self.doc.load_page(i)
                page_rect = old_page.rect

                # Create a new page of the same size
                new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)

                if apply:
                    # First we draw the background (it will be behind all the elements)
                    if bg_type == 'color':
                        # Fill the sheet with color without a stroke
                        new_page.draw_rect(new_page.rect, color=None, fill=settings['color_value'])
                    elif bg_type == 'jpg':
                        # We insert JPG with stretch (keep_proportion=False)
                        new_page.insert_image(new_page.rect, filename=settings['file_path'], keep_proportion=False)
                    elif bg_type == 'pdf' and bg_doc and len(bg_doc) > 0:
                        # We insert PDF with stretch
                        new_page.show_pdf_page(new_page.rect, bg_doc, 0, keep_proportion=False)

                # Then we overlay the contents of the original page
                new_page.show_pdf_page(new_page.rect, self.doc, i)

            if bg_doc:
                bg_doc.close()

            if self.doc:
                self.doc.close()

            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            QMessageBox.information(self, self.tr("Success"), self.tr("Background successfully applied."))

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to apply background')}:\n{e}")

    def open_convertcolor_module(self):
        """Opening the color conversion module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        dialog = ConvertColorDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_convertcolor(settings)

    def apply_convertcolor(self, settings):
        """Applying color conversion via Ghostscript (corrected version)"""
        try:
            mode = settings['range']
            target = settings['target']
            profile = settings.get('profile', '')

            # WE TAKE THE WAY TO GHOSTSCRIPT STRICTLY FROM DIALOG SETTINGS (CROSS-PLATFORM)
            gs_exec = settings.get('gs_path')

            # Fallback option in case the settings are empty
            if not gs_exec:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
                if platform.system() == "Windows":
                    gs_exec = os.path.join(bin_dir, "gswin64c.exe")
                else:
                    local_gs = os.path.join(bin_dir, "gs")
                    gs_exec = local_gs if os.path.exists(local_gs) else (shutil.which("gs") or "gs")

            # Checking the existence of the file (for absolute paths)
            if gs_exec and os.path.isabs(gs_exec) and not os.path.exists(gs_exec):
                if platform.system() != "Windows":
                    gs_exec = "gs"

            if not gs_exec:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Not found Ghostscript!"
                )
                return

            temp_in = os.path.join(tempfile.gettempdir(), "librepage_color_in.pdf")
            temp_out = os.path.join(tempfile.gettempdir(), "librepage_color_out.pdf")

            self.doc.save(temp_in)

            # Ghostscript 10.x requires correct model parameters.
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

            # ICC add a profile only if Ghostscript will be able to use it.
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
                # If the profile caused an error, repeat without ICC.
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

                if mode == "All pages":
                    apply = True
                elif mode == "Current page" and i == self.active_page_index:
                    apply = True
                elif mode == "Even pages" and (i + 1) % 2 == 0:
                    apply = True
                elif mode == "Odd pages" and (i + 1) % 2 != 0:
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
                "Success",
                "Color space successfully changed!"
            )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to apply color conversion:\n{e}"
            )

    def open_curves_module(self):
        """Opening the text to curves translation module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        dialog = CurvesDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_curves(settings)

    def apply_curves(self, settings):
        """Applying text to curves conversion using Ghostscript (sideways)"""
        try:
            mode = settings['range']
            custom_pages_str = settings.get('custom_pages', '')
            
            # WE TAKE THE WAY TO GHOSTSCRIPT STRICTLY FROM DIALOG SETTINGS (CROSS-PLATFORM)
            gs_exec = settings.get('gs_path')

            # Fallback option in case the settings are empty
            if not gs_exec:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
                if platform.system() == "Windows":
                    gs_exec = os.path.join(bin_dir, "gswin64c.exe")
                else:
                    local_gs = os.path.join(bin_dir, "gs")
                    gs_exec = local_gs if os.path.exists(local_gs) else (shutil.which("gs") or "gs")

            # Checking the existence of the file (for absolute paths)
            if gs_exec and os.path.isabs(gs_exec) and not os.path.exists(gs_exec):
                if platform.system() != "Windows":
                    gs_exec = "gs"

            if not gs_exec:
                QMessageBox.critical(self, "Error", "Not found Ghostscript!")
                return

            total_pages = len(self.doc)
            pages_to_process = []

            if mode == "All pages":
                pages_to_process = list(range(total_pages))
            elif mode == "Current page":
                current_idx = self.active_page_index if self.active_page_index != -1 else 0
                pages_to_process = [current_idx]
            elif mode == "Even pages":
                pages_to_process = [i for i in range(total_pages) if (i + 1) % 2 == 0]
            elif mode == "Odd pages":
                pages_to_process = [i for i in range(total_pages) if (i + 1) % 2 != 0]
            elif mode == "Specified pages":
                try:
                    for part in custom_pages_str.replace(" ", "").split(","):
                        if "-" in part:
                            start, end = map(int, part.split("-"))
                            pages_to_process.extend(range(start - 1, end))
                        else:
                            pages_to_process.append(int(part) - 1)
                    pages_to_process = [p for p in set(pages_to_process) if 0 <= p < total_pages]
                except ValueError:
                    QMessageBox.warning(self, "Error", "Incorrect format of the specified pages.")
                    return

            if not pages_to_process:
                QMessageBox.warning(self, "Attention", "No pages to process.")
                return

            new_doc = fitz.open()
            main_temp_dir = tempfile.mkdtemp(prefix="librepage_curves_")
            system_fonts = None

            # Processing sheets one at a time
            for i in range(total_pages):
                if i not in pages_to_process:
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                    continue
                
                # --- VISUALIZATION: "The sheets will run" ---
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

                # IDLE RUN (Dry Run): Looking for missing fonts
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
                
                # IF THE FONT IS NOT IN THE SYSTEM
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

                # FINAL PAGE CONVERSION
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
                    print(f"Error while converting page {i+1}: {e}")
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)

            # --- Completion ---
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc

            self.render_all()
            self.history_manager.save_state()

            shutil.rmtree(main_temp_dir, ignore_errors=True)
            QMessageBox.information(self, "Success", "Text converted to curves!")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to convert text to curves:\n{e}")

    def open_imageclone_module(self):
        """Opening the photo cloning module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        page_index = self.active_page_index if self.active_page_index != -1 else 0
        page = self.doc.load_page(page_index)
        
        # Let's increase it for better highlighting quality in the dialog.
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
                QMessageBox.warning(self, "Attention", "You have not selected the area for cloning.")

    # --- ADDED: PHOTO CORRECTION MODULE ---
    def open_photocorrection_module(self):
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        # Checking that the photo is selected
        if not self.image_selection_manager.selected_bbox:
            QMessageBox.warning(self, "Attention", "First select the photo with the 'Select' tool'.")
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

            # Getting a raster of the selected area
            pix = page.get_pixmap(clip=bbox, dpi=300)
            
            # Convert to PIL
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")

            # Applying the settings
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(settings['brightness'])
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(settings['contrast'])
            
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(settings['saturation'])

            # Save to a temporary buffer for pasting
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            
            # We insert it back into PDF
            # First we cover the area with white (similar to cloning)
            page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
            page.insert_image(bbox, stream=buf.getvalue())
            
            self.render_all()
            self.history_manager.save_state()
            QMessageBox.information(self, "Success", "Correction applied.")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to apply correction: {e}")
    # ----------------------------------------

    # --- ADDED: MODULE OPEN IN THE EDITOR ---
    def open_edit_photo_module(self):
        """Opening the selected photo in an external editor"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return

        if not self.image_selection_manager.selected_bbox:
            QMessageBox.warning(self, "Attention", "First select the photo with the 'Select' tool'.")
            return

        # CHANGE: Moved all fetch, run and wait logic to main.py
        # This ensures that the file is saved as .png (solves the problem with Photoshop)
        # And pause the code (solves the problem with GIMP/Krita, when no changes appeared)

        page_index = self.image_selection_manager.selected_page_index
        bbox = self.image_selection_manager.selected_bbox
        page = self.doc.load_page(page_index)

        try:
            # Extracting the raster
            pix = page.get_pixmap(clip=bbox, dpi=300)
            img_data = pix.tobytes("png")

            # Save to a temporary file with an explicit extension .png
            temp_file_path = os.path.join(tempfile.gettempdir(), "librepage_edit_photo.png")
            with open(temp_file_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract photo:\n{e}")
            return

        # We request the path to the editor if it is not already selected
        if not self.external_editor_path or not os.path.exists(self.external_editor_path):
            editor_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select editing program (Photoshop, GIMP, Krita...)",
                "",
                "Executable files (*.exe *.app *.sh *.bat);;All files (*.*)"
            )
            if not editor_path:
                return
            self.external_editor_path = editor_path

        # Open the editor
        try:
            safe_file_path = os.path.normpath(temp_file_path)
            safe_editor_path = os.path.normpath(self.external_editor_path)

            if platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", safe_editor_path, safe_file_path])
            else:
                subprocess.Popen([safe_editor_path, safe_file_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start editor:\n{e}")
            return

        # Important! Pausing execution to wait for the user to save the file
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Waiting for the editor")
        msg_box.setText("The image is opened in an external editor.\n\n1. Make changes in the editor that opens.\n2. Save the file (Overwrite the current file, do not select 'Save As'').\n3. Return to this program and click 'Apply Changes''.\n\nIf you want to choose a different editor in the future, just restart LibrePage.")
        btn_apply = msg_box.addButton("Apply changes", QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()

        if msg_box.clickedButton() == btn_apply:
            try:
                # Refresh the page. Paste over the white rectangle
                page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))
                page.insert_image(bbox, filename=temp_file_path)

                self.render_all()
                self.history_manager.save_state()
                QMessageBox.information(self, "Success", "Image updated successfully!")
            except Exception as e:
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to apply changes:\n{e}")
    # ----------------------------------------

    def apply_imageclone(self, rect_ratio, page_index):
        """Cloning logic: obtaining an area raster, white background on 0.5 mm more, raster insertion"""
        try:
            rx, ry, rw, rh = rect_ratio
            page = self.doc.load_page(page_index)
            
            # We get the coordinates of the current page in PDF
            pw = page.rect.width
            ph = page.rect.height
            
            x0 = page.rect.x0 + rx * pw
            y0 = page.rect.y0 + ry * ph
            x1 = x0 + rw * pw
            y1 = y0 + rh * ph
            
            target_rect = fitz.Rect(x0, y0, x1, y1)
            
            # We obtain a raster of the cloned area with good resolution (300 dpi)
            clip_pix = page.get_pixmap(clip=target_rect, dpi=300)
            
            # We are counting 0.5 mm in points to expand the white rectangle
            mm_to_pts = 72 / 25.4
            offset = 0.5 * mm_to_pts
            
            white_rect = fitz.Rect(x0 - offset, y0 - offset, x1 + offset, y1 + offset)
            
            # Overlay a white rectangle to hide the old photo and background
            page.draw_rect(white_rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Insert the cloned image on top of the white rectangle at the same coordinates
            page.insert_image(target_rect, pixmap=clip_pix)
            
            self.render_all()
            self.history_manager.save_state()
            
            QMessageBox.information(self, "Success", "Photo cloned successfully!")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to clone photo:\n{e}")

    def open_scale_module(self):
        """Opening the page content resizer module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return

        dialog = ScalePageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_scale(settings)

    def apply_scale(self, settings):
        """Page Content Scaling: Stretch Axis Independently"""
        try:
            # Converting percentages to coefficients
            gen = settings['general'] / 100.0
            h_sc = settings['horiz'] / 100.0
            v_sc = settings['vert'] / 100.0

            # Resulting scaling factors for each axis
            scale_x = gen * h_sc
            scale_y = gen * v_sc

            mode = settings.get('mode', '').strip()
            mode_lower = mode.lower()

            new_doc = fitz.open()

            for i in range(len(self.doc)):
                apply = False
                if mode_lower in ["all pages", "все страницы"]:
                    apply = True
                elif mode_lower in ["current page", "текущая страница"] and i == self.active_page_index:
                    apply = True
                elif mode_lower in ["even pages", "четные страницы"] and (i + 1) % 2 == 0:
                    apply = True
                elif mode_lower in ["odd pages", "нечетные страницы"] and (i + 1) % 2 != 0:
                    apply = True

                old_page = self.doc.load_page(i)
                page_rect = old_page.rect

                new_page = new_doc.new_page(
                    width=page_rect.width,
                    height=page_rect.height
                )

                if apply:
                    # We calculate content sizes independently for each axis
                    content_w = page_rect.width * scale_x
                    content_h = page_rect.height * scale_y

                    # Center the content: 
                    x = (page_rect.width - content_w) / 2
                    y = (page_rect.height - content_h) / 2

                    target_rect = fitz.Rect(
                        x,
                        y,
                        x + content_w,
                        y + content_h
                    )

                    # show_pdf_page with parameter keep_proportion=False allows
                    # stretch the content strictly into a given rectangle target_rect
                    new_page.show_pdf_page(
                        target_rect,
                        self.doc,
                        i,
                        keep_proportion=False 
                    )
                else:
                    # Normal copying without changes
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
                "Success",
                "Content scale changed (axial stretch)."
            )

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to scale content:\n{e}"
            )

    def open_spusk_module(self):
        """Opening the Imposition module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return

        dialog = SpuskDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings is not None:
                self.apply_spusk(settings)

    def apply_spusk(self, settings):
        """Formula processing logic (shuffle) And N-up placement"""
        try:
            mm_to_pts = 72 / 25.4
            target_w_pts = settings['target_w'] * mm_to_pts
            target_h_pts = settings['target_h'] * mm_to_pts
            cols = settings['cols']
            rows = settings['rows']
            group_size = settings['group_size']
            formula = settings['formula']

            if cols <= 0 or rows <= 0 or group_size <= 0:
                QMessageBox.warning(self, "Error", "Descent parameters must be greater than zero.")
                return

            # Stage 1: Parsing shuffle formula
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
                            rot = 270  # turn counterclockwise 90
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

            # Stage 2: Accommodation N-up on the new list
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
                        
                        # Method show_pdf_page supports rotation, 
                        # proportions (keep_proportion=True) are applied automatically
                        new_page.show_pdf_page(rect, self.doc, src_idx, rotate=item['rot'])

            # Replace the old document with a new one
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.active_page_index = 0
            self.render_all()
            self.history_manager.save_state()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Imposition failed:\n{e}")

    def open_crop_module(self):
        """Opening the crop module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
    
        try:
            dialog = CropPageDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_settings()
                mode = data['mode']
            
            # Конвертация миллиметров в пункты (1 мм = 72 / 25.4 pt)
            mm_to_pt = 72.0 / 25.4
            top_pt = data['top'] * mm_to_pt
            bottom_pt = data['bottom'] * mm_to_pt
            left_pt = data['left'] * mm_to_pt
            right_pt = data['right'] * mm_to_pt
            
            total_pages = len(self.doc)
            target_pages = []
            
            # Определение номеров страниц для обработки
            if mode in ["All Pages", "Все страницы"]:
                target_pages = list(range(total_pages))
            elif mode in ["Even Pages", "Четные страницы"]:
                target_pages = [i for i in range(total_pages) if (i + 1) % 2 == 0]
            elif mode in ["Odd Pages", "Нечетные страницы"]:
                target_pages = [i for i in range(total_pages) if (i + 1) % 2 != 0]
            elif mode in ["Current Page", "Текущая страница"]:
                current_idx = getattr(self, 'current_page', 0)
                target_pages = [current_idx]
            
            # Применение кадрирования (cropbox) к страницам PyMuPDF
            for page_num in target_pages:
                if 0 <= page_num < total_pages:
                    page = self.doc[page_num]
                    # Берем mediabox как базовый размер оригинальной страницы
                    base_rect = page.mediabox
                    
                    new_x0 = base_rect.x0 + left_pt
                    new_y0 = base_rect.y0 + top_pt
                    new_x1 = base_rect.x1 - right_pt
                    new_y1 = base_rect.y1 - bottom_pt
                    
                    # Проверка валидности полученных прямоугольных координат
                    if new_x1 > new_x0 and new_y1 > new_y0:
                        new_cropbox = fitz.Rect(new_x0, new_y0, new_x1, new_y1)
                        page.set_cropbox(new_cropbox)
            
            # Принудительное обновление отображения страниц в UI LibrePage
            if hasattr(self, 'update_preview'):
                self.update_preview()
            elif hasattr(self, 'render_pages'):
                self.render_pages()
            elif hasattr(self, 'render_page'):
                self.render_page()
            elif hasattr(self, 'show_page'):
                self.show_page()
            elif hasattr(self, 'reload_pdf'):
                self.reload_pdf()
            elif hasattr(self, 'display_pages'):
                self.display_pages()
            else:
                QMessageBox.information(self, "Info", "Обрезка применена к документу, но метод перерисовки предпросмотра не найден.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ошибка при обрезке: {str(e)}")
            
    def open_fields_module(self):
        """Opening the add fields module (fields+)"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        dialog = FieldsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_fields(settings)

    def apply_fields(self, settings):
        """Logic for adding fields around the page"""
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
                if mode == "All pages": should_apply = True
                elif mode == "Even pages" and (i + 1) % 2 == 0: should_apply = True
                elif mode == "Odd pages" and (i + 1) % 2 != 0: should_apply = True
                elif mode == "Current page" and i == self.active_page_index: should_apply = True
                
                old_page = self.doc.load_page(i)
                old_rect = old_page.rect
                
                if should_apply:
                    # New sheet size = old size + required fields
                    new_w = old_rect.width + left_pts + right_pts
                    new_h = old_rect.height + top_pts + bottom_pts
                    
                    new_page = new_doc.new_page(width=new_w, height=new_h)
                    
                    # Rectangle for inserting the old page, offset by the size of the left and top margins
                    target_rect = fitz.Rect(left_pts, top_pts, left_pts + old_rect.width, top_pts + old_rect.height)
                    
                    # Paste the contents of the old page
                    new_page.show_pdf_page(target_rect, self.doc, i)
                else:
                    # Just copy the page without changes
                    new_page = new_doc.new_page(width=old_rect.width, height=old_rect.height)
                    new_page.show_pdf_page(new_page.rect, self.doc, i)
                    
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            
            self.render_all()
            self.history_manager.save_state()
            QMessageBox.information(self, "Success", "Fields added successfully.")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to add fields:\n{e}")

    def apply_crop(self, settings):
        """Applying cropping to pages"""
        try:
            mm_to_pts = 72 / 25.4
            top_pts = settings['top'] * mm_to_pts
            bottom_pts = settings['bottom'] * mm_to_pts
            left_pts = settings['left'] * mm_to_pts
            right_pts = settings['right'] * mm_to_pts
            
            mode = settings['mode']
            
            for i in range(len(self.doc)):
                should_apply = False
                if mode == "All pages": should_apply = True
                elif mode == "Even pages" and (i + 1) % 2 == 0: should_apply = True
                elif mode == "Odd pages" and (i + 1) % 2 != 0: should_apply = True
                elif mode == "Current page" and i == self.active_page_index: should_apply = True
                
                if should_apply:
                    page = self.doc.load_page(i)
                    rect = page.rect
                    # Reducing the page size (shift the coordinates of the rectangle inward)
                    new_rect = fitz.Rect(rect.x0 + left_pts, rect.y0 + top_pts, 
                                           rect.x1 - right_pts, rect.y1 - bottom_pts)
                    
                    if new_rect.width > 0 and new_rect.height > 0:
                        page.set_cropbox(new_rect)
                        page.set_mediabox(new_rect)
                    else:
                        QMessageBox.warning(self, "Error", f"Incorrect values ​​for page cropping {i+1} (cut larger than the sheet itself).")
                        return
            
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to trim pages:\n{e}")

    def open_size_module(self):
        """Opening the resize module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        dialog = SizePageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_resize(settings)

    def apply_resize(self, settings):
        """Scales document pages to a new size"""
        try:
            mm_to_pts = 72 / 25.4
            new_w = settings['w_mm'] * mm_to_pts
            new_h = settings['h_mm'] * mm_to_pts
            
            new_doc = fitz.open()
            pages_to_process = range(len(self.doc)) if settings['all'] else [self.active_page_index]
            
            for i in range(len(self.doc)):
                if i in pages_to_process:
                    old_p = self.doc.load_page(i)
                    new_p = new_doc.new_page(width=new_w, height=new_h)
                    
                    # We scale content through rectangle
                    new_p.show_pdf_page(new_p.rect, self.doc, i)
                else:
                    new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
            
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.render_all()
            self.history_manager.save_state()
            QMessageBox.information(self, "Success", "Pages resized.")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to resize:\n{e}")

    def open_print_module(self):
        """Launching the print module and saving current changes"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        # 1. Save the temporary file to the system folder temp
        temp_dir = tempfile.gettempdir()
        temp_print_path = os.path.join(temp_dir, "temp_print_job.pdf")
        
        try:
            self.doc.save(temp_print_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare file for printing: {e}")
            return
            
        # 2. We call printing directly through the imported module
        try:
            page_to_print = self.active_page_index if self.active_page_index != -1 else 0
            
            # Importing the print module
            import print as print_module
            
            # Calling the print function from the module print.py
            # We pass the path to the temporary PDF and page number (1-based)
            print_module.start_print(temp_print_path, page_to_print + 1)

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Print Error", 
                f"Failed to call print module:\n{e}\n\n{traceback.format_exc()}"
            )

    def open_multiply_module(self):
        """Opening the page propagation module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        dialog = MultiplyDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_multiply(settings)

    def apply_multiply(self, settings):
        """Logic for placing copies of original pages on a new canvas"""
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
                QMessageBox.warning(self, "Error", "The sheet dimensions are set incorrectly.")
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

                # --- STAGE 1: We post all pages ---
                for r in range(rows):
                    for c in range(cols):
                        x0 = start_x + c * (orig_w + spacing_pts)
                        y0 = start_y + r * (orig_h + spacing_pts)
                        rect = fitz.Rect(x0, y0, x0 + orig_w, y0 + orig_h)
                        new_page.show_pdf_page(rect, self.doc, i)

                # --- STAGE 2: Draw all the cut marks ---
                if crop_marks:
                    # Set label parameters
                    mark_len = 3 * mm_to_pts
                    gap_pts = 1 * mm_to_pts  # Clearance 1 mm so that it does not reach the corner
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

                            # Upper left corner
                            # Shift to gap_pts from the corner (cut_x0, cut_y0)
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

                            # Upper right corner
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

                            # Bottom left corner
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

                            # Bottom right corner
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
            QMessageBox.critical(self, "Error", f"Failed to reproduce pages:\n{e}")

    def open_mask_module(self):
        """Opening the hiding module (rectangle overlay)"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
            
        page_index = self.active_page_index if self.active_page_index != -1 else 0
        page = self.doc.load_page(page_index)
        
        zoom = 1.0 # Basic scale for the docker
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        
        dialog = MaskPageDialog(pixmap, self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings['rect_ratio']:
                self.apply_mask(settings)
            else:
                QMessageBox.warning(self, "Attention", "You have not selected the area to hide.")

    def apply_mask(self, settings):
        """Applies a white rectangle to selected pages"""
        ratio_x, ratio_y, ratio_w, ratio_h = settings['rect_ratio']
        mode = settings['mode']
        
        pages_to_process = []
        if mode == "Hide on current page":
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
        """Opening the page shifter"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        dialog = MovePageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_move(settings)

    def apply_move(self, settings):
        """Applying shift to pages"""
        mm_to_pts = 72 / 25.4
        dx = settings['dx'] * mm_to_pts
        dy = settings['dy'] * mm_to_pts
        
        mode = settings['mode']
        
        for i in range(len(self.doc)):
            should_apply = False
            if mode == "All pages": should_apply = True
            elif mode == "Even pages" and (i + 1) % 2 == 0: should_apply = True
            elif mode == "Odd pages" and (i + 1) % 2 != 0: should_apply = True
            elif mode == "Current page" and i == self.active_page_index: should_apply = True
            
            if should_apply:
                page = self.doc.load_page(i)
                page.set_mediabox(fitz.Rect(page.rect.x0 - dx, page.rect.y0 - dy, 
                                            page.rect.x1 - dx, page.rect.y1 - dy))
        
        self.render_all()
        self.history_manager.save_state()

    def open_cutpage_module(self):
        """Opening the cutting module"""
        if not self.current_file_path:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        dialog = CutPageDialog(self.current_file_path, self)
        dialog.exec()

    def open_merge_module(self):
        """Opening the splicing module"""
        merged_file_path = merge_pdfs_dialog(self)
        if merged_file_path:
            self.load_document(merged_file_path)

    def open_reverse_module(self):
        """Opening the page reverse module"""
        reverse_pages_action(self)

    def open_cheredov_module(self):
        """Opening the Interleave Module"""
        cheredov_pages_action(self)

    def open_rotate_module(self):
        """Opening the page turner module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        dialog = RotatePageDialog(self)
        dialog.exec()

    def open_number_module(self):
        """Opening the pagination module"""
        if not self.current_file_path:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        dialog = NumberPageDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_numeration(settings)

    def apply_numeration(self, settings):
        """Applying page numbering PDF"""
        try:
            mm_to_pts = 72 / 25.4
            
            for i in range(len(self.doc)):
                page = self.doc.load_page(i)
                page_w = page.rect.width
                page_h = page.rect.height
                
                x_pts = settings['offset_x'] * mm_to_pts
                y_pts = settings['offset_y'] * mm_to_pts
                
                if settings['position'] == 'From below':
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
            QMessageBox.critical(self, "Error", f"Failed to add numbering:\n{e}")

    def load_document(self, file_name):
        """Generalized loading function PDF-the document in an interface"""
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
        """Multibooklet: breakdown into notebooks (signatures)"""
        # FIXED: Now we use self.doc, instead of opening the file again
        if not self.doc:
            QMessageBox.critical(self, "Error", "No document open.")
            return

        try:
            # Working with the current object self.doc
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
                    # Front side of the sheet
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
                    
                    # Reverse side of the sheet
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
            
            # Close the old one and insert the new one
            if self.doc: self.doc.close()
            self.doc = new_doc
            self.open_docs[self.current_file_path] = self.doc
            self.active_page_index = 0
            self.render_all()
            self.history_manager.save_state()
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to create booklet:\n{e}")

    def open_booklet_module(self):
        """Opening the booklet module"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        dialog = BookletDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_booklet(settings)

    # --- ADDED: MODULE BOOKLET B 2 FOLD ---
    def open_booklet2_module(self):
        """Opening the booklet module in 2 fold"""
        if not self.doc:
            QMessageBox.warning(self, "Attention", "Open first PDF file.")
            return
        
        dialog = Booklet2Dialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            if settings:
                self.apply_booklet2(settings)

    def apply_booklet2(self, settings):
        """Creating a booklet in 2 fold (by 3 pages per sheet)"""
        if not self.doc:
            return

        try:
            N = len(self.doc)
            page_w = self.doc.load_page(0).rect.width
            page_h = self.doc.load_page(0).rect.height
            
            mm_to_pts = 72 / 25.4
            inner_pts = settings['inner_offset'] * mm_to_pts
            outer_pts = settings['outer_offset'] * mm_to_pts
            # The final shift of the outer sheets
            shift_pts = inner_pts - outer_pts
            
            # Translate from 1-based V 0-based indexes for array
            front_order = [x - 1 for x in settings['front']] 
            back_order = [x - 1 for x in settings['back']]   
            
            new_doc = fitz.open()
            
            # We process the document in blocks of 6 pages
            for i in range(0, N, 6):
                # We collect the indices of the current block, replacing the missing ones with -1
                chunk = []
                for j in range(6):
                    chunk.append(i + j if i + j < N else -1)
                
                # --- Face (width 3 pages) ---
                page_f = new_doc.new_page(width=page_w * 3, height=page_h)
                
                # Left panel (shifts to the right when positive shift)
                p_idx = front_order[0]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_f.show_pdf_page(rect, self.doc, chunk[p_idx])
                    
                # Right panel (shifts to the left when positive shift)
                # Draw the right and left BEFORE the center, 
                # so that with a strong displacement the central (motionless) the page hid the excess
                p_idx = front_order[2]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w * 2 - shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_f.show_pdf_page(rect, self.doc, chunk[p_idx])

                # Central panel (ALWAYS stays still - no offset applied)
                p_idx = front_order[1]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_f.show_pdf_page(rect, self.doc, chunk[p_idx])
                
                # --- Reverse side ---
                page_b = new_doc.new_page(width=page_w * 3, height=page_h)
                
                # Left panel
                p_idx = back_order[0]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_b.show_pdf_page(rect, self.doc, chunk[p_idx])
                    
                # Right panel
                p_idx = back_order[2]
                if 0 <= p_idx < 6 and chunk[p_idx] != -1:
                    x0 = page_w * 2 - shift_pts
                    rect = fitz.Rect(x0, 0, x0 + page_w, page_h)
                    page_b.show_pdf_page(rect, self.doc, chunk[p_idx])

                # Central panel (ALWAYS stands still)
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
            QMessageBox.critical(self, "Error", f"Failed to create booklet in 2 fold:\n{e}")
    # ----------------------------------------

    def switch_active_doc(self, file_path):
        """Switch to another open document"""
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
        """Closes a specific document"""
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
        """Closes the currently active document."""

        # Normal saved document
        if self.current_file_path:
            self.close_specific_document(self.current_file_path)
            return

        # Document from ImageToPDF, which has not yet been saved
        if self.doc is not None:
            try:
                self.doc.close()
            except Exception:
                pass

            self.clear_interface()

    def clear_interface(self):
        """Complete clearing of the interface if there are no documents"""
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
        self.info_label.setText("Size: 0x0 mm | Sheets: 0")
        self.page_input.setText("0")

    def save_file(self):
        """Saves the current PDF.
        
        If the document has already been opened from a file and is saved under the same name,
        first a temporary one is created PDF, and then it replaces the original.
        """

        if not self.doc:
            QMessageBox.warning(
                self,
                "Attention",
                "No document open to save."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF",
            self.current_file_path if self.current_file_path else "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Add .pdf, if the user did not write it
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        try:
            import os
            import tempfile

            old_path = self.current_file_path

            # -------------------------------------------------
            # CASE 1:
            # save over an already open file
            # -------------------------------------------------
            if old_path and os.path.abspath(file_path) == os.path.abspath(old_path):

                directory = os.path.dirname(os.path.abspath(file_path))

                fd, temp_path = tempfile.mkstemp(
                    suffix=".pdf",
                    dir=directory
                )
                os.close(fd)

                try:
                    # First we save it to a temporary file
                    self.doc.save(
                        temp_path,
                        garbage=4,
                        deflate=True
                    )

                    # Close the current object to free the old file
                    # before replacement
                    old_doc = self.doc

                    # Deleting the old entry from open_docs
                    if old_path in self.open_docs:
                        del self.open_docs[old_path]

                    try:
                        old_doc.close()
                    except Exception:
                        pass

                    # Replace the old one PDF new
                    os.replace(temp_path, file_path)

                    # Opening an already saved one PDF again
                    new_doc = fitz.open(file_path)

                    self.doc = new_doc
                    self.current_file_path = file_path
                    self.open_docs[file_path] = new_doc

                finally:
                    # If the temporary file remains after an error
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

            # -------------------------------------------------
            # CASE 2:
            # save under a new name
            # -------------------------------------------------
            else:

                # If such a name already exists, delete the old one
                # temporary version before recording
                if os.path.exists(file_path):
                    os.remove(file_path)

                # Save the current document
                self.doc.save(
                    file_path,
                    garbage=4,
                    deflate=True
                )

                # If the old document was opened under a different path,
                # delete old connection
                if old_path and old_path != file_path:
                    if old_path in self.open_docs:
                        del self.open_docs[old_path]

                # Registering a new path
                self.current_file_path = file_path
                self.open_docs[file_path] = self.doc

            # Updating the document panel
            self.files_panel.refresh(self.open_docs)

            # Updating information
            self.update_page_info()

            QMessageBox.information(
                self,
                "Success",
                f"File saved successfully:\n{file_path}"
            )

        except Exception as e:
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Save error",
                f"Failed to save PDF:\n\n{e}"
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
        """Duplicating a page"""
        if not self.doc:
            return

        try:
            page_count_before = len(self.doc)

            # Create a copy of the page at the end of the document
            self.doc.fullcopy_page(page_index)

            # New page index
            new_index = page_count_before

            # Move the copy immediately after the original
            self.doc.move_page(new_index, page_index + 1)

            self.active_page_index = page_index + 1

            self.render_all()
            self.history_manager.save_state()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to duplicate page:\n{e}"
            )

    def move_page(self, source_idx, target_idx):
        if not self.doc or source_idx == target_idx: return
        
        # FIX: Feature workaround PyMuPDF. At shift of 1 step down (idx -> idx+1), 
        # The library does nothing due to the index shift. The solution is to move the bottom sheet up.
        if target_idx == source_idx + 1:
            self.doc.move_page(target_idx, source_idx)
        else:
            self.doc.move_page(source_idx, target_idx)
            
        self.active_page_index = target_idx
        self.render_all()
        self.history_manager.save_state()

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

    def eventFilter(self, obj, event):
        if obj == self.scroll_area.viewport() and event.type() == QEvent.Type.Wheel:
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
        # 1. Page selection logic
        self.active_page_index = page_index
        self.page_input.setText(str(page_index + 1))
        
        for widget in self.page_widgets:
            widget.set_active(widget.page_index == self.active_page_index)
            
        for thumb in self.thumb_widgets:
            thumb.set_active(thumb.page_index == self.active_page_index)

        # 2. Logic for selecting an image if the mode is enabled
        if self.is_image_select_mode and pos_x is not None and pos_y is not None:
            # Converting from screen pixels to PDF points
            zoom_factor = self.current_zoom / 100.0
            pdf_x = pos_x / zoom_factor
            pdf_y = pos_y / zoom_factor
            
            page = self.doc.load_page(page_index)
            # Trying to select a photo by coordinates
            self.image_selection_manager.select_image_at(page, page_index, pdf_x, pdf_y)
            # Redraw the pages to update the blue highlight border
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
            self.btn_toggle_cols.setText("Switch to 2 speakers")
        else:
            self.thumb_columns = 2
            self.btn_toggle_cols.setText("Switch to 1 column")
        self.render_thumbnails()

    def thumbnail_clicked(self, page_index):
        self.handle_page_click(page_index)
        row = page_index // self.pages_in_row
        col = page_index % self.pages_in_row
        item = self.preview_layout.itemAtPosition(row, col)
        if item and item.widget():
            self.scroll_area.ensureWidgetVisible(item.widget(), 10, 10)

    def set_mode(self, count, fit_method='width', sender_btn=None, margin=40):
        self.pages_in_row = count
        if sender_btn: self.update_button_styles(sender_btn)
        if fit_method == 'width':
            self.fit_to_width(margin, sender_btn)
        else:
            self.fit_to_height(sender_btn)
            
        show_rulers_flag = (self.pages_in_row == 1) and self.rulers_enabled
        for widget in self.page_widgets:
            widget.show_rulers = show_rulers_flag
            widget.update_style()

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
        w, h = self.get_page_size_mm(self.doc.load_page(0))
        # Updated text (without p)
        self.info_label.setText(f"Size: {w:.1f}x{h:.1f} mm | Sheets: {total_pages}")
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

    def on_zoom_changed(self):
        self.current_zoom = self.zoom_slider.value()
        if self.doc: self.render_pages()

    def fit_to_height(self, sender_btn=None):
        if not self.doc: return
        if sender_btn: self.update_button_styles(sender_btn)
        page_h = self.doc.load_page(0).rect.height
        view_h = self.scroll_area.viewport().height()
        
        if self.pages_in_row == 1 and self.rulers_enabled:
            view_h -= 40
            
        self.current_zoom = int((view_h / page_h) * 100)
        if self.current_zoom < 10: self.current_zoom = 10 
            
        self.zoom_slider.setValue(self.current_zoom)
        self.render_pages()
        self.center_page_in_view()

    def fit_to_width(self, margin=40, sender_btn=None):
        if not self.doc: return
        if sender_btn: self.update_button_styles(sender_btn)
        page_w = self.doc.load_page(0).rect.width
        view_w = (self.scroll_area.viewport().width() - margin) / self.pages_in_row
        
        if self.pages_in_row == 1 and self.rulers_enabled:
            view_w -= 40
            
        self.current_zoom = int((view_w / page_w) * 100)
        if self.current_zoom < 10: self.current_zoom = 10
            
        self.zoom_slider.setValue(self.current_zoom)
        self.render_pages()
        self.center_page_in_view()

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file_name:
            self.load_document(file_name)

    def open_image_to_pdf(self):
        """Opens the module Image V PDF."""

        dialog = ImageToPdfDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.created_doc is not None:
                self.open_created_pdf(dialog.created_doc)

    def open_created_pdf(self, new_doc):
        """Opens PDF, created by module Image V PDF."""

        try:
            # If an old document was opened without saved changes —
            # just leave it in the list of open documents.
            if self.doc is not None and self.current_file_path:
                self.open_docs[self.current_file_path] = self.doc

            # The new document becomes active
            self.doc = new_doc

            # It's not saved yet
            self.current_file_path = None

            # First page
            self.active_page_index = 0

            # Resetting history
            self.history_manager.history = [self.doc.write()]
            self.history_manager.index = 0

            # Updating the display
            self.fit_to_height()
            self.render_thumbnails()
            self.update_page_info()

            self.page_input.setText("1")

            # Updating the list of documents
            self.files_panel.refresh(self.open_docs)

            self.update()

        except Exception as e:
            traceback.print_exc()

            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open created PDF:\n\n{e}"
        
            )

    def render_thumbnails(self):
        if not self.doc: return
        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            if item and item.widget(): item.widget().deleteLater()
            
        self.thumb_widgets = []
        zoom_factor = 0.12 if self.thumb_columns == 2 else 0.25
        
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            
            pixmap = QPixmap.fromImage(img)
            pixmap = add_number_to_pixmap(pixmap, page_num + 1)
            
            container = QWidget()
            v_layout = QVBoxLayout(container)
            
            label = ClickableThumbnail(page_num, self.thumbnail_clicked, self.mouse_handler)
            label.setPixmap(pixmap)
            
            if page_num == self.active_page_index:
                label.set_active(True)
                
            self.thumb_widgets.append(label)
            
            v_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
            self.thumb_layout.addWidget(container, page_num // self.thumb_columns, page_num % self.thumb_columns)

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
            
            # Added new arguments zoom_factor And image_selection_manager
            label = PageWidget(QPixmap.fromImage(img), page_num, self.handle_page_click, pixels_per_mm, show_rulers_flag, w_mm, h_mm, zoom_factor, self.image_selection_manager)
            
            if page_num == self.active_page_index:
                label.set_active(True)
            
            self.preview_layout.addWidget(label, page_num // self.pages_in_row, page_num % self.pages_in_row)
            self.page_widgets.append(label)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # We determine the path to the image in the same folder as main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    splash_image_path = os.path.join(base_dir, "logostart.png")
    
    # Uploading a picture
    if os.path.exists(splash_image_path):
        splash_pixmap = QPixmap(splash_image_path)
        # Create a splash window without borders and always on top of other windows
        splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        # Required flag to support transparency (alpha channel) pictures
        splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        splash.show()
        # Rendering the splash screen before starting other calculations
        app.processEvents()
    else:
        splash = None
    
    # Initializing the main window (but we don't show it yet)
    window = BaseImposingModule("LibrePageKST v.0.1")
    
    # Function to hide the splash screen and show the main window
    def show_main_window():
        if splash: splash.finish(window) # Give focus to the main window
        window.show()
        
    # Running the function show_main_window exactly in 4 seconds (4000 ms)
    QTimer.singleShot(4000, show_main_window)
    
    sys.exit(app.exec())