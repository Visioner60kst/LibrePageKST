import fitz  # PyMuPDF
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QLineEdit, 
                             QPushButton, QHBoxLayout, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt

class CutPageDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cutting PDF")
        self.resize(350, 150)
        self.file_path = file_path
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.radio_even_odd = QRadioButton("Cut even and odd")
        self.radio_each = QRadioButton("Each sheet separately")
        self.radio_custom = QRadioButton("Cut after pages:")
        
        # The first item is selected by default
        self.radio_even_odd.setChecked(True)

        self.input_custom = QLineEdit()
        self.input_custom.setPlaceholderText("For example: 5, 100, 150")
        self.input_custom.setEnabled(False) # Inactive until selected 3-th point

        # Linking the activity of the input field to the selection of a radio button
        self.radio_custom.toggled.connect(self.input_custom.setEnabled)

        layout.addWidget(self.radio_even_odd)
        layout.addWidget(self.radio_each)
        
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(self.radio_custom)
        custom_layout.addWidget(self.input_custom)
        layout.addLayout(custom_layout)

        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold; padding: 5px;")
        self.btn_apply.clicked.connect(self.apply_cut)
        layout.addWidget(self.btn_apply)

    def apply_cut(self):
        # Open the dialog for selecting a folder to save
        out_dir = QFileDialog.getExistingDirectory(self, "Select a folder to save files")
        if not out_dir:
            return  # If the user deselected a folder

        try:
            doc = fitz.open(self.file_path)
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]

            if self.radio_even_odd.isChecked():
                # Division into even and odd
                doc_odd = fitz.open()
                doc_even = fitz.open()
                for i in range(len(doc)):
                    if i % 2 == 0:  # Index 0 - This 1-I am the page (odd)
                        doc_odd.insert_pdf(doc, from_page=i, to_page=i)
                    else:           # Index 1 - This 2-I am the page (even)
                        doc_even.insert_pdf(doc, from_page=i, to_page=i)
                
                if len(doc_odd) > 0: 
                    doc_odd.save(os.path.join(out_dir, f"{base_name}_odd.pdf"))
                if len(doc_even) > 0: 
                    doc_even.save(os.path.join(out_dir, f"{base_name}_even.pdf"))
                
                doc_odd.close()
                doc_even.close()

            elif self.radio_each.isChecked():
                # Each sheet is a separate file
                for i in range(len(doc)):
                    doc_single = fitz.open()
                    doc_single.insert_pdf(doc, from_page=i, to_page=i)
                    doc_single.save(os.path.join(out_dir, f"{base_name}_p_{i+1}.pdf"))
                    doc_single.close()

            elif self.radio_custom.isChecked():
                # Division by ranges
                pages_str = self.input_custom.text()
                try:
                    # Convert the entered string into a sorted list of unique numbers
                    split_pages = sorted(list(set([int(p.strip()) for p in pages_str.split(',') if p.strip().isdigit()])))
                except ValueError:
                    QMessageBox.warning(self, "Error", "Invalid format. Use numbers separated by commas.")
                    return

                if not split_pages:
                    QMessageBox.warning(self, "Error", "Please specify at least one page to cut.")
                    return

                start_idx = 0
                total_pages = len(doc)

                for sp in split_pages:
                    end_idx = sp - 1  # Translation from 1-based V 0-based index
                    if end_idx >= total_pages:
                        end_idx = total_pages - 1
                        
                    if start_idx <= end_idx:
                        doc_part = fitz.open()
                        doc_part.insert_pdf(doc, from_page=start_idx, to_page=end_idx)
                        # Forming a clear name (for example: Name_1-5.pdf)
                        file_part_name = f"{base_name}_{start_idx+1}-{end_idx+1}.pdf"
                        if start_idx == end_idx:
                            file_part_name = f"{base_name}_{start_idx+1}.pdf"
                            
                        doc_part.save(os.path.join(out_dir, file_part_name))
                        doc_part.close()
                    start_idx = end_idx + 1

                # We save the "tail"" (remaining pages after the last one listed)
                if start_idx < total_pages:
                    doc_part = fitz.open()
                    doc_part.insert_pdf(doc, from_page=start_idx, to_page=total_pages - 1)
                    file_part_name = f"{base_name}_{start_idx+1}-{total_pages}.pdf"
                    if start_idx == total_pages - 1:
                        file_part_name = f"{base_name}_{total_pages}.pdf"
                        
                    doc_part.save(os.path.join(out_dir, file_part_name))
                    doc_part.close()

            doc.close()
            QMessageBox.information(self, "Success", "Files successfully cut and saved.")
            self.accept() # Close the window after success

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while cutting:\n{e}")