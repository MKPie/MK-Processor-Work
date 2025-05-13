#!/usr/bin/env python3
# Save this as plugins/multi_prefix_plugin.py

from PyQt5.QtWidgets import (
    QPushButton, QMessageBox, QVBoxLayout, QDialog, QLabel, QLineEdit, 
    QHBoxLayout, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
import os
import json

class Plugin:
    """Plugin that allows trying multiple prefixes when scraping Katom"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.name = "Multi-Prefix Plugin"
        self.version = "1.0.0"
        self.description = "Try multiple prefixes when scraping Katom"
        self.button = None
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'multi_prefix_config.json')
        self.prefixes = self.load_prefixes()
    
    def load_prefixes(self):
        """Load prefixes from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return ["605", "123", "456"]  # Default prefixes
        else:
            return ["605", "123", "456"]  # Default prefixes
    
    def save_prefixes(self):
        """Save prefixes to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.prefixes, f)
        except Exception as e:
            print(f"Error saving prefixes: {e}")
    
    def initialize(self):
        """Called when the plugin is loaded"""
        print(f"Initializing {self.name} v{self.version}")
        
        # Add a button to the main window's button layout
        self.button = QPushButton("Multi-Prefix Settings", self.main_window)
        self.button.setObjectName("secondaryButton")
        self.button.clicked.connect(self.on_button_clicked)
        
        # Find the button layout in the main window
        button_layout = None
        for i in range(self.main_window.layout().count()):
            item = self.main_window.layout().itemAt(i)
            if item and item.layout() and any(isinstance(item.layout().itemAt(j).widget(), QPushButton) 
                 for j in range(item.layout().count()) if item.layout().itemAt(j).widget()):
                button_layout = item.layout()
                break
        
        if button_layout:
            button_layout.addWidget(self.button)
        else:
            print("Could not find button layout")
    
    def on_button_clicked(self):
        """Handle the button click event"""
        dialog = PrefixDialog(self.prefixes, self.main_window)
        if dialog.exec_():
            self.prefixes = dialog.get_prefixes()
            self.save_prefixes()
            QMessageBox.information(
                self.main_window, 
                "Prefixes Saved", 
                "Multiple prefixes will be tried when the primary prefix fails."
            )
    
    # Hook into the scrape_katom method to try multiple prefixes
    def before_process_file(self, sheet_row, file_info):
        """Hook to modify the scrape_katom method"""
        # Store the original method
        if not hasattr(sheet_row, 'original_scrape_katom'):
            sheet_row.original_scrape_katom = sheet_row.scrape_katom
            # Replace with our enhanced version
            sheet_row.scrape_katom = lambda model_number, prefix: self.enhanced_scrape_katom(sheet_row, model_number, prefix)
        return True
    
    def enhanced_scrape_katom(self, sheet_row, model_number, prefix):
        """Enhanced version of scrape_katom that tries multiple prefixes"""
        # First try with the original prefix
        title, desc, specs_data, specs_html, video_links = sheet_row.original_scrape_katom(model_number, prefix)
        
        # If not found, try alternate prefixes
        if title == "Title not found" or "not found" in title.lower():
            sheet_row.signals.update_status.emit(f"Primary prefix failed, trying alternatives...")
            
            for alt_prefix in self.prefixes:
                if alt_prefix != prefix:  # Skip the original prefix
                    sheet_row.signals.update_status.emit(f"Trying prefix: {alt_prefix}")
                    
                    alt_title, alt_desc, alt_specs, alt_html, alt_video = sheet_row.original_scrape_katom(model_number, alt_prefix)
                    
                    if alt_title != "Title not found" and "not found" not in alt_title.lower():
                        sheet_row.signals.update_status.emit(f"Found match with prefix: {alt_prefix}")
                        return alt_title, alt_desc, alt_specs, alt_html, alt_video
        
        # Return original results (either successful or not)
        return title, desc, specs_data, specs_html, video_links


class PrefixDialog(QDialog):
    """Dialog to manage multiple prefixes"""
    
    def __init__(self, prefixes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Prefix Settings")
        self.resize(400, 300)
        self.prefixes = prefixes.copy()
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Add instructions
        label = QLabel(
            "Configure multiple prefixes to try if the primary prefix fails. "
            "The system will try each prefix in order until a match is found."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Add prefix list
        self.prefix_list = QListWidget()
        for prefix in self.prefixes:
            item = QListWidgetItem(prefix)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.prefix_list.addItem(item)
            
        layout.addWidget(self.prefix_list)
        
        # Add controls for prefix list
        buttons_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_prefix)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_prefix)
        
        self.up_button = QPushButton("↑")
        self.up_button.clicked.connect(self.move_up)
        
        self.down_button = QPushButton("↓")
        self.down_button.clicked.connect(self.move_down)
        
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.remove_button)
        buttons_layout.addWidget(self.up_button)
        buttons_layout.addWidget(self.down_button)
        
        layout.addLayout(buttons_layout)
        
        # Add OK/Cancel buttons
        dialog_buttons = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        dialog_buttons.addStretch(1)
        dialog_buttons.addWidget(self.ok_button)
        dialog_buttons.addWidget(self.cancel_button)
        
        layout.addLayout(dialog_buttons)
    
    def add_prefix(self):
        """Add a new prefix to the list"""
        item = QListWidgetItem("new")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.prefix_list.addItem(item)
        self.prefix_list.editItem(item)
    
    def remove_prefix(self):
        """Remove the selected prefix from the list"""
        selected_items = self.prefix_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            self.prefix_list.takeItem(self.prefix_list.row(item))
    
    def move_up(self):
        """Move the selected prefix up in the list"""
        current_row = self.prefix_list.currentRow()
        if current_row > 0:
            item = self.prefix_list.takeItem(current_row)
            self.prefix_list.insertItem(current_row - 1, item)
            self.prefix_list.setCurrentRow(current_row - 1)
    
    def move_down(self):
        """Move the selected prefix down in the list"""
        current_row = self.prefix_list.currentRow()
        if current_row < self.prefix_list.count() - 1:
            item = self.prefix_list.takeItem(current_row)
            self.prefix_list.insertItem(current_row + 1, item)
            self.prefix_list.setCurrentRow(current_row + 1)
    
    def get_prefixes(self):
        """Get the list of prefixes"""
        prefixes = []
        for i in range(self.prefix_list.count()):
            prefixes.append(self.prefix_list.item(i).text())
        return prefixes
