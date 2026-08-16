from PyQt6.QtWidgets import QPushButton
import fitz

class HistoryManager:
    def __init__(self, parent_module):
        self.parent = parent_module
        self.history = []
        self.index = -1
        
        self.btn_undo = QPushButton("⟲")
        self.btn_undo.setFixedSize(30, 25)
        self.btn_undo.setToolTip("Cancel action")
        self.btn_undo.clicked.connect(self.undo)
        
        self.btn_redo = QPushButton("⟳")
        self.btn_redo.setFixedSize(30, 25)
        self.btn_redo.setToolTip("Return action")
        self.btn_redo.clicked.connect(self.redo)

    def save_state(self):
        if not self.parent.doc: return
        self.history = self.history[:self.index + 1]
        self.history.append(self.parent.doc.write())
        self.index += 1

    def undo(self):
        if self.index > 0:
            self.index -= 1
            self.load_state()

    def redo(self):
        if self.index < len(self.history) - 1:
            self.index += 1
            self.load_state()

    def load_state(self):
        if self.index < 0: return
        pdf_bytes = self.history[self.index]
        
        # Safe closing
        if self.parent.doc:
            self.parent.doc.close()
            self.parent.doc = None # Resetting the link
            
        self.parent.doc = fitz.open("pdf", pdf_bytes)
        
        if self.parent.current_file_path:
            self.parent.open_docs[self.parent.current_file_path] = self.parent.doc
        
        self.parent.active_page_index = min(self.parent.active_page_index, len(self.parent.doc) - 1)
        self.parent.render_all()
        self.parent.update_page_info()