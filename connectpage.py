import fitz  # PyMuPDF
import tempfile
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox

def merge_pdfs_dialog(parent):
    """
    Selects files, merges them into a temporary file and returns its path.
    """
    files, _ = QFileDialog.getOpenFileNames(
        parent,
        "Select PDF files for gluing",
        "",
        "PDF Files (*.pdf)"
    )
    
    if not files:
        return None
        
    if len(files) < 2:
        QMessageBox.warning(parent, "Attention", "Select more than one file.")
        return None
        
    # Sorting: English letters -> Russians
    files = sorted(files)
    
    try:
        # Create a temporary file
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_path = tmp.name
        tmp.close()

        # Glue it together
        merged_doc = fitz.open()
        for f in files:
            with fitz.open(f) as pdf:
                merged_doc.insert_pdf(pdf)
                
        merged_doc.save(tmp_path)
        merged_doc.close()
        
        return tmp_path
        
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Gluing error:\n{e}")
        return None