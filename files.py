import os
import fitz
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QGridLayout, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImage, QPixmap

class FileItem(QWidget):
    def __init__(self, file_path, doc, callback, close_callback):
        super().__init__()
        self.file_path = file_path
        self.callback = callback
        self.close_callback = close_callback
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)
        
        # Container for the icon and close button
        img_container = QWidget()
        img_layout = QGridLayout(img_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        
        # We get a preview 1-th page
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        
        self.lbl_img = QLabel()
        self.lbl_img.setPixmap(QPixmap.fromImage(img))
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img.setStyleSheet("border: 1px solid #555; background: #111;")
        self.lbl_img.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Close button (cross)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setStyleSheet("background-color: #cc0000; color: white; font-weight: bold; border-radius: 10px; border: none;")
        self.btn_close.clicked.connect(lambda: self.close_callback(self.file_path))
        
        img_layout.addWidget(self.lbl_img, 0, 0)
        img_layout.addWidget(self.btn_close, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        # File name
        filename = os.path.basename(file_path)
        lbl_name = QLabel(filename)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_name.setStyleSheet("color: white; font-size: 9px; padding: 2px;")
        lbl_name.setWordWrap(True)
        lbl_name.setMaximumWidth(120)
        
        main_layout.addWidget(img_container)
        main_layout.addWidget(lbl_name)

    def mousePressEvent(self, event):
        self.callback(self.file_path)

class FilesPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setFixedWidth(150)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #333; border: none;")
        
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll.setWidget(self.container)
        
        lbl_title = QLabel("Open files")
        lbl_title.setStyleSheet("color: #aaa; font-weight: bold; padding: 5px; background: #222;")
        layout.addWidget(lbl_title)
        layout.addWidget(self.scroll)

    def refresh(self, open_files_dict):
        # Cleaning
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        row = 0
        for path, doc in open_files_dict.items():
            widget = FileItem(path, doc, self.main_window.switch_active_doc, self.main_window.close_specific_document)
            self.grid.addWidget(widget, row, 0)
            row += 1