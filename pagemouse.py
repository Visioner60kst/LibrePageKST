from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt

class ThumbnailHandler:
    def __init__(self, main_window):
        self.main_window = main_window

    def handle_context_menu(self, widget, pos):
        menu = QMenu()
        
        # Move Actions
        up_action = menu.addAction("UP")
        down_action = menu.addAction("DOWN")
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete page")
        insert_before_action = menu.addAction("Insert empty BEFORE")
        insert_after_action = menu.addAction("Insert empty AFTER")
        duplicate_action = menu.addAction("Duplicate page")
        
        action = menu.exec(widget.mapToGlobal(pos))
        
        if not action or not self.main_window.doc:
            return

        idx = widget.page_index
        total_pages = len(self.main_window.doc)

        # Move logic
        if action == up_action:
            if idx > 0:
                self.main_window.move_page(idx, idx - 1)
        elif action == down_action:
            if idx < total_pages - 1:
                self.main_window.move_page(idx, idx + 1)
        
        # Other actions
        elif action == delete_action:
            self.main_window.delete_page(idx)
        elif action == insert_before_action:
            self.main_window.insert_empty_page(idx)
        elif action == insert_after_action:
            self.main_window.insert_empty_page(idx + 1)
        elif action == duplicate_action:
            self.main_window.duplicate_page(idx)

    def handle_drag_drop(self, source_index, target_index):
        self.main_window.move_page(source_index, target_index)