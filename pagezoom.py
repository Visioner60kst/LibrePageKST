from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QApplication
)
from PyQt6.QtCore import Qt


class PageZoom(QWidget):
    """
    Масштаб листа.

    100% = размер активного листа,
    полученный при выравнивании "По высоте".

    Масштабирование производится относительно
    центра активного листа.
    """

    ZOOM_VALUES = [
        10, 20, 30, 40, 50, 60, 70, 80, 90,
        100,
        120, 150, 180, 200, 250, 300
    ]

    def __init__(self, main_window):
        super().__init__(main_window)

        self.main_window = main_window

        # --------------------------------------------------
        # Основной layout
        # --------------------------------------------------

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # --------------------------------------------------
        # Выпадающий список
        # --------------------------------------------------

        self.combo = QComboBox()

        self.combo.setFixedWidth(72)
        self.combo.setFixedHeight(25)

        for value in self.ZOOM_VALUES:
            self.combo.addItem(
                f"{value}%",
                value
            )

        # По умолчанию 100%
        self.combo.setCurrentIndex(
            self.ZOOM_VALUES.index(100)
        )

        self.combo.currentIndexChanged.connect(
            self._zoom_changed
        )

        # --------------------------------------------------
        # Надпись
        # --------------------------------------------------

        self.label = QLabel("МАСШТАБ ЛИСТА")

        self.label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        # --------------------------------------------------
        # Стили
        # --------------------------------------------------

        self.combo.setStyleSheet("""
            QComboBox {
                background-color: #e0e0e0;
                color: black;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding-left: 6px;
                font-weight: bold;
            }

            QComboBox:hover {
                background-color: #eeeeee;
            }

            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)

        self.label.setStyleSheet("""
            QLabel {
                color: #555555;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        layout.addWidget(self.combo)
        layout.addWidget(self.label)

    # ======================================================
    # Получить выбранный процент
    # ======================================================

    def value(self):
        return int(
            self.combo.currentData()
        )

    # ======================================================
    # Установить процент
    # ======================================================

    def set_value(self, value):
        """
        Устанавливает значение списка,
        не вызывая масштабирование.
        """

        value = int(value)

        if value not in self.ZOOM_VALUES:
            value = min(
                self.ZOOM_VALUES,
                key=lambda x: abs(x - value)
            )

        index = self.ZOOM_VALUES.index(value)

        self.combo.blockSignals(True)

        self.combo.setCurrentIndex(index)

        self.combo.blockSignals(False)

    # ======================================================
    # Изменение масштаба пользователем
    # ======================================================

    def _zoom_changed(self, index):

        if index < 0:
            return

        value = self.combo.itemData(index)

        if value is None:
            return

        self.apply_zoom(
            int(value)
        )

    # ======================================================
    # Основное масштабирование
    # ======================================================

    def apply_zoom(self, percent):

        main = self.main_window

        if not main.doc:
            return

        # --------------------------------------------------
        # Определяем активный лист
        # --------------------------------------------------

        page_index = main.active_page_index

        if (
            page_index < 0
            or page_index >= len(main.doc)
        ):
            page_index = 0
            main.active_page_index = 0

        page = main.doc.load_page(page_index)

        page_width = page.rect.width
        page_height = page.rect.height

        if page_height <= 0:
            return

        # --------------------------------------------------
        # Размер видимой области
        # --------------------------------------------------

        viewport = main.scroll_area.viewport()

        view_height = viewport.height()

        # Если включены линейки и отображается
        # один лист — оставляем место под линейку.
        if (
            main.pages_in_row == 1
            and main.rulers_enabled
        ):
            view_height -= 40

        if view_height <= 0:
            return

        # --------------------------------------------------
        # Вычисляем масштаб "По высоте".
        #
        # Этот масштаб = 100%.
        # --------------------------------------------------

        base_zoom = (
            view_height
            / page_height
            * 100.0
        )

        # --------------------------------------------------
        # Применяем выбранный процент
        #
        # Например:
        #
        # По высоте = 72%
        #
        # выбран 150%
        #
        # реальный масштаб:
        #
        # 72 * 1.5 = 108%
        # --------------------------------------------------

        real_zoom = (
            base_zoom
            * float(percent)
            / 100.0
        )

        if real_zoom < 1:
            real_zoom = 1

        # Сохраняем технический масштаб
        main.current_zoom = real_zoom

        # --------------------------------------------------
        # Запоминаем активную страницу
        # --------------------------------------------------

        main.active_page_index = page_index

        # --------------------------------------------------
        # Перерисовываем страницы
        # --------------------------------------------------

        main.render_pages()

        # --------------------------------------------------
        # Центрируем активный лист
        # --------------------------------------------------

        self.center_active_page()

    # ======================================================
    # Центрирование активного листа
    # ======================================================

    def center_active_page(self):

        main = self.main_window

        if not main.page_widgets:
            return

        active_widget = None

        # --------------------------------------------------
        # Ищем активный лист
        # --------------------------------------------------

        for widget in main.page_widgets:

            if (
                widget.page_index
                == main.active_page_index
            ):
                active_widget = widget
                break

        if active_widget is None:
            return

        # --------------------------------------------------
        # Даём Qt пересчитать размеры
        # --------------------------------------------------

        QApplication.processEvents()

        viewport = main.scroll_area.viewport()

        # --------------------------------------------------
        # Получаем положение листа
        # относительно preview_container
        # --------------------------------------------------

        top_left = active_widget.mapTo(
            main.preview_container,
            active_widget.rect().topLeft()
        )

        page_rect = active_widget.rect().translated(
            top_left
        )

        # --------------------------------------------------
        # Центр листа
        # --------------------------------------------------

        page_center_x = page_rect.center().x()
        page_center_y = page_rect.center().y()

        # --------------------------------------------------
        # Центр окна просмотра
        # --------------------------------------------------

        viewport_center_x = (
            viewport.width() // 2
        )

        viewport_center_y = (
            viewport.height() // 2
        )

        # --------------------------------------------------
        # Рассчитываем прокрутку
        # --------------------------------------------------

        new_x = (
            page_center_x
            - viewport_center_x
        )

        new_y = (
            page_center_y
            - viewport_center_y
        )

        # --------------------------------------------------
        # Ограничиваем scrollbar
        # --------------------------------------------------

        hbar = main.scroll_area.horizontalScrollBar()
        vbar = main.scroll_area.verticalScrollBar()

        new_x = max(
            hbar.minimum(),
            min(
                int(new_x),
                hbar.maximum()
            )
        )

        new_y = max(
            vbar.minimum(),
            min(
                int(new_y),
                vbar.maximum()
            )
        )

        # --------------------------------------------------
        # Устанавливаем положение
        # --------------------------------------------------

        hbar.setValue(new_x)
        vbar.setValue(new_y)

        QApplication.processEvents()

    # ======================================================
    # Установить 100%
    # ======================================================

    def set_100_percent(self):

        self.set_value(100)