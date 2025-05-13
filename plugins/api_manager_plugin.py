#!/usr/bin/env python3
# Save this as plugins/api_manager_plugin.py

import os
import json
import requests
import traceback
from PyQt5.QtWidgets import (
    QPushButton, QMessageBox, QVBoxLayout, QHBoxLayout, QDialog, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QTabWidget, QWidget, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QCheckBox,
    QFileDialog, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

class ApiRequestThread(QThread):
    """Thread for making API requests without blocking the UI"""
    
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, method, url, headers, params, data, timeout=30):
        super().__init__()
        self.method = method
        self.url = url
        self.headers = headers
        self.params = params
        self.data = data
        self.timeout = timeout
    
    def run(self):
        try:
            # Convert headers from JSON string to dict if needed
            headers = self.headers
            if isinstance(headers, str) and headers.strip():
                try:
                    headers = json.loads(headers)
                except:
                    self.error_occurred.emit("Invalid JSON in headers")
                    return
            
            # Convert params from JSON string to dict if needed
            params = self.params
            if isinstance(params, str) and params.strip():
                try:
                    params = json.loads(params)
                except:
                    self.error_occurred.emit("Invalid JSON in query parameters")
                    return
            
            # Convert data from JSON string to dict if needed
            data = self.data
            if isinstance(data, str) and data.strip():
                try:
                    data = json.loads(data)
                except:
                    self.error_occurred.emit("Invalid JSON in request body")
                    return
            
            # Make the API request
            response = requests.request(
                method=self.method,
                url=self.url,
                headers=headers,
                params=params,
                json=data if data else None,
                timeout=self.timeout
            )
            
            # Prepare result
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "elapsed": response.elapsed.total_seconds(),
                "content_type": response.headers.get("Content-Type", ""),
                "raw_response": response.text
            }
            
            # Try to parse JSON if content type is JSON
            if "application/json" in result["content_type"] or response.text.strip().startswith("{") or response.text.strip().startswith("["):
                try:
                    result["json_response"] = response.json()
                except:
                    result["json_response"] = None
            
            self.result_ready.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class ApiTestingDialog(QDialog):
    """Dialog for testing API endpoints"""
    
    def __init__(self, api_config, parent=None):
        super().__init__(parent)
        self.api_config = api_config
        self.current_endpoint = None
        self.request_thread = None
        
        self.setWindowTitle("API Testing")
        self.resize(1000, 700)
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create a splitter for the left panel (endpoints) and right panel (details)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - List of endpoints
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Search box for endpoints
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search endpoints...")
        self.search_box.textChanged.connect(self.filter_endpoints)
        left_layout.addWidget(self.search_box)
        
        # Add button for new endpoint
        self.add_endpoint_btn = QPushButton("Add New Endpoint")
        self.add_endpoint_btn.clicked.connect(self.add_new_endpoint)
        left_layout.addWidget(self.add_endpoint_btn)
        
        # Table of endpoints
        self.endpoints_table = QTableWidget(0, 2)  # 0 rows, 2 columns (Method, Endpoint)
        self.endpoints_table.setHorizontalHeaderLabels(["Method", "Endpoint"])
        self.endpoints_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.endpoints_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.endpoints_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.endpoints_table.cellClicked.connect(self.endpoint_selected)
        
        left_layout.addWidget(self.endpoints_table)
        
        # Right panel - Endpoint details and testing
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Tabs for Request, Response, and Configuration
        self.tabs = QTabWidget()
        self.request_tab = QWidget()
        self.response_tab = QWidget()
        self.config_tab = QWidget()
        
        self.tabs.addTab(self.request_tab, "Request")
        self.tabs.addTab(self.response_tab, "Response")
        self.tabs.addTab(self.config_tab, "Configuration")
        
        # Setup tabs
        self.setup_request_tab()
        self.setup_response_tab()
        self.setup_config_tab()
        
        right_layout.addWidget(self.tabs)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])  # Initial sizes
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save All")
        self.save_btn.clicked.connect(self.save_all_changes)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Load endpoints
        self.load_endpoints()
    
    def setup_request_tab(self):
        layout = QVBoxLayout(self.request_tab)
        
        # URL and Method
        url_layout = QHBoxLayout()
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        self.method_combo.currentTextChanged.connect(self.method_changed)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/endpoint")
        self.url_input.textChanged.connect(self.url_changed)
        
        url_layout.addWidget(self.method_combo)
        url_layout.addWidget(self.url_input, 1)  # Stretch factor 1
        
        layout.addLayout(url_layout)
        
        # Headers, Params, Body in tabs
        request_details_tabs = QTabWidget()
        
        # Headers tab
        headers_tab = QWidget()
        headers_layout = QVBoxLayout(headers_tab)
        self.headers_input = QTextEdit()
        self.headers_input.setPlaceholderText('{\n    "Content-Type": "application/json",\n    "Authorization": "Bearer YOUR_TOKEN"\n}')
        headers_layout.addWidget(self.headers_input)
        
        # Query Params tab
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)
        self.params_input = QTextEdit()
        self.params_input.setPlaceholderText('{\n    "page": 1,\n    "limit": 10\n}')
        params_layout.addWidget(self.params_input)
        
        # Request Body tab
        body_tab = QWidget()
        body_layout = QVBoxLayout(body_tab)
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText('{\n    "name": "Example",\n    "description": "This is a test"\n}')
        body_layout.addWidget(self.body_input)
        
        request_details_tabs.addTab(headers_tab, "Headers")
        request_details_tabs.addTab(params_tab, "Query Params")
        request_details_tabs.addTab(body_tab, "Request Body")
        
        layout.addWidget(request_details_tabs)
        
        # Send button
        self.send_btn = QPushButton("Send Request")
        self.send_btn.clicked.connect(self.send_request)
        layout.addWidget(self.send_btn)
    
    def setup_response_tab(self):
        layout = QVBoxLayout(self.response_tab)
        
        # Status and timing info
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Status: -")
        self.time_label = QLabel("Time: -")
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.time_label)
        
        layout.addLayout(status_layout)
        
        # Response headers
        self.response_headers_label = QLabel("Response Headers:")
        layout.addWidget(self.response_headers_label)
        
        self.response_headers = QTextEdit()
        self.response_headers.setReadOnly(True)
        self.response_headers.setMaximumHeight(100)
        layout.addWidget(self.response_headers)
        
        # Response body
        self.response_body_label = QLabel("Response Body:")
        layout.addWidget(self.response_body_label)
        
        self.response_body = QTextEdit()
        self.response_body.setReadOnly(True)
        layout.addWidget(self.response_body)
        
        # Copy response button
        self.copy_response_btn = QPushButton("Copy Response")
        self.copy_response_btn.clicked.connect(self.copy_response)
        layout.addWidget(self.copy_response_btn)
    
    def setup_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        
        # Form layout for config options
        form_layout = QFormLayout()
        
        # Integration name
        self.integration_name = QLineEdit()
        form_layout.addRow("Integration Name:", self.integration_name)
        
        # Base URL
        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("https://api.example.com")
        self.base_url.textChanged.connect(self.base_url_changed)
        form_layout.addRow("Base URL:", self.base_url)
        
        # Authentication section
        auth_label = QLabel("Authentication")
        auth_label.setFont(QFont("Arial", 10, QFont.Bold))
        form_layout.addRow(auth_label)
        
        # Auth type
        self.auth_type = QComboBox()
        self.auth_type.addItems(["None", "API Key", "Bearer Token", "Basic Auth", "OAuth 2.0"])
        self.auth_type.currentTextChanged.connect(self.auth_type_changed)
        form_layout.addRow("Auth Type:", self.auth_type)
        
        # Auth fields
        self.auth_fields = QWidget()
        self.auth_fields_layout = QFormLayout(self.auth_fields)
        form_layout.addRow(self.auth_fields)
        
        # Rate limiting
        rate_label = QLabel("Rate Limiting")
        rate_label.setFont(QFont("Arial", 10, QFont.Bold))
        form_layout.addRow(rate_label)
        
        self.rate_limit_enabled = QCheckBox("Enable Rate Limiting")
        form_layout.addRow(self.rate_limit_enabled)
        
        # Integration with main app
        integration_label = QLabel("Integration Settings")
        integration_label.setFont(QFont("Arial", 10, QFont.Bold))
        form_layout.addRow(integration_label)
        
        self.auto_update = QCheckBox("Auto-update products from API")
        form_layout.addRow(self.auto_update)
        
        self.update_frequency = QComboBox()
        self.update_frequency.addItems(["Daily", "Weekly", "On Demand"])
        form_layout.addRow("Update Frequency:", self.update_frequency)
        
        # Add form layout to main layout
        layout.addLayout(form_layout)
        
        # Save changes button
        self.save_config_btn = QPushButton("Save Configuration")
        self.save_config_btn.clicked.connect(self.save_configuration)
        layout.addWidget(self.save_config_btn)
        
        # Export/Import buttons
        buttons_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Export Configuration")
        self.export_btn.clicked.connect(self.export_configuration)
        
        self.import_btn = QPushButton("Import Configuration")
        self.import_btn.clicked.connect(self.import_configuration)
        
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addWidget(self.import_btn)
        
        layout.addLayout(buttons_layout)
        
        # Stretch to push everything up
        layout.addStretch(1)
    
    def load_endpoints(self):
        """Load endpoints from API configuration"""
        self.endpoints_table.setRowCount(0)
        
        # Check if we have endpoints
        if "endpoints" not in self.api_config:
            self.api_config["endpoints"] = []
        
        # Add endpoints to table
        for i, endpoint in enumerate(self.api_config["endpoints"]):
            self.endpoints_table.insertRow(i)
            
            # Method
            method_item = QTableWidgetItem(endpoint.get("method", "GET"))
            method_item.setTextAlignment(Qt.AlignCenter)
            self.endpoints_table.setItem(i, 0, method_item)
            
            # Path
            path_item = QTableWidgetItem(endpoint.get("path", ""))
            self.endpoints_table.setItem(i, 1, path_item)
            
            # Color the row based on method
            self.color_row_by_method(i, endpoint.get("method", "GET"))
    
    def color_row_by_method(self, row, method):
        """Apply color to a row based on the HTTP method"""
        colors = {
            "GET": QColor(240, 255, 240),  # Light green
            "POST": QColor(255, 240, 240),  # Light red
            "PUT": QColor(240, 240, 255),  # Light blue
            "DELETE": QColor(255, 240, 255),  # Light purple
            "PATCH": QColor(255, 255, 240),  # Light yellow
        }
        
        color = colors.get(method, QColor(255, 255, 255))  # Default white
        
        for col in range(self.endpoints_table.columnCount()):
            item = self.endpoints_table.item(row, col)
            if item:
                item.setBackground(color)
    
    def filter_endpoints(self):
        """Filter endpoints based on search text"""
        search_text = self.search_box.text().lower()
        
        for row in range(self.endpoints_table.rowCount()):
            path_item = self.endpoints_table.item(row, 1)
            method_item = self.endpoints_table.item(row, 0)
            
            if path_item and method_item:
                path = path_item.text().lower()
                method = method_item.text().lower()
                
                if search_text in path or search_text in method:
                    self.endpoints_table.setRowHidden(row, False)
                else:
                    self.endpoints_table.setRowHidden(row, True)
    
    def endpoint_selected(self, row, column):
        """Handle endpoint selection"""
        method_item = self.endpoints_table.item(row, 0)
        path_item = self.endpoints_table.item(row, 1)
        
        if method_item and path_item:
            method = method_item.text()
            path = path_item.text()
            
            # Find the endpoint in our config
            for endpoint in self.api_config["endpoints"]:
                if endpoint.get("method") == method and endpoint.get("path") == path:
                    self.current_endpoint = endpoint
                    self.load_endpoint_details()
                    break
    
    def load_endpoint_details(self):
        """Load selected endpoint details into form"""
        if not self.current_endpoint:
            return
        
        # Update request tab
        self.method_combo.setCurrentText(self.current_endpoint.get("method", "GET"))
        
        # Combine base URL and path
        base_url = self.api_config.get("base_url", "")
        path = self.current_endpoint.get("path", "")
        full_url = base_url + path if base_url and not path.startswith("http") else path
        self.url_input.setText(full_url)
        
        # Set headers, params, body
        self.headers_input.setText(json.dumps(self.current_endpoint.get("headers", {}), indent=4))
        self.params_input.setText(json.dumps(self.current_endpoint.get("params", {}), indent=4))
        self.body_input.setText(json.dumps(self.current_endpoint.get("body", {}), indent=4))
        
        # Switch to request tab
        self.tabs.setCurrentIndex(0)
        
        # Clear response tab
        self.status_label.setText("Status: -")
        self.time_label.setText("Time: -")
        self.response_headers.setText("")
        self.response_body.setText("")
    
    def add_new_endpoint(self):
        """Add a new endpoint"""
        # Create a new endpoint
        new_endpoint = {
            "method": "GET",
            "path": "/new-endpoint",
            "headers": {},
            "params": {},
            "body": {}
        }
        
        # Add to config
        self.api_config["endpoints"].append(new_endpoint)
        
        # Add to table
        row = self.endpoints_table.rowCount()
        self.endpoints_table.insertRow(row)
        
        # Method
        method_item = QTableWidgetItem(new_endpoint["method"])
        method_item.setTextAlignment(Qt.AlignCenter)
        self.endpoints_table.setItem(row, 0, method_item)
        
        # Path
        path_item = QTableWidgetItem(new_endpoint["path"])
        self.endpoints_table.setItem(row, 1, path_item)
        
        # Color the row
        self.color_row_by_method(row, new_endpoint["method"])
        
        # Select the new endpoint
        self.endpoints_table.selectRow(row)
        self.current_endpoint = new_endpoint
        self.load_endpoint_details()
    
    def send_request(self):
        """Send a request to the API endpoint"""
        if self.request_thread and self.request_thread.isRunning():
            QMessageBox.warning(self, "Request in Progress", "A request is already in progress. Please wait.")
            return
        
        # Get request details
        method = self.method_combo.currentText()
        url = self.url_input.text()
        
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a URL for the request.")
            return
        
        # Get headers, params, body
        headers_text = self.headers_input.toPlainText()
        params_text = self.params_input.toPlainText()
        body_text = self.body_input.toPlainText()
        
        # Update UI
        self.send_btn.setText("Sending...")
        self.send_btn.setEnabled(False)
        self.tabs.setCurrentIndex(1)  # Switch to response tab
        
        # Create request thread
        self.request_thread = ApiRequestThread(
            method=method,
            url=url,
            headers=headers_text,
            params=params_text,
            data=body_text
        )
        
        # Connect signals
        self.request_thread.result_ready.connect(self.handle_response)
        self.request_thread.error_occurred.connect(self.handle_error)
        self.request_thread.finished.connect(self.request_finished)
        
        # Start thread
        self.request_thread.start()
    
    def handle_response(self, result):
        """Handle API response"""
        # Update status
        self.status_label.setText(f"Status: {result['status_code']}")
        self.time_label.setText(f"Time: {result['elapsed']:.2f}s")
        
        # Update headers
        headers_text = json.dumps(result["headers"], indent=4)
        self.response_headers.setText(headers_text)
        
        # Update body
        if "json_response" in result and result["json_response"] is not None:
            body_text = json.dumps(result["json_response"], indent=4)
        else:
            body_text = result["raw_response"]
        
        self.response_body.setText(body_text)
        
        # Colorize based on status code
        status_code = result["status_code"]
        if 200 <= status_code < 300:
            # Success - green
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        elif 300 <= status_code < 400:
            # Redirect - blue
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        elif 400 <= status_code < 500:
            # Client error - orange
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif 500 <= status_code < 600:
            # Server error - red
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            # Unknown - black
            self.status_label.setStyleSheet("color: black; font-weight: bold;")
    
    def handle_error(self, error_message):
        """Handle API request error"""
        self.status_label.setText("Status: Error")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.time_label.setText("Time: -")
        self.response_headers.setText("")
        self.response_body.setText(error_message)
        
        QMessageBox.critical(self, "Request Error", error_message)
    
    def request_finished(self):
        """Called when the request thread finishes"""
        self.send_btn.setText("Send Request")
        self.send_btn.setEnabled(True)
    
    def copy_response(self):
        """Copy response to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.response_body.toPlainText())
        
        QMessageBox.information(self, "Copied", "Response copied to clipboard.")
    
    def method_changed(self, method):
        """Handle method change - update current endpoint"""
        if self.current_endpoint:
            self.current_endpoint["method"] = method
            
            # Update table
            selected_rows = self.endpoints_table.selectedItems()
            if selected_rows:
                row = selected_rows[0].row()
                
                # Update method cell
                method_item = QTableWidgetItem(method)
                method_item.setTextAlignment(Qt.AlignCenter)
                self.endpoints_table.setItem(row, 0, method_item)
                
                # Update row color
                self.color_row_by_method(row, method)
    
    def url_changed(self, url):
        """Handle URL change - update current endpoint"""
        if self.current_endpoint:
            # Check if base URL is part of the URL
            base_url = self.api_config.get("base_url", "")
            
            if base_url and url.startswith(base_url):
                # Remove base URL to get path
                path = url[len(base_url):]
                self.current_endpoint["path"] = path
            else:
                # Just use the whole URL as path
                self.current_endpoint["path"] = url
            
            # Update table
            selected_rows = self.endpoints_table.selectedItems()
            if selected_rows:
                row = selected_rows[0].row()
                path_item = QTableWidgetItem(self.current_endpoint["path"])
                self.endpoints_table.setItem(row, 1, path_item)
    
    def base_url_changed(self, base_url):
        """Handle base URL change"""
        self.api_config["base_url"] = base_url
        
        # If we have a current endpoint, update the URL field
        if self.current_endpoint:
            path = self.current_endpoint.get("path", "")
            if not path.startswith("http"):
                self.url_input.setText(base_url + path)
    
    def auth_type_changed(self, auth_type):
        """Handle auth type change - update auth fields"""
        # Clear existing auth fields
        while self.auth_fields_layout.count():
            item = self.auth_fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add fields based on auth type
        if auth_type == "API Key":
            self.auth_key_name = QLineEdit()
            self.auth_key_name.setPlaceholderText("X-API-Key")
            self.auth_fields_layout.addRow("Key Name:", self.auth_key_name)
            
            self.auth_key_value = QLineEdit()
            self.auth_key_value.setPlaceholderText("your-api-key")
            self.auth_fields_layout.addRow("Key Value:", self.auth_key_value)
            
            self.auth_key_location = QComboBox()
            self.auth_key_location.addItems(["Header", "Query Parameter"])
            self.auth_fields_layout.addRow("Key Location:", self.auth_key_location)
            
        elif auth_type == "Bearer Token":
            self.auth_token = QLineEdit()
            self.auth_token.setPlaceholderText("your-token")
            self.auth_fields_layout.addRow("Token:", self.auth_token)
            
        elif auth_type == "Basic Auth":
            self.auth_username = QLineEdit()
            self.auth_username.setPlaceholderText("username")
            self.auth_fields_layout.addRow("Username:", self.auth_username)
            
            self.auth_password = QLineEdit()
            self.auth_password.setPlaceholderText("password")
            self.auth_password.setEchoMode(QLineEdit.Password)
            self.auth_fields_layout.addRow("Password:", self.auth_password)
            
        elif auth_type == "OAuth 2.0":
            self.auth_client_id = QLineEdit()
            self.auth_client_id.setPlaceholderText("client-id")
            self.auth_fields_layout.addRow("Client ID:", self.auth_client_id)
            
            self.auth_client_secret = QLineEdit()
            self.auth_client_secret.setPlaceholderText("client-secret")
            self.auth_client_secret.setEchoMode(QLineEdit.Password)
            self.auth_fields_layout.addRow("Client Secret:", self.auth_client_secret)
            
            self.auth_token_url = QLineEdit()
            self.auth_token_url.setPlaceholderText("https://api.example.com/oauth/token")
            self.auth_fields_layout.addRow("Token URL:", self.auth_token_url)
        
        # Update the auth type in config
        self.api_config["auth_type"] = auth_type
    
    def save_configuration(self):
        """Save configuration changes"""
        # Get basic config
        self.api_config["name"] = self.integration_name.text()
        self.api_config["base_url"] = self.base_url.text()
        self.api_config["auth_type"] = self.auth_type.currentText()
        
        # Get auth fields
        auth_type = self.auth_type.currentText()
        auth_config = {}
        
        if auth_type == "API Key":
            auth_config["key_name"] = getattr(self, "auth_key_name", QLineEdit()).text()
            auth_config["key_value"] = getattr(self, "auth_key_value", QLineEdit()).text()
            auth_config["key_location"] = getattr(self, "auth_key_location", QComboBox()).currentText()
            
        elif auth_type == "Bearer Token":
            auth_config["token"] = getattr(self, "auth_token", QLineEdit()).text()
            
        elif auth_type == "Basic Auth":
            auth_config["username"] = getattr(self, "auth_username", QLineEdit()).text()
            auth_config["password"] = getattr(self, "auth_password", QLineEdit()).text()
            
        elif auth_type == "OAuth 2.0":
            auth_config["client_id"] = getattr(self, "auth_client_id", QLineEdit()).text()
            auth_config["client_secret"] = getattr(self, "auth_client_secret", QLineEdit()).text()
            auth_config["token_url"] = getattr(self, "auth_token_url", QLineEdit()).text()
        
        self.api_config["auth_config"] = auth_config
        
        # Get rate limiting and integration settings
        self.api_config["rate_limiting"] = {
            "enabled": self.rate_limit_enabled.isChecked()
        }
        
        self.api_config["integration"] = {
            "auto_update": self.auto_update.isChecked(),
            "update_frequency": self.update_frequency.currentText()
        }
        
        QMessageBox.information(self, "Configuration Saved", "API configuration has been saved.")
    
    def export_configuration(self):
        """Export configuration to JSON file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.api_config, f, indent=4)
                
                QMessageBox.information(self, "Export Successful", f"Configuration exported to {file_path}.")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export configuration: {str(e)}")
    
    def import_configuration(self):
        """Import configuration from JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, "r") as f:
                    imported_config = json.loads(f.read())
                
                # Validate the imported config
                if "endpoints" not in imported_config:
                    raise ValueError("Invalid configuration: missing 'endpoints' key")
                
                # Update our config
                self.api_config.update(imported_config)
                
                # Reload UI
                self.load_endpoints()
                
                # Update config tab
                self.integration_name.setText(self.api_config.get("name", ""))
                self.base_url.setText(self.api_config.get("base_url", ""))
                self.auth_type.setCurrentText(self.api_config.get("auth_type", "None"))
                
                # Trigger auth type changed to update fields
                self.auth_type_changed(self.auth_type.currentText())
                
                # Load auth config
                auth_config = self.api_config.get("auth_config", {})
                auth_type = self.api_config.get("auth_type", "None")
                
                if auth_type == "API Key" and hasattr(self, "auth_key_name"):
                    self.auth_key_name.setText(auth_config.get("key_name", ""))
                    self.auth_key_value.setText(auth_config.get("key_value", ""))
                    index = self.auth_key_location.findText(auth_config.get("key_location", "Header"))
                    if index >= 0:
                        self.auth_key_location.setCurrentIndex(index)
                
                elif auth_type == "Bearer Token" and hasattr(self, "auth_token"):
                    self.auth_token.setText(auth_config.get("token", ""))
                
                elif auth_type == "Basic Auth" and hasattr(self, "auth_username"):
                    self.auth_username.setText(auth_config.get("username", ""))
                    self.auth_password.setText(auth_config.get("password", ""))
                
                elif auth_type == "OAuth 2.0" and hasattr(self, "auth_client_id"):
                    self.auth_client_id.setText(auth_config.get("client_id", ""))
                    self.auth_client_secret.setText(auth_config.get("client_secret", ""))
                    self.auth_token_url.setText(auth_config.get("token_url", ""))
                
                # Load rate limiting and integration settings
                rate_limiting = self.api_config.get("rate_limiting", {})
                self.rate_limit_enabled.setChecked(rate_limiting.get("enabled", False))
                
                integration = self.api_config.get("integration", {})
                self.auto_update.setChecked(integration.get("auto_update", False))
                
                update_frequency = integration.get("update_frequency", "On Demand")
                index = self.update_frequency.findText(update_frequency)
                if index >= 0:
                    self.update_frequency.setCurrentIndex(index)
                
                QMessageBox.information(self, "Import Successful", "Configuration imported successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"Failed to import configuration: {str(e)}")
    
    def save_all_changes(self):
        """Save all changes including current endpoint details"""
        if self.current_endpoint:
            # Save request details
            headers_text = self.headers_input.toPlainText()
            params_text = self.params_input.toPlainText()
            body_text = self.body_input.toPlainText()
            
            try:
                self.current_endpoint["headers"] = json.loads(headers_text) if headers_text.strip() else {}
            except:
                QMessageBox.warning(self, "Invalid JSON", "Headers contain invalid JSON.")
                return
                
            try:
                self.current_endpoint["params"] = json.loads(params_text) if params_text.strip() else {}
            except:
                QMessageBox.warning(self, "Invalid JSON", "Query parameters contain invalid JSON.")
                return
                
            try:
                self.current_endpoint["body"] = json.loads(body_text) if body_text.strip() else {}
            except:
                QMessageBox.warning(self, "Invalid JSON", "Request body contains invalid JSON.")
                return
        
        # Save configuration
        self.save_configuration()
        
        # Notify parent to save to file
        self.parent().save_api_config(self.api_config)


class Plugin:
    """Plugin that adds API manager functionality to the MK Processor application"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.name = "API Manager"
        self.version = "1.0.0"
        self.description = "Manage API integrations for product data retrieval"
        self.button = None
        self.api_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_config.json')
        self.api_config = self.load_api_config()
    
    def load_api_config(self):
        """Load API configuration from file"""
        if os.path.exists(self.api_config_file):
            try:
                with open(self.api_config_file, 'r') as f:
                    return json.load(f)
            except:
                # Return default config if file exists but has invalid JSON
                return {"endpoints": [], "base_url": "", "auth_type": "None", "auth_config": {}}
        else:
            # Return default config if file doesn't exist
            return {"endpoints": [], "base_url": "", "auth_type": "None", "auth_config": {}}
    
    def save_api_config(self, config):
        """Save API configuration to file"""
        try:
            with open(self.api_config_file, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"API configuration saved to {self.api_config_file}")
            self.api_config = config
            return True
        except Exception as e:
            print(f"Error saving API configuration: {e}")
            print(traceback.format_exc())
            return False
    
    def initialize(self):
        """Called when the plugin is loaded"""
        print(f"DEBUG: Initializing {self.name} v{self.version}")
        
        # Check if button already exists
        if hasattr(self, 'button') and self.button is not None:
            print(f"DEBUG: Button already exists for {self.name}, skipping")
            return
            
        # Create a simple button
        self.button = QPushButton("API Manager", self.main_window)
        self.button.setObjectName("secondaryButton")
        # Use lambda to avoid method reference issues
        self.button.clicked.connect(lambda: self.on_button_clicked())
        
        # Find button layout
        button_layout = None
        for i in range(self.main_window.layout().count()):
            item = self.main_window.layout().itemAt(i)
            if item and item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QPushButton):
                        # Found a layout with buttons
                        button_layout = item.layout()
                        break
                if button_layout:
                    break
                    
        if button_layout:
            # Check for existing buttons
            button_exists = False
            for i in range(button_layout.count()):
                widget = button_layout.itemAt(i).widget()
                if isinstance(widget, QPushButton) and widget.text() == "API Manager":
                    button_exists = True
                    self.button = widget  # Use existing button
                    self.button.clicked.disconnect()  # Disconnect any existing connections
                    self.button.clicked.connect(lambda: self.on_button_clicked())
                    print(f"DEBUG: Reconnected existing button")
                    break
                    
            if not button_exists:
                button_layout.addWidget(self.button)
                print(f"DEBUG: Added new button to layout")
        else:
            print("DEBUG: Could not find button layout")
    
    def on_button_clicked(self):
        """Handle the button click event"""
        print("DEBUG: API Manager button clicked!")
        try:
            dialog = ApiTestingDialog(self.api_config, self.main_window)
            result = dialog.exec_()
            print(f"DEBUG: Dialog closed with result: {result}")
            if result:
                self.save_api_config(dialog.api_config)
        except Exception as e:
            print(f"ERROR: Exception in button click handler: {e}")
            print(traceback.format_exc())
            QMessageBox.critical(self.main_window, "Error", f"Failed to open API Manager: {str(e)}")
    
    def hide_ui(self):
        """Hide UI elements when plugin is set to not show in UI"""
        if self.button and self.button.isVisible():
            self.button.setVisible(False)
            print(f"DEBUG: Hid button for {self.name}")

    def cleanup(self):
        """Called when the plugin is disabled or unloaded"""
        if self.button and self.button.parent():
            # Remove the button from its parent layout
            parent_layout = self.button.parent().layout()
            if parent_layout:
                parent_layout.removeWidget(self.button)
                self.button.deleteLater()
                self.button = None
                print(f"DEBUG: Cleaned up button for {self.name}")
    
    def get_headers_for_endpoint(self, endpoint_path, method="GET"):
        """Get headers for a specific endpoint"""
        # Add auth headers based on auth type
        headers = {}
        
        auth_type = self.api_config.get("auth_type", "None")
        auth_config = self.api_config.get("auth_config", {})
        
        if auth_type == "API Key" and auth_config.get("key_location") == "Header":
            headers[auth_config.get("key_name", "X-API-Key")] = auth_config.get("key_value", "")
            
        elif auth_type == "Bearer Token":
            headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
            
        elif auth_type == "Basic Auth":
            import base64
            username = auth_config.get("username", "")
            password = auth_config.get("password", "")
            auth_string = f"{username}:{password}"
            encoded = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        
        # Add endpoint-specific headers
        for endpoint in self.api_config.get("endpoints", []):
            if endpoint.get("path") == endpoint_path and endpoint.get("method") == method:
                endpoint_headers = endpoint.get("headers", {})
                headers.update(endpoint_headers)
                break
        
        return headers
    
    def make_api_request(self, endpoint_path, method="GET", params=None, data=None):
        """Make an API request to a specific endpoint"""
        # Find the endpoint in config
        endpoint = None
        for ep in self.api_config.get("endpoints", []):
            if ep.get("path") == endpoint_path and ep.get("method") == method:
                endpoint = ep
                break
        
        if not endpoint:
            raise ValueError(f"Endpoint not found: {method} {endpoint_path}")
        
        # Build the URL
        base_url = self.api_config.get("base_url", "")
        url = base_url + endpoint_path if base_url and not endpoint_path.startswith("http") else endpoint_path
        
        # Get headers
        headers = self.get_headers_for_endpoint(endpoint_path, method)
        
        # Get params (merge provided params with endpoint params)
        merged_params = {}
        merged_params.update(endpoint.get("params", {}))
        if params:
            merged_params.update(params)
            
        # Handle auth params
        auth_type = self.api_config.get("auth_type", "None")
        auth_config = self.api_config.get("auth_config", {})
        
        if auth_type == "API Key" and auth_config.get("key_location") == "Query Parameter":
            merged_params[auth_config.get("key_name", "api_key")] = auth_config.get("key_value", "")
        
        # Get data (merge provided data with endpoint data)
        merged_data = {}
        merged_data.update(endpoint.get("body", {}))
        if data:
            merged_data.update(data)
        
        # Make the request
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=merged_params,
                json=merged_data if merged_data else None,
                timeout=30
            )
            
            # Try to parse JSON response
            if "application/json" in response.headers.get("Content-Type", "") or response.text.strip().startswith("{") or response.text.strip().startswith("["):
                try:
                    return response.json()
                except:
                    return response.text
            else:
                return response.text
                
        except Exception as e:
            print(f"API request error: {e}")
            print(traceback.format_exc())
            raise
    
    # Hook for integration with file processing
    def before_process_file(self, sheet_row, file_info):
        """Hook to potentially fetch additional data from API before processing a file"""
        # Example: Check if auto-update is enabled
        if self.api_config.get("integration", {}).get("auto_update", False):
            try:
                # You could fetch updates for models in the file
                # This is just an example - you'd need to implement logic specific to your needs
                pass
            except Exception as e:
                print(f"API integration error: {e}")
                print(traceback.format_exc())
        
        return True
