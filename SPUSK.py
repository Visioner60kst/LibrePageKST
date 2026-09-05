import sys
import os
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QGroupBox, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt

class SpuskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Спуск полос")
        self.resize(500, 530)

        layout = QVBoxLayout(self)

        # 1. Группа: ПЕРЕТАСОВАТЬ СТРАНИЦЫ
        group1 = QGroupBox("ПЕРЕТАСОВАТЬ СТРАНИЦЫ (Аналог Shuffle pages)")
        layout1 = QVBoxLayout()

        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel("Количество страниц в группе:"))
        self.group_size_input = QLineEdit("4")
        h_layout1.addWidget(self.group_size_input)
        layout1.addLayout(h_layout1)

        instruction_text = (
            "___________________________________________________________________\n"
            "ПРАВИЛА\n"
            "Укажите номер каждой страницы в первой группе. Числа разделяются пробелами.\n"
            "Если после числа поставить *(звездочку), то страница перевернется на 180 гр.\n"
            "Если после числа поставить / , то страница перевернется на 90 гр. по часовой\n"
            "Если после числа поставить \\ , то страница перевернется на 90 гр. против часовой\n"
            "X добавляет пустую страницу\n"
            "___________________________________________________________________"
        )
        instr_label = QLabel(instruction_text)
        instr_label.setWordWrap(True)
        layout1.addWidget(instr_label)

        self.formula_input = QLineEdit("4 1 2 3")
        layout1.addWidget(self.formula_input)

        group1.setLayout(layout1)
        layout.addWidget(group1)

        # 2. Группа: РАЗМЕЩЕНИЕ СТРАНИЦ НА ЛИСТЕ
        group2 = QGroupBox("РАЗМЕЩЕНИЕ СТРАНИЦ НА ЛИСТЕ (Аналог N-up page)")
        layout2 = QVBoxLayout()

        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel("Выберите новый размер листа:"))
        self.size_combo = QComboBox()
        self.sizes = {
            "Пользовательский": (0, 0),
            "A0": (841, 1189),
            "A1": (594, 841),
            "A2": (420, 594),
            "A3": (297, 420),
            "A4": (210, 297),
            "A5": (148, 210),
            "A6": (105, 148),
            "A7": (74, 105)
        }
        self.size_combo.addItems(self.sizes.keys())
        self.size_combo.setCurrentText("A3")
        self.size_combo.currentTextChanged.connect(self.update_size_inputs)
        h_layout2.addWidget(self.size_combo)
        layout2.addLayout(h_layout2)

        h_layout3 = QHBoxLayout()
        h_layout3.addWidget(QLabel("Ширина (мм):"))
        self.width_input = QLineEdit("297")
        h_layout3.addWidget(self.width_input)
        h_layout3.addWidget(QLabel("Высота (мм):"))
        self.height_input = QLineEdit("420")
        h_layout3.addWidget(self.height_input)
        layout2.addLayout(h_layout3)

        h_layout4 = QHBoxLayout()
        h_layout4.addWidget(QLabel("Поместить на листе  -  в столбик:"))
        self.cols_input = QLineEdit("2")
        h_layout4.addWidget(self.cols_input)
        h_layout4.addWidget(QLabel("в строку:"))
        self.rows_input = QLineEdit("1")
        h_layout4.addWidget(self.rows_input)
        layout2.addLayout(h_layout4)

        group2.setLayout(layout2)
        layout.addWidget(group2)

        # Блок кнопок Загрузить и Сохранить
        btn_saveload_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("ЗАГРУЗИТЬ СПУСК")
        self.btn_load.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 5px;")
        self.btn_load.clicked.connect(self.load_spusk)
        
        self.btn_save = QPushButton("СОХРАНИТЬ СПУСК")
        self.btn_save.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 5px;")
        self.btn_save.clicked.connect(self.save_spusk)
        
        btn_saveload_layout.addWidget(self.btn_load)
        btn_saveload_layout.addWidget(self.btn_save)
        layout.addLayout(btn_saveload_layout)

        # Кнопка применить
        self.btn_apply = QPushButton("ПРИМЕНИТЬ")
        self.btn_apply.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_apply.clicked.connect(self.accept)
        layout.addWidget(self.btn_apply)

    def update_size_inputs(self, text):
        if text != "Пользовательский":
            w, h = self.sizes[text]
            self.width_input.setText(str(w))
            self.height_input.setText(str(h))

    def get_settings(self):
        try:
            w = float(self.width_input.text().replace(',', '.'))
            h = float(self.height_input.text().replace(',', '.'))
            cols = int(self.cols_input.text())
            rows = int(self.rows_input.text())
            group_size = int(self.group_size_input.text())
            formula = self.formula_input.text().strip()

            return {
                'target_w': w,
                'target_h': h,
                'cols': cols,
                'rows': rows,
                'group_size': group_size,
                'formula': formula
            }
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Проверьте правильность введенных числовых значений.")
            return None

    def get_resources_dir(self):
        """Определяет правильный путь к папке resources/spusk, даже если программа стала exe"""
        if getattr(sys, 'frozen', False):
            # Если программа скомпилирована PyInstaller
            base_dir = os.path.dirname(sys.executable)
        else:
            # Если запущена как python скрипт
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        res_dir = os.path.join(base_dir, "resources", "spusk")
        os.makedirs(res_dir, exist_ok=True) # Создаем папку, если ее нет
        return res_dir

    def save_spusk(self):
        settings = self.get_settings()
        if not settings:
            return # Если есть ошибка в полях, get_settings() вернет None
            
        spusk_dir = self.get_resources_dir()
        filepath, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить спуск", 
            spusk_dir, 
            "JSON Files (*.json)"
        )
        
        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
                
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Успешно", "Сценарий спуска сохранен.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить файл:\n{e}")

    def load_spusk(self):
        spusk_dir = self.get_resources_dir()
        filepath, _ = QFileDialog.getOpenFileName(
            self, 
            "Загрузить спуск", 
            spusk_dir, 
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Подставляем значения в поля
                self.width_input.setText(str(settings.get('target_w', '')))
                self.height_input.setText(str(settings.get('target_h', '')))
                self.cols_input.setText(str(settings.get('cols', '')))
                self.rows_input.setText(str(settings.get('rows', '')))
                self.group_size_input.setText(str(settings.get('group_size', '')))
                self.formula_input.setText(str(settings.get('formula', '')))
                
                # Пытаемся сопоставить загруженные размеры с выпадающим списком форматов
                w = settings.get('target_w', 0)
                h = settings.get('target_h', 0)
                matched = False
                for size_name, (sw, sh) in self.sizes.items():
                    if size_name != "Пользовательский" and float(sw) == float(w) and float(sh) == float(h):
                        self.size_combo.setCurrentText(size_name)
                        matched = True
                        break
                
                if not matched:
                    self.size_combo.setCurrentText("Пользовательский")

            except Exception as e:
                QMessageBox.warning(self, "Ошибка загрузки", f"Не удалось загрузить файл:\n{e}")