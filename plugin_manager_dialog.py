#!/usr/bin/env python3
# Save as plugin_manager_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QCheckBox, QHeaderView, QMessageBox, QTabWidget,
    QWidget, QTextEdit, QGroupBox, QFormLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QIcon

class PluginManagerDialog(QDialog):
    """Dialog for managing plugins with enable/disable functionality"""
    
    def __init__(self, plugin_manager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        
        self.setWindowTitle("Plugin Manager")
        self.resize(800, 500)  # Larger dialog for better management
        
        # Main layout
        self.layout = QVBoxLayout(self)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.plugins_tab = QWidget()
        self.about_tab = QWidget()
        
        self.tabs.addTab(self.plugins_tab, "Installed Plugins")
        self.tabs.addTab(self.about_tab, "About Plugins")
        
        # Setup each tab
        self.setup_plugins_tab()
        self.setup_about_tab()
        
        # Add tabs to main layout
        self.layout.addWidget(self.tabs)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Plugins")
        self.refresh_btn.clicked.connect(self.refresh_plugins)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_btn)
        
        self.layout.addLayout(button_layout)
        
        # Load plugins data
        self.load_plugins_data()
    
    def setup_plugins_tab(self):
        """Setup the installed plugins tab"""
        layout = QVBoxLayout(self.plugins_tab)
        
        # Introduction text
        intro_label = QLabel(
            "Manage your installed plugins. You can enable/disable plugins and control "
            "whether they are visible in the main UI. Changes take effect immediately."
        )
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)
        
        # Plugins table
        self.plugins_table = QTableWidget(0, 5)  # Rows will be added dynamically, 5 columns
        self.plugins_table.setHorizontalHeaderLabels(["Plugin", "Version", "Enabled", "Show in UI", "Description"])
        
        # Set column properties
        self.plugins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.plugins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.plugins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.plugins_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.plugins_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        
        # Disable editing for the table itself
        self.plugins_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.plugins_table)
    
    def setup_about_tab(self):
        """Setup the about plugins tab"""
        layout = QVBoxLayout(self.about_tab)
        
        # Introduction text
        intro_label = QLabel(
            "This tab provides detailed information about each plugin. "
            "Select a plugin from the list to view its details."
        )
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)
        
        # Split layout for plugin list and details
        split_layout = QHBoxLayout()
        
        # Plugin list
        plugin_list_group = QGroupBox("Plugins")
        plugin_list_layout = QVBoxLayout(plugin_list_group)
        
        self.plugin_list = QTableWidget(0, 2)  # Rows, Columns
        self.plugin_list.setHorizontalHeaderLabels(["Plugin", "Status"])
        self.plugin_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.plugin_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.plugin_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.plugin_list.setSelectionMode(QTableWidget.SingleSelection)
        self.plugin_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.plugin_list.cellClicked.connect(self.plugin_selected)
        
        plugin_list_layout.addWidget(self.plugin_list)
        split_layout.addWidget(plugin_list_group, 1)  # 1 = stretch factor
        
        # Plugin details
        details_group = QGroupBox("Plugin Details")
        details_layout = QVBoxLayout(details_group)
        
        details_form = QFormLayout()
        
        self.detail_name = QLabel("-")
        self.detail_name.setFont(QFont("Arial", 12, QFont.Bold))
        details_form.addRow("Name:", self.detail_name)
        
        self.detail_version = QLabel("-")
        details_form.addRow("Version:", self.detail_version)
        
        self.detail_status = QLabel("-")
        details_form.addRow("Status:", self.detail_status)
        
        self.detail_visibility = QLabel("-")
        details_form.addRow("Visibility:", self.detail_visibility)
        
        details_layout.addLayout(details_form)
        
        # Description
        details_layout.addWidget(QLabel("Description:"))
        self.detail_description = QTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMinimumHeight(100)
        details_layout.addWidget(self.detail_description)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.toggle_enabled_btn = QPushButton("Enable/Disable")
        self.toggle_enabled_btn.clicked.connect(self.toggle_plugin_enabled)
        
        self.toggle_visibility_btn = QPushButton("Show/Hide")
        self.toggle_visibility_btn.clicked.connect(self.toggle_plugin_visibility)
        
        action_layout.addWidget(self.toggle_enabled_btn)
        action_layout.addWidget(self.toggle_visibility_btn)
        
        details_layout.addLayout(action_layout)
        
        # Add some spacer at the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        details_layout.addItem(spacer)
        
        split_layout.addWidget(details_group, 2)  # 2 = stretch factor (wider than list)
        
        layout.addLayout(split_layout)
    
    def load_plugins_data(self):
        """Load plugin data into the UI"""
        # Clear tables
        self.plugins_table.setRowCount(0)
        self.plugin_list.setRowCount(0)
        
        # Sort plugins by name for consistent display
        plugin_names = sorted(self.plugin_manager.plugin_info.keys())
        
        # Fill the plugins table
        for row, plugin_name in enumerate(plugin_names):
            plugin_info = self.plugin_manager.plugin_info[plugin_name]
            
            # Add a row to the plugins table
            self.plugins_table.insertRow(row)
            
            # Plugin name
            name_item = QTableWidgetItem(plugin_info.get("name", plugin_name))
            self.plugins_table.setItem(row, 0, name_item)
            
            # Version
            version_item = QTableWidgetItem(plugin_info.get("version", ""))
            self.plugins_table.setItem(row, 1, version_item)
            
            # Enabled checkbox
            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(plugin_info.get("enabled", True))
            enabled_checkbox.stateChanged.connect(
                lambda state, name=plugin_name: self.on_enabled_changed(state, name)
            )
            self.plugins_table.setCellWidget(row, 2, self.create_checkbox_widget(enabled_checkbox))
            
            # Show in UI checkbox
            show_ui_checkbox = QCheckBox()
            show_ui_checkbox.setChecked(plugin_info.get("show_in_ui", True))
            show_ui_checkbox.stateChanged.connect(
                lambda state, name=plugin_name: self.on_visibility_changed(state, name)
            )
            self.plugins_table.setCellWidget(row, 3, self.create_checkbox_widget(show_ui_checkbox))
            
            # Description
            description_item = QTableWidgetItem(plugin_info.get("description", ""))
            self.plugins_table.setItem(row, 4, description_item)
            
            # Add to plugin list in the About tab
            self.plugin_list.insertRow(row)
            
            # Plugin name
            list_name_item = QTableWidgetItem(plugin_info.get("name", plugin_name))
            self.plugin_list.setItem(row, 0, list_name_item)
            
            # Status
            status_text = "Enabled" if plugin_info.get("enabled", True) else "Disabled"
            status_item = QTableWidgetItem(status_text)
            if plugin_info.get("enabled", True):
                status_item.setForeground(QColor("green"))
            else:
                status_item.setForeground(QColor("red"))
            self.plugin_list.setItem(row, 1, status_item)
        
        # Select the first plugin if available
        if self.plugin_list.rowCount() > 0:
            self.plugin_list.selectRow(0)
            self.plugin_selected(0, 0)
    
    def create_checkbox_widget(self, checkbox):
        """Create a widget that centers a checkbox"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget
    
    def on_enabled_changed(self, state, plugin_name):
        """Handle enabled checkbox state changes"""
        enabled = state == Qt.Checked
        self.plugin_manager.enable_plugin(plugin_name, enabled)
        
        # Update the plugin list status
        self.update_plugin_list_status(plugin_name, enabled)
        
        # If the currently selected plugin is the one changed, update details
        selected_rows = self.plugin_list.selectedItems()
        if selected_rows:
            selected_plugin = self.get_selected_plugin_name()
            if selected_plugin == plugin_name:
                self.update_plugin_details(plugin_name)
    
    def on_visibility_changed(self, state, plugin_name):
        """Handle visibility checkbox state changes"""
        visible = state == Qt.Checked
        self.plugin_manager.set_plugin_visibility(plugin_name, visible)
        
        # If the currently selected plugin is the one changed, update details
        selected_rows = self.plugin_list.selectedItems()
        if selected_rows:
            selected_plugin = self.get_selected_plugin_name()
            if selected_plugin == plugin_name:
                self.update_plugin_details(plugin_name)
    
    def update_plugin_list_status(self, plugin_name, enabled):
        """Update the status of a plugin in the list"""
        # Find the plugin in the list
        for row in range(self.plugin_list.rowCount()):
            name_item = self.plugin_list.item(row, 0)
            if name_item and self.get_plugin_name_from_display(name_item.text()) == plugin_name:
                # Update status
                status_text = "Enabled" if enabled else "Disabled"
                status_item = QTableWidgetItem(status_text)
                if enabled:
                    status_item.setForeground(QColor("green"))
                else:
                    status_item.setForeground(QColor("red"))
                self.plugin_list.setItem(row, 1, status_item)
                break
    
    def get_plugin_name_from_display(self, display_name):
        """Get the plugin name (key) from the display name"""
        for plugin_name, info in self.plugin_manager.plugin_info.items():
            if info.get("name", plugin_name) == display_name:
                return plugin_name
        return display_name
    
    def plugin_selected(self, row, column):
        """Handle plugin selection in the list"""
        name_item = self.plugin_list.item(row, 0)
        if name_item:
            plugin_name = self.get_plugin_name_from_display(name_item.text())
            self.update_plugin_details(plugin_name)
    
    def update_plugin_details(self, plugin_name):
        """Update the plugin details panel"""
        if plugin_name in self.plugin_manager.plugin_info:
            plugin_info = self.plugin_manager.plugin_info[plugin_name]
            
            # Update detail fields
            self.detail_name.setText(plugin_info.get("name", plugin_name))
            self.detail_version.setText(plugin_info.get("version", "Unknown"))
            
            status = "Enabled" if plugin_info.get("enabled", True) else "Disabled"
            status_color = "green" if plugin_info.get("enabled", True) else "red"
            self.detail_status.setText(status)
            self.detail_status.setStyleSheet(f"color: {status_color};")
            
            visibility = "Visible in UI" if plugin_info.get("show_in_ui", True) else "Hidden from UI"
            self.detail_visibility.setText(visibility)
            
            self.detail_description.setText(plugin_info.get("description", "No description available."))
            
            # Update button texts
            enabled_text = "Disable" if plugin_info.get("enabled", True) else "Enable"
            self.toggle_enabled_btn.setText(enabled_text)
            
            visibility_text = "Hide from UI" if plugin_info.get("show_in_ui", True) else "Show in UI"
            self.toggle_visibility_btn.setText(visibility_text)
    
    def toggle_plugin_enabled(self):
        """Toggle the enabled state of the selected plugin"""
        plugin_name = self.get_selected_plugin_name()
        if plugin_name:
            plugin_info = self.plugin_manager.plugin_info[plugin_name]
            enabled = plugin_info.get("enabled", True)
            
            # Toggle state
            self.plugin_manager.enable_plugin(plugin_name, not enabled)
            
            # Update UI
            self.update_plugin_details(plugin_name)
            self.update_plugin_list_status(plugin_name, not enabled)
            
            # Refresh the main plugins table
            self.refresh_plugins()
    
    def toggle_plugin_visibility(self):
        """Toggle the visibility of the selected plugin"""
        plugin_name = self.get_selected_plugin_name()
        if plugin_name:
            plugin_info = self.plugin_manager.plugin_info[plugin_name]
            visible = plugin_info.get("show_in_ui", True)
            
            # Toggle state
            self.plugin_manager.set_plugin_visibility(plugin_name, not visible)
            
            # Update UI
            self.update_plugin_details(plugin_name)
            
            # Refresh the main plugins table
            self.refresh_plugins()
    
    def get_selected_plugin_name(self):
        """Get the name of the currently selected plugin"""
        selected_rows = self.plugin_list.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            name_item = self.plugin_list.item(row, 0)
            if name_item:
                return self.get_plugin_name_from_display(name_item.text())
        return None
    
    def refresh_plugins(self):
        """Refresh plugins and update the UI"""
        self.plugin_manager.reload_plugins()
        self.load_plugins_data()
        QMessageBox.information(self, "Plugins Refreshed", "Plugins have been refreshed successfully.")


if __name__ == "__main__":
    # For testing
    import sys
    from PyQt5.QtWidgets import QApplication
    from plugin_manager import PluginManager
    
    app = QApplication(sys.argv)
    
    # Mock main window
    class MockMainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setGeometry(100, 100, 300, 200)
    
    main_window = MockMainWindow()
    plugin_manager = PluginManager(main_window)
    
    dialog = PluginManagerDialog(plugin_manager)
    dialog.exec_()
    
    sys.exit(app.exec_())
