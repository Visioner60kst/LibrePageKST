import fitz  # PyMuPDF
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QRadioButton, QLineEdit, 
                             QPushButton, QHBoxLayout, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt

class CutPageDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Разрезка PDF")
        self.resize(350, 150)
        self.file_path = file_path
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.radio_even_odd = QRadioButton("Разрезать четные и нечетные")
        self.radio_each = QRadioButton("Каждый лист отдельно")
        self.radio_custom = QRadioButton("Разрезать после страниц:")
        
        # По умолчанию выбран первый пункт
        self.radio_even_odd.setChecked(True)

        self.input_custom = QLineEdit()
        self.input_custom.setPlaceholderText("Например: 5, 100, 150")
        self.input_custom.setEnabled(False) # Неактивно, пока не выбран 3-й пункт

        # Привязываем активность поля ввода к выбору радиокнопки
        self.radio_custom.toggled.connect(self.input_custom.setEnabled)

        layout.addWidget(self.radio_even_odd)
        layout.addWidget(self.radio_each)
        
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(self.radio_custom)
        custom_layout.addWidget(self.input_custom)
        layout.addLayout(custom_layout)

        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setStyleSheet("background-color: #fd7e14; color: white; font-weight: bold; padding: 5px;")
        self.btn_apply.clicked.connect(self.apply_cut)
        layout.addWidget(self.btn_apply)

    def apply_cut(self):
        # Открываем диалог выбора папки для сохранения
        out_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения файлов")
        if not out_dir:
            return  # Если пользователь отменил выбор папки

        try:
            doc = fitz.open(self.file_path)
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]

            if self.radio_even_odd.isChecked():
                # Разделение на четные и нечетные
                doc_odd = fitz.open()
                doc_even = fitz.open()
                for i in range(len(doc)):
                    if i % 2 == 0:  # Индекс 0 - это 1-я страница (нечетная)
                        doc_odd.insert_pdf(doc, from_page=i, to_page=i)
                    else:           # Индекс 1 - это 2-я страница (четная)
                        doc_even.insert_pdf(doc, from_page=i, to_page=i)
                
                if len(doc_odd) > 0: 
                    doc_odd.save(os.path.join(out_dir, f"{base_name}_нечетные.pdf"))
                if len(doc_even) > 0: 
                    doc_even.save(os.path.join(out_dir, f"{base_name}_четные.pdf"))
                
                doc_odd.close()
                doc_even.close()

            elif self.radio_each.isChecked():
                # Каждый лист отдельным файлом
                for i in range(len(doc)):
                    doc_single = fitz.open()
                    doc_single.insert_pdf(doc, from_page=i, to_page=i)
                    doc_single.save(os.path.join(out_dir, f"{base_name}_стр_{i+1}.pdf"))
                    doc_single.close()

            elif self.radio_custom.isChecked():
                # Разделение по диапазонам
                pages_str = self.input_custom.text()
                try:
                    # Преобразуем введенную строку в отсортированный список уникальных чисел
                    split_pages = sorted(list(set([int(p.strip()) for p in pages_str.split(',') if p.strip().isdigit()])))
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", "Неверный формат. Используйте числа, разделенные запятыми.")
                    return

                if not split_pages:
                    QMessageBox.warning(self, "Ошибка", "Укажите хотя бы одну страницу для разрезки.")
                    return

                start_idx = 0
                total_pages = len(doc)

                for sp in split_pages:
                    end_idx = sp - 1  # Перевод из 1-based в 0-based индекс
                    if end_idx >= total_pages:
                        end_idx = total_pages - 1
                        
                    if start_idx <= end_idx:
                        doc_part = fitz.open()
                        doc_part.insert_pdf(doc, from_page=start_idx, to_page=end_idx)
                        # Формируем понятное имя (например: Имя_1-5.pdf)
                        file_part_name = f"{base_name}_{start_idx+1}-{end_idx+1}.pdf"
                        if start_idx == end_idx:
                            file_part_name = f"{base_name}_{start_idx+1}.pdf"
                            
                        doc_part.save(os.path.join(out_dir, file_part_name))
                        doc_part.close()
                    start_idx = end_idx + 1

                # Сохраняем "хвост" (оставшиеся страницы после последней указанной)
                if start_idx < total_pages:
                    doc_part = fitz.open()
                    doc_part.insert_pdf(doc, from_page=start_idx, to_page=total_pages - 1)
                    file_part_name = f"{base_name}_{start_idx+1}-{total_pages}.pdf"
                    if start_idx == total_pages - 1:
                        file_part_name = f"{base_name}_{total_pages}.pdf"
                        
                    doc_part.save(os.path.join(out_dir, file_part_name))
                    doc_part.close()

            doc.close()
            QMessageBox.information(self, "Успех", "Файлы успешно разрезаны и сохранены.")
            self.accept() # Закрываем окно после успеха

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при разрезке:\n{e}")