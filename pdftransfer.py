import os
import traceback
import fitz

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QWidget,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QPoint, QMimeData
from PyQt6.QtGui import QImage, QPixmap, QDrag


PDFTRANSFER_MIME = "application/x-librepage-pdf-page"


class TransferThumbnail(QLabel):
    """Эскиз страницы внешнего PDF с выделением и Drag & Drop."""

    def __init__(self, page_index, pixmap, owner):
        super().__init__()
        self.page_index = page_index
        self.owner = owner
        self.drag_start_pos = QPoint()
        self.setPixmap(pixmap)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._apply_selection_style()

    def _apply_selection_style(self):
        if self.page_index in self.owner.selected_pages:
            self.setStyleSheet(
                "QLabel { background-color: #cfe8ff; "
                "border: 3px solid #0078d7; padding: 1px; }"
            )
        else:
            self.setStyleSheet(
                "QLabel { background-color: #eeeeee; "
                "border: 1px solid #777777; padding: 3px; }"
                "QLabel:hover { border: 2px solid #0078d7; "
                "background-color: #f7f7f7; }"
            )

    def set_selected(self, selected):
        self._apply_selection_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.owner.select_page_range(self.page_index)
                event.accept()
                return

            if self.page_index in self.owner.selected_pages:
                self.owner.set_selection_anchor(self.page_index)
            else:
                self.owner.select_single_page(self.page_index)

            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < 8:
            return

        selected = sorted(self.owner.selected_pages)
        if self.page_index not in selected:
            selected = [self.page_index]

        drag = QDrag(self)
        mime = QMimeData()
        payload = f"{self.owner.file_path}\n" + ",".join(map(str, selected))
        mime.setData(PDFTRANSFER_MIME, payload.encode("utf-8"))
        drag.setMimeData(mime)

        pixmap = self.pixmap()
        if pixmap and not pixmap.isNull():
            drag_pix = pixmap.scaledToWidth(
                min(140, pixmap.width()),
                Qt.TransformationMode.SmoothTransformation
            )
            drag.setPixmap(drag_pix)
            drag.setHotSpot(
                QPoint(drag_pix.width() // 2, drag_pix.height() // 2)
            )

        self.setCursor(Qt.CursorShape.OpenHandCursor)
        drag.exec(Qt.DropAction.CopyAction)


class PDFTransferDialog(QDialog):
    """
    Окно «Обмен страницами».

    Здесь открывается отдельный PDF только для просмотра.
    Страница никогда не удаляется из этого PDF при перетаскивании:
    в основной документ она именно КОПИРУЕТСЯ.
    """

    THUMB_WIDTH = 150
    THUMB_HEIGHT = 210
    RENDER_ZOOM = 2.0

    def __init__(self, parent, file_path):
        super().__init__(parent)

        self.parent_window = parent
        self.file_path = os.path.abspath(file_path)
        self.source_doc = None
        self.thumbnails = []
        self.selected_pages = set()
        self.selection_anchor = None

        self.setWindowTitle(f"Обмен страницами — {os.path.basename(file_path)}")
        self.resize(430, 760)
        self.setMinimumSize(320, 420)

        self._build_ui()
        self._open_source_pdf()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        top_layout = QHBoxLayout()

        title = QLabel("Страницы PDF для копирования")
        title.setStyleSheet(
            "font-weight: bold; color: #444; padding: 3px;"
        )
        top_layout.addWidget(title)
        top_layout.addStretch()

        close_button = QPushButton("Закрыть")
        close_button.setFixedWidth(85)
        close_button.clicked.connect(self.close)
        top_layout.addWidget(close_button)

        main_layout.addLayout(top_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #555555; border: 1px solid #333333; }"
        )

        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(12)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)

        self.status_label = QLabel("Всего страниц: 0")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "font-weight: bold; color: #444; padding: 5px;"
        )
        main_layout.addWidget(self.status_label)

        selection_layout = QHBoxLayout()

        self.clear_selection_button = QPushButton("Снять выделение")
        self.clear_selection_button.clicked.connect(self.clear_selection)
        selection_layout.addWidget(self.clear_selection_button)

        self.selected_info_label = QLabel("Выбрано: 0")
        self.selected_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        selection_layout.addWidget(self.selected_info_label)

        main_layout.addLayout(selection_layout)

    def _open_source_pdf(self):
        try:
            self.source_doc = fitz.open(self.file_path)

            if self.source_doc.is_closed or len(self.source_doc) == 0:
                raise RuntimeError("PDF не содержит страниц.")

            self._render_thumbnails()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось открыть PDF:\n\n{self.file_path}\n\n{e}"
            )
            self.close()

    def _refresh_selection_visuals(self):
        for thumb in self.thumbnails:
            thumb.set_selected(thumb.page_index in self.selected_pages)
        self.selected_info_label.setText(
            f"Выбрано: {len(self.selected_pages)}"
        )

    def set_selection_anchor(self, page_index):
        self.selection_anchor = page_index
        self._refresh_selection_visuals()

    def select_single_page(self, page_index):
        self.selected_pages = {page_index}
        self.selection_anchor = page_index
        self._refresh_selection_visuals()

    def select_page_range(self, page_index):
        if self.selection_anchor is None:
            self.selected_pages = {page_index}
        else:
            first = min(self.selection_anchor, page_index)
            last = max(self.selection_anchor, page_index)
            self.selected_pages = set(range(first, last + 1))
        self.selection_anchor = page_index
        self._refresh_selection_visuals()

    def clear_selection(self):
        self.selected_pages.clear()
        self.selection_anchor = None
        self._refresh_selection_visuals()

    def _page_size_text(self, page):
        rect = page.rect
        width_mm = rect.width * 25.4 / 72.0
        height_mm = rect.height * 25.4 / 72.0
        return f"Размер: {width_mm:.1f} × {height_mm:.1f} мм"

    def _render_thumbnails(self):
        self.selected_pages.clear()
        self.selection_anchor = None

        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.thumbnails.clear()

        for page_index in range(len(self.source_doc)):
            page = self.source_doc.load_page(page_index)

            # Качественный рендер. 2x достаточно для крупных эскизов.
            pix = page.get_pixmap(
                matrix=fitz.Matrix(self.RENDER_ZOOM, self.RENDER_ZOOM),
                alpha=False
            )

            img = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888
            ).copy()

            pixmap = QPixmap.fromImage(img)

            # Масштабируем с сохранением реального соотношения сторон.
            pixmap = pixmap.scaled(
                self.THUMB_WIDTH,
                self.THUMB_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            # Номер страницы.
            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.setSpacing(3)

            label = TransferThumbnail(page_index, pixmap, self)

            number_label = QLabel(f"Страница {page_index + 1}")
            number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number_label.setStyleSheet(
                "color: white; font-weight: bold; background: #444444; "
                "padding: 2px 6px; border-radius: 3px;"
            )

            size_label = QLabel(self._page_size_text(page))
            size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            size_label.setStyleSheet(
                "color: white; background: #555555; "
                "padding: 2px 4px; border-radius: 3px;"
            )

            wrapper_layout.addWidget(
                label,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
            wrapper_layout.addWidget(
                number_label,
                alignment=Qt.AlignmentFlag.AlignCenter
            )
            wrapper_layout.addWidget(
                size_label,
                alignment=Qt.AlignmentFlag.AlignCenter
            )

            self.layout.addWidget(
                wrapper,
                alignment=Qt.AlignmentFlag.AlignHCenter
            )
            self.thumbnails.append(label)

        self.status_label.setText(
            f"Всего страниц: {len(self.source_doc)}"
        )
        self.selected_info_label.setText("Выбрано: 0")

    def is_source_page_open(self, page_index):
        """Проверка, что эта страница относится к данному открытому PDF."""
        return (
            self.source_doc is not None
            and not self.source_doc.is_closed
            and 0 <= int(page_index) < len(self.source_doc)
        )

    def wheelEvent(self, event):
        # Обычное колесо прокручивает окно.
        # Передаём событие QScrollArea, чтобы вертикальный scrollbar
        # работал естественно.
        delta = event.angleDelta().y()
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.value() - delta)
        event.accept()

    def closeEvent(self, event):
        try:
            if self.source_doc is not None and not self.source_doc.is_closed:
                self.source_doc.close()
        except Exception:
            pass

        self.source_doc = None
        super().closeEvent(event)
