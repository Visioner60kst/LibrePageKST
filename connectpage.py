import fitz  # PyMuPDF
import tempfile
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox

def merge_pdfs_dialog(parent):
    """
    Выбирает файлы, склеивает их во временный файл и возвращает путь к нему.
    """
    files, _ = QFileDialog.getOpenFileNames(
        parent,
        "Выберите PDF файлы для склейки",
        "",
        "PDF Files (*.pdf)"
    )
    
    if not files:
        return None
        
    if len(files) < 2:
        QMessageBox.warning(parent, "Внимание", "Выберите больше одного файла.")
        return None
        
    # Сортировка: английские буквы -> русские
    files = sorted(files)
    
    try:
        # Создаем временный файл
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_path = tmp.name
        tmp.close()

        # Склеиваем
        merged_doc = fitz.open()
        for f in files:
            with fitz.open(f) as pdf:
                merged_doc.insert_pdf(pdf)
                
        merged_doc.save(tmp_path)
        merged_doc.close()
        
        return tmp_path
        
    except Exception as e:
        QMessageBox.critical(parent, "Ошибка", f"Ошибка при склеивании:\n{e}")
        return None