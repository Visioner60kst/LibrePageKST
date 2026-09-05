import fitz
from PyQt6.QtWidgets import QMessageBox


def reverse_pages_action(main_window):
    """
    Реверс порядка страниц PDF.
    Создает новый документ и копирует страницы в обратном порядке.
    """

    if not main_window.doc:
        QMessageBox.warning(
            main_window,
            "Внимание",
            "Сначала откройте PDF файл."
        )
        return

    total_pages = len(main_window.doc)

    if total_pages <= 1:
        QMessageBox.information(
            main_window,
            "Информация",
            "В документе только одна страница."
        )
        return

    reply = QMessageBox.question(
        main_window,
        "Реверс страниц",
        f"Изменить порядок {total_pages} страниц на обратный?",
        QMessageBox.StandardButton.Yes |
        QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )

    if reply != QMessageBox.StandardButton.Yes:
        return

    try:
        old_doc = main_window.doc

        new_doc = fitz.open()

        for page_num in range(total_pages - 1, -1, -1):
            new_doc.insert_pdf(
                old_doc,
                from_page=page_num,
                to_page=page_num
            )

        main_window.doc = new_doc

        if main_window.current_file_path:
            main_window.open_docs[main_window.current_file_path] = new_doc

        main_window.active_page_index = 0

        main_window.render_all()
        main_window.history_manager.save_state()

        QMessageBox.information(
            main_window,
            "Готово",
            "Реверс страниц выполнен."
        )

    except Exception as e:
        QMessageBox.critical(
            main_window,
            "Ошибка",
            f"Не удалось выполнить реверс страниц:\n{e}"
        )