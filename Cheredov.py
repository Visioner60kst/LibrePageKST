import fitz
from PyQt6.QtWidgets import QMessageBox

def cheredov_pages_action(main_window):
    """
    Interleaving Module: Reassembles pages in order 1, last, 2, penultimate...
    """
    if not main_window.current_file_path or not main_window.doc:
        QMessageBox.warning(main_window, "Attention", "Open first PDF file.")
        return

    total_pages = len(main_window.doc)
    if total_pages < 2:
        QMessageBox.information(main_window, "Information", "Minimum required 2 pages for rotation.")
        return

    reply = QMessageBox.question(
        main_window,
        "Page Alternation",
        "Rebuild (1, last, 2, penultimate...)?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        try:
            # Generating a list of new indexes
            new_order = []
            left = 0
            right = total_pages - 1
            
            while left <= right:
                if left == right:
                    new_order.append(left)
                else:
                    new_order.append(left)
                    new_order.append(right)
                left += 1
                right -= 1
            
            # Rebuilding the document
            main_window.doc.select(new_order)
            
            # We update UI
            main_window.active_page_index = 0
            main_window.render_all()
            main_window.history_manager.save_state()
            
        except Exception as e:
            QMessageBox.critical(main_window, "Error", f"Alternation error: {e}")