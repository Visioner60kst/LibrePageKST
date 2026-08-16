import fitz
from PyQt6.QtWidgets import QMessageBox


def reverse_pages_action(main_window):
    """
    Reverse page order PDF.
    Creates a new document and copies the pages in reverse order.
    """

    if not main_window.doc:
        QMessageBox.warning(
            main_window,
            "Attention",
            "First open PDF file."
        )
        return

    total_pages = len(main_window.doc)

    if total_pages <= 1:
        QMessageBox.information(
            main_window,
            "Information",
            "There is only one page in the document."
        )
        return

    reply = QMessageBox.question(
        main_window,
        "Reverse pages",
        f"Change order {total_pages} pages to return?",
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
            "Done",
            "Page reverse completed."
        )

    except Exception as e:
        QMessageBox.critical(
            main_window,
            "Error",
            f"Failed to reverse pages:\n{e}"
        )