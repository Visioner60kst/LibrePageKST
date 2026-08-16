import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton)
from PyQt6.QtCore import Qt

class ConvertColorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color conversion")
        self.setFixedSize(450, 220)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)

        # 1. Page range
        range_layout = QHBoxLayout()
        range_label = QLabel("Page range:")
        range_label.setFixedWidth(130)
        range_layout.addWidget(range_label)
        
        self.range_combo = QComboBox()
        self.range_combo.addItems([
            "All pages", 
            "Current page", 
            "Even pages", 
            "Odd pages"
        ])
        range_layout.addWidget(self.range_combo)
        self.layout.addLayout(range_layout)

        # 2. Selecting a color model (Target)
        target_layout = QHBoxLayout()
        target_label = QLabel("Color model:")
        target_label.setFixedWidth(130)
        target_layout.addWidget(target_label)
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(["cmyk", "rgb", "grey"])
        target_layout.addWidget(self.target_combo)
        self.layout.addLayout(target_layout)

        # 3. Choice ICC Profile (Dynamic)
        profile_layout = QHBoxLayout()
        profile_label = QLabel("ICC Profile:")
        profile_label.setFixedWidth(130)
        profile_layout.addWidget(profile_label)
        
        self.profile_combo = QComboBox()
        profile_layout.addWidget(self.profile_combo)
        self.layout.addLayout(profile_layout)

        # Linking model changes to updating the list of profiles
        self.target_combo.currentTextChanged.connect(self.update_profiles_list)
        
        # Initializing the list of profiles for the first time
        self.update_profiles_list(self.target_combo.currentText())

        # 4. Ok buttons/Cancel
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Apply")
        self.btn_ok.setStyleSheet("background-color: #9c27b0; color: white; font-weight: bold; padding: 6px;")
        self.btn_ok.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("padding: 6px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        self.layout.addLayout(btn_layout)

    def get_base_dir(self):
        """Defines the base directory for the program to run"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def get_gs_path(self):
        """Identifies the correct executable file Ghostscript depending on OS"""
        base_dir = self.get_base_dir()
        bin_dir = os.path.join(base_dir, "resources", "ghostscript", "gs10.07.1", "bin")
        
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            local_gs = os.path.join(bin_dir, "gs")
            if os.path.exists(local_gs):
                return local_gs
            # If there is no local binary, use the system one
            return "gs" 
        else:
            # For Windows
            return os.path.join(bin_dir, "gswin64c.exe")

    def update_profiles_list(self, target_color):
        """Loads profile files from the corresponding folder into resources"""
        self.profile_combo.clear()
        
        # Default option when inline GS takes your base profile
        self.profile_combo.addItem("The default (no profile)", "")

        # We compare the user's choice with the folder name
        folder_map = {
            "cmyk": "CMYK",
            "rgb": "RGB",
            "grey": "GRAY",
        }
        
        folder_name = folder_map.get(target_color, "")
        if not folder_name:
            return

        base_dir = self.get_base_dir()
        profile_dir = os.path.join(base_dir, "resources", "profiles", folder_name)

        if os.path.exists(profile_dir) and os.path.isdir(profile_dir):
            for file_name in os.listdir(profile_dir):
                if file_name.lower().endswith(('.icc', '.icm')):
                    # We store the full absolute path to the file in userData (for Ghostscript)
                    full_path = os.path.join(profile_dir, file_name)
                    # List only the file name
                    self.profile_combo.addItem(file_name, full_path)

    def get_settings(self):
        """Returns settings to main.py after clicking 'Apply''"""
        return {
            'range': self.range_combo.currentText(),
            'target': self.target_combo.currentText(),
            # currentData() will return the full path to the profile file (or "" if "Default" is selected")
            'profile': self.profile_combo.currentData(),
            'gs_path': self.get_gs_path()  # Added path to Ghostscript
        }