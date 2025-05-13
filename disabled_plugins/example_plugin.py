#!/usr/bin/env python3
# Save as plugins/example_plugin.py

from PyQt5.QtWidgets import (
    QPushButton, QMessageBox, QVBoxLayout, QDialog, QLabel, QLineEdit
)
from PyQt5.QtCore import Qt

class Plugin:
    """Example plugin that demonstrates how to extend the MK Processor application"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.name = "Example Plugin"
        self.version = "1.0.0"
        self.description = "Demonstrates plugin functionality with enable/disable and show/hide support"
        self.button = None
    
    def initialize(self):
        """Called when the plugin is loaded and should be shown in UI"""
        print(f"Initializing {self.name} v{self.version}")
        
        # Add a button to the main window's button layout
        self.button = QPushButton("Example Plugin", self.main_window)
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
    
    def hide_ui(self):
        """Hide UI elements when plugin is set to not show in UI"""
        if self.button and self.button.parent():
            self.button.setVisible(False)
    
    def cleanup(self):
        """Called when the plugin is disabled or unloaded"""
        if self.button and self.button.parent():
            # Remove the button from its parent layout
            parent_layout = self.button.parent().layout()
            if parent_layout:
                parent_layout.removeWidget(self.button)
                self.button.deleteLater()
                self.button = None
    
    def on_button_clicked(self):
        """Handle the button click event"""
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(self.name)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Add content to the dialog
        label = QLabel(f"This is an example plugin dialog.\nYou can add custom functionality here.", dialog)
        layout.addWidget(label)
        
        # Add some interactive element
        input_field = QLineEdit(dialog)
        input_field.setPlaceholderText("Enter something...")
        layout.addWidget(input_field)
        
        # Add an action button
        action_button = QPushButton("Do Something", dialog)
        action_button.clicked.connect(lambda: QMessageBox.information(
            dialog, "Plugin Action", f"You entered: {input_field.text()}"
        ))
        layout.addWidget(action_button)
        
        dialog.exec_()
    
    # Hook function that will be called during file processing
    def before_process_file(self, sheet_row, file_info):
        """Called before a file is processed"""
        print(f"Plugin hook: before_process_file for {file_info['name']}")
        # You could modify parameters or perform additional actions here
        return True  # Return True to allow processing to continue
    
    # Hook function that will be called after file processing
    def after_process_file(self, sheet_row, output_df, output_path):
        """Called after a file has been processed"""
        print(f"Plugin hook: after_process_file, saved to {output_path}")
        # You could perform additional actions on the output data
        return True
