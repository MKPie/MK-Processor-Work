#!/usr/bin/env python3
# Save this as settings_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, 
    QLineEdit, QSpinBox, QPushButton, QCheckBox, QFormLayout, QFileDialog,
    QMessageBox, QComboBox, QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
import os

class ColorButton(QPushButton):
    """Custom button for selecting colors"""
    
    color_changed = pyqtSignal(str)
    
    def __init__(self, color_code, parent=None):
        super().__init__(parent)
        self.color = color_code
        self.setFixedSize(50, 24)
        self.setStyleSheet(f"background-color: {color_code}; border: 1px solid #aaaaaa;")
        self.clicked.connect(self.show_color_dialog)
    
    def show_color_dialog(self):
        """Show a color picker dialog"""
        from PyQt5.QtWidgets import QColorDialog
        
        color = QColorDialog.getColor(QColor(self.color), self.parent())
        if color.isValid():
            self.color = color.name()
            self.setStyleSheet(f"background-color: {self.color}; border: 1px solid #aaaaaa;")
            self.color_changed.emit(self.color)


class SettingsDialog(QDialog):
    """Settings dialog for the MK Processor application"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.resize(550, 400)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.scraping_tab = QWidget()
        self.fields_tab = QWidget()
        self.appearance_tab = QWidget()
        
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.scraping_tab, "Scraping")
        self.tabs.addTab(self.fields_tab, "Fields")
        self.tabs.addTab(self.appearance_tab, "Appearance")
        
        # Setup each tab
        self.setup_general_tab()
        self.setup_scraping_tab()
        self.setup_fields_tab()
        self.setup_appearance_tab()
        
        # Add tabs to layout
        self.layout.addWidget(self.tabs)
        
        # Add save and cancel buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("actionButton")
        self.save_button.clicked.connect(self.save_settings)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        self.layout.addLayout(button_layout)
    
    def setup_general_tab(self):
        """Setup the general settings tab"""
        layout = QFormLayout(self.general_tab)
        
        # App title
        self.app_title = QLineEdit()
        self.app_title.setText(self.config_manager.get("app", "window_title"))
        layout.addRow("Application Title:", self.app_title)
        
        # Output directory
        output_layout = QHBoxLayout()
        self.output_dir = QLineEdit()
        self.output_dir.setText(os.path.expanduser(self.config_manager.get("output", "output_dir")))
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(browse_button)
        
        layout.addRow("Output Directory:", output_layout)
        
        # Output file prefix
        self.output_prefix = QLineEdit()
        self.output_prefix.setText(self.config_manager.get("output", "prefix"))
        layout.addRow("Output File Prefix:", self.output_prefix)
    
    def setup_scraping_tab(self):
        """Setup the scraping settings tab"""
        layout = QFormLayout(self.scraping_tab)
        
        # Timeout
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 120)
        self.timeout.setValue(self.config_manager.get("scraping", "timeout"))
        layout.addRow("Timeout (seconds):", self.timeout)
        
        # Retry attempts
        self.retry_attempts = QSpinBox()
        self.retry_attempts.setRange(0, 5)
        self.retry_attempts.setValue(self.config_manager.get("scraping", "retry_attempts"))
        layout.addRow("Retry Attempts:", self.retry_attempts)
        
        # User agent rotation
        self.user_agent_rotation = QCheckBox()
        self.user_agent_rotation.setChecked(self.config_manager.get("scraping", "user_agent_rotation"))
        layout.addRow("Rotate User Agents:", self.user_agent_rotation)
    
    def setup_fields_tab(self):
        """Setup the fields settings tab"""
        layout = QVBoxLayout(self.fields_tab)
        
        # Label
        label = QLabel("Specification Fields to Extract as Columns:")
        layout.addWidget(label)
        
        # Fields list
        self.fields_list = QListWidget()
        
        # Add common spec fields from config
        for field in self.config_manager.get("common_spec_fields"):
            item = QListWidgetItem(field)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.fields_list.addItem(item)
        
        layout.addWidget(self.fields_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.add_field_button = QPushButton("Add Field")
        self.add_field_button.clicked.connect(self.add_field)
        
        self.remove_field_button = QPushButton("Remove Field")
        self.remove_field_button.clicked.connect(self.remove_field)
        
        buttons_layout.addWidget(self.add_field_button)
        buttons_layout.addWidget(self.remove_field_button)
        
        layout.addLayout(buttons_layout)
    
    def setup_appearance_tab(self):
        """Setup the appearance settings tab"""
        layout = QFormLayout(self.appearance_tab)
        
        # Primary button color
        primary_color = self.config_manager.get("ui", "button_primary_color")
        self.primary_color_button = ColorButton(primary_color)
        layout.addRow("Primary Button Color:", self.primary_color_button)
        
        # Secondary button color
        secondary_color = self.config_manager.get("ui", "button_secondary_color")
        self.secondary_color_button = ColorButton(secondary_color)
        layout.addRow("Secondary Button Color:", self.secondary_color_button)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addRow(separator)
        
        # Reset to defaults button
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.clicked.connect(self.reset_appearance)
        layout.addRow("", self.reset_button)
    
    def browse_output_dir(self):
        """Open a file dialog to browse for output directory"""
        current_dir = os.path.expanduser(self.output_dir.text())
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", current_dir
        )
        
        if directory:
            self.output_dir.setText(directory)
    
    def add_field(self):
        """Add a new field to the list"""
        item = QListWidgetItem("new_field")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.fields_list.addItem(item)
        self.fields_list.editItem(item)
    
    def remove_field(self):
        """Remove the selected field from the list"""
        selected_items = self.fields_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            self.fields_list.takeItem(self.fields_list.row(item))
    
    def reset_appearance(self):
        """Reset appearance settings to defaults"""
        from config_manager import DEFAULT_CONFIG
        default_primary = DEFAULT_CONFIG["ui"]["button_primary_color"]
        default_secondary = DEFAULT_CONFIG["ui"]["button_secondary_color"]
        
        self.primary_color_button.color = default_primary
        self.primary_color_button.setStyleSheet(f"background-color: {default_primary}; border: 1px solid #aaaaaa;")
        
        self.secondary_color_button.color = default_secondary
        self.secondary_color_button.setStyleSheet(f"background-color: {default_secondary}; border: 1px solid #aaaaaa;")
    
    def save_settings(self):
        """Save settings to config file"""
        # General tab
        self.config_manager.set("app", "window_title", self.app_title.text())
        self.config_manager.set("output", "output_dir", self.output_dir.text())
        self.config_manager.set("output", "prefix", self.output_prefix.text())
        
        # Scraping tab
        self.config_manager.set("scraping", "timeout", self.timeout.value())
        self.config_manager.set("scraping", "retry_attempts", self.retry_attempts.value())
        self.config_manager.set("scraping", "user_agent_rotation", self.user_agent_rotation.isChecked())
        
        # Fields tab
        fields = []
        for i in range(self.fields_list.count()):
            fields.append(self.fields_list.item(i).text())
        self.config_manager.set("common_spec_fields", None, fields)
        
        # Appearance tab
        self.config_manager.set("ui", "button_primary_color", self.primary_color_button.color)
        self.config_manager.set("ui", "button_secondary_color", self.secondary_color_button.color)
        
        # Save config to file
        if self.config_manager.save_config():
            QMessageBox.information(self, "Settings Saved", "Settings have been saved. Restart the application for changes to take effect.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")
