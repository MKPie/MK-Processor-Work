#!/usr/bin/env python3
import sys, os, json, time, threading
import traceback

# Add debug logging
print("Starting script...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

try:
    print("Importing pandas...")
    import pandas as pd
    print("Importing gspread...")
    import gspread
    print("Importing base64...")
    import base64
    print("Importing PyQt5 components...")
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
        QProgressBar, QScrollArea, QFrame, QMessageBox, QSplashScreen
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QPropertyAnimation, QEasingCurve
    from PyQt5.QtGui import QFont, QMovie, QPixmap, QIcon
    print("Importing web components...")
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWebChannel import QWebChannel
    print("Importing Google auth...")
    from oauth2client.service_account import ServiceAccountCredentials
    print("Importing Selenium...")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import NoSuchElementException
    print("Importing UserAgent...")
    from fake_useragent import UserAgent
    
    print("All imports successful!")
except Exception as e:
    print(f"Error during imports: {e}")
    traceback.print_exc()
    with open('/home/mkpie/GoogleSheetsProcessor/error_log.txt', 'w') as f:
        f.write(f"Import Error: {str(e)}\n")
        f.write(traceback.format_exc())
    sys.exit(1)

# Worker signals for threaded operations
class WorkerSignals(QObject):
    progress = pyqtSignal(int, int, int)  # current, total, percentage
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    log = pyqtSignal(str)

print("Defined WorkerSignals class")

class SheetProcessor(QWidget):
    def __init__(self):
        print("Initializing SheetProcessor...")
        super().__init__()
        self.setWindowTitle("Google Sheets Processor 3.0.2")
        self.setGeometry(100, 100, 1000, 750)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 8px;
                background-color: #fff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4285f4;
            }
            QPushButton {
                border-radius: 20px;
                padding: 10px 15px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #f5f5f5;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4285f4;
                border-radius: 5px;
            }
        """)
        self.rows = []
        self.active_index = -1
        self.processing = False
        print("Setting up UI...")
        self.init_ui()
        try:
            print("Attempting Google Drive authentication...")
            self.auth = self.authenticate_google_drive()
            print("Google Drive authentication successful!")
        except Exception as e:
            print(f"Google Drive Auth Failed: {e}")
            traceback.print_exc()
            self.show_error(f"Google Drive Auth Failed: {e}")

    def init_ui(self):
        print("Inside init_ui method")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header with simple title
        header_layout = QHBoxLayout()
        
        # Title and status
        title_layout = QVBoxLayout()
        title_layout.setSpacing(10)
        
        header = QLabel("Google Sheets Processor")
        header.setFont(QFont("Arial", 24, QFont.Bold))
        header.setStyleSheet("color: #333; margin-bottom: 5px;")
        header.setAlignment(Qt.AlignCenter)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 14))
        self.status_label.setStyleSheet("color: #0f9d58; margin-bottom: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Current processing info
        self.processing_info = QLabel("")
        self.processing_info.setFont(QFont("Arial", 12))
        self.processing_info.setStyleSheet("color: #4285f4;")
        self.processing_info.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(header)
        title_layout.addWidget(self.status_label)
        title_layout.addWidget(self.processing_info)
        
        header_layout.addLayout(title_layout, 1)
        layout.addLayout(header_layout)

        # Control buttons
        top_controls = QHBoxLayout()
        top_controls.setSpacing(15)
        
        self.start_all_btn = QPushButton("Start All")
        self.start_all_btn.clicked.connect(self.start_all)
        self.stop_all_btn = QPushButton("Stop")
        self.stop_all_btn.clicked.connect(self.stop_all)
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        
        for btn in [self.start_all_btn, self.stop_all_btn, self.clear_btn]:
            btn.setFixedHeight(50)
            btn.setFont(QFont("Arial", 14, QFont.Bold))
            if btn == self.start_all_btn:
                btn.setStyleSheet("background-color: #0f9d58;")
            elif btn == self.stop_all_btn:
                btn.setStyleSheet("background-color: #db4437;")
            else:
                btn.setStyleSheet("background-color: #4285f4;")
            top_controls.addWidget(btn)
            
        layout.addLayout(top_controls)

        # Main scrollable area for sheet rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
            }
        """)
        
        self.container = QVBoxLayout()
        self.container.setAlignment(Qt.AlignTop)
        self.container.setSpacing(10)
        self.container.setContentsMargins(10, 10, 10, 10)

        container_widget = QWidget()
        container_widget.setLayout(self.container)
        self.scroll_area.setWidget(container_widget)

        layout.addWidget(self.scroll_area)

        # Add new sheet button
        add_btn = QPushButton("+ Add Sheet")
        add_btn.clicked.connect(self.add_row)
        add_btn.setFixedHeight(50)
        add_btn.setFont(QFont("Arial", 14, QFont.Bold))
        add_btn.setStyleSheet("background-color: #0f9d58;")
        layout.addWidget(add_btn)
        
        self.setLayout(layout)
        print("UI setup complete")

    def authenticate_google_drive(self):
        print("Authenticating Google Drive...")
        creds_path = os.path.expanduser("~/GoogleDriveMount/Web/zapier-454818-4e4abf368f57.json")
        print(f"Looking for credentials at: {creds_path}")
        
        if not os.path.exists(creds_path):
            print(f"ERROR: Credentials file not found at {creds_path}")
            raise FileNotFoundError(f"Credentials file not found at {creds_path}")
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        return client
        
    def update_processing_info(self, current_row=None, total_rows=None, filename=None):
        """Update the processing information display"""
        if not filename and not current_row:
            self.processing_info.setText("")
            return
            
        if filename and current_row and total_rows:
            self.processing_info.setText(f"Processing: {filename} - Row {current_row} of {total_rows} ({int((current_row/total_rows)*100)}% complete)")
        elif filename:
            self.processing_info.setText(f"Processing: {filename}")
        elif current_row and total_rows:
            self.processing_info.setText(f"Row {current_row} of {total_rows} ({int((current_row/total_rows)*100)}% complete)")

    def add_row(self):
        print("Adding new row...")
        row = SheetRow(len(self.rows), self)
        self.rows.append(row)
        self.container.addWidget(row)
        print("Row added")

    def start_all(self):
        print("Start All button clicked")
        if self.processing:
            print("Already processing, ignoring")
            return
            
        # Validate that there are rows to process
        valid_rows = [row for row in self.rows if row.filename_input.text().strip()]
        if not valid_rows:
            print("No valid rows to process")
            QMessageBox.warning(self, "No Sheets", "Please add at least one sheet to process")
            return
            
        self.processing = True
        self.status_label.setText("Processing...")
        self.status_label.setStyleSheet("color: #f4b400;")
        self.start_all_btn.setEnabled(False)
        self.stop_all_btn.setEnabled(True)
        
        # Start from the first row
        self.active_index = 0
        print("Starting to process rows")
        self.process_next()

    def process_next(self):
        print(f"Processing next row, active_index = {self.active_index}")
        if self.active_index >= len(self.rows):
            print("All rows processed")
            self.processing = False
            self.status_label.setText("Completed")
            self.status_label.setStyleSheet("color: #0f9d58;")
            self.start_all_btn.setEnabled(True)
            self.stop_all_btn.setEnabled(False)
            self.update_processing_info()
            return
            
        row = self.rows[self.active_index]
        
        # Skip rows with empty inputs
        if not row.filename_input.text().strip():
            print(f"Skipping empty row at index {self.active_index}")
            self.active_index += 1
            self.process_next()
            return
            
        if not row.completed:
            # Update processing info
            sheet_name = row.filename_input.text()
            print(f"Starting to process sheet: {sheet_name}")
            self.update_processing_info(filename=sheet_name)
            row.start()
            QTimer.singleShot(1000, self.wait_for_row)
        else:
            print(f"Row {self.active_index} already completed, moving to next")
            self.active_index += 1
            self.process_next()

    def wait_for_row(self):
        if self.active_index >= len(self.rows):
            print("No more rows to wait for")
            return
            
        if not self.rows[self.active_index].completed:
            print(f"Row {self.active_index} still processing, waiting...")
            QTimer.singleShot(500, self.wait_for_row)
        else:
            print(f"Row {self.active_index} completed, moving to next")
            self.active_index += 1
            self.process_next()

    def stop_all(self):
        print("Stop All button clicked")
        if not self.processing:
            print("Not processing, nothing to stop")
            return
            
        for row in self.rows:
            row.stop()
            
        self.processing = False
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("color: #db4437;")
        self.start_all_btn.setEnabled(True)
        self.stop_all_btn.setEnabled(False)
        self.update_processing_info()
        print("All processing stopped")

    def clear_all(self):
        print("Clear All button clicked")
        # Confirm if processing is currently running
        if self.processing:
            print("Processing is running, asking for confirmation")
            reply = QMessageBox.question(
                self, "Confirm Clear", 
                "Processing is currently running. Are you sure you want to clear all sheets?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                print("Clear cancelled by user")
                return
            
            # Stop all processing first
            print("Stopping all processing before clearing")
            self.stop_all()
        
        # Clear all rows
        print("Clearing all rows")
        for i in reversed(range(self.container.count())):
            widget = self.container.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        self.rows.clear()
        self.processing = False
        self.active_index = -1
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #0f9d58;")
        self.update_processing_info()
        
        # Add a default empty row
        print("Adding a default empty row")
        self.add_row()
        print("Clear All completed")

    def show_error(self, message):
        print(f"ERROR: {message}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.exec()

class SheetRow(QFrame):
    def __init__(self, index, parent):
        print(f"Initializing SheetRow {index}")
        super().__init__()
        self.index = index
        self.parent = parent
        self.thread = None
        self.running = False
        self.completed = False
        self.signals = WorkerSignals()
        self.output_df = None
        self.output_path = None
        self.model_column = None
        
        # Connect signals
        self.signals.progress.connect(self.update_progress)
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white; 
                border-radius: 12px; 
                padding: 15px;
                border: 1px solid #e0e0e0;
            }
            QFrame:hover {
                border: 1px solid #4285f4;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
        """)
        self.init_ui()
        print(f"SheetRow {index} initialized")

    def init_ui(self):
        print(f"Setting up UI for SheetRow {self.index}")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Main input row
        row_layout = QHBoxLayout()
        row_layout.setSpacing(15)

        # Sheet name input with label
        sheet_layout = QVBoxLayout()
        sheet_layout.setSpacing(5)
        
        # Sheet name input
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Enter Google Sheet Name")
        self.filename_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 12px;
                background-color: #fff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4285f4;
            }
        """)
        sheet_layout.addWidget(self.filename_input)
        
        # Prefix input with label
        prefix_layout = QVBoxLayout()
        prefix_layout.setSpacing(5)
        
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("Enter Katom Prefix")
        self.prefix_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 12px;
                background-color: #fff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4285f4;
            }
        """)
        prefix_layout.addWidget(self.prefix_input)
        
        # Add components to the main row layout
        row_layout.addLayout(sheet_layout, 3)
        row_layout.addLayout(prefix_layout, 2)

        # Progress section
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        
        # Status info label
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Arial", 12))
        self.info_label.setStyleSheet("color: #666;")
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setMinimumHeight(25)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 12px;
                background-color: #f5f5f5;
                text-align: center;
                font-weight: bold;
                color: #333;
            }
            QProgressBar::chunk {
                background-color: #4285f4;
                border-radius: 12px;
            }
        """)
        
        progress_layout.addWidget(self.info_label, 1)
        progress_layout.addWidget(self.progress, 2)

        # Add everything to the main layout
        layout.addLayout(row_layout)
        layout.addLayout(progress_layout)
        self.setLayout(layout)
        print(f"UI setup complete for SheetRow {self.index}")
        
    def update_progress(self, current, total, percent):
        """Update progress bar and info label"""
        print(f"Updating progress: row {current}/{total} - {percent}%")
        self.progress.setValue(percent)
        self.info_label.setText(f"Processing row {current} of {total} - {percent}% complete")
        self.parent.update_processing_info(current, total, self.filename_input.text())
    
    def detect_model_column(self, df):
        """Automatically detect the column that contains model numbers"""
        print("Detecting model column")
        # Try to find a column with "model" in the name
        model_columns = [col for col in df.columns if "model" in col.lower()]
        if model_columns:
            print(f"Found model column by name 'model': {model_columns[0]}")
            return model_columns[0]  # Return the first match
            
        # Try to find a column with "mfr" in the name
        mfr_columns = [col for col in df.columns if "mfr" in col.lower()]
        if mfr_columns:
            print(f"Found model column by name 'mfr': {mfr_columns[0]}")
            return mfr_columns[0]  # Return the first match
            
        # Try to find a column with "part" or "number" in the name
        part_columns = [col for col in df.columns if "part" in col.lower() or "number" in col.lower()]
        if part_columns:
            print(f"Found model column by name containing 'part' or 'number': {part_columns[0]}")
            return part_columns[0]  # Return the first match
            
        # If all else fails, return the first column that has alphanumeric values
        print("No named column found, looking for column with alphanumeric values")
        for col in df.columns:
            sample = df[col].dropna().head(5)
            if len(sample) > 0 and all(isinstance(val, str) or isinstance(val, (int, float)) for val in sample):
                print(f"Using column with alphanumeric values: {col}")
                return col
                
        # If still nothing found, return the first column
        if len(df.columns) > 0:
            print(f"No suitable column found, defaulting to first column: {df.columns[0]}")
            return df.columns[0]
            
        # No columns found
        print("ERROR: No columns found in dataframe")
        return None

    def start(self):
        print(f"Starting row {self.index}")
        if self.running:
            print("Already running, ignoring")
            return
        
        # Validate inputs
        sheet_name = self.filename_input.text().strip()
        prefix = self.prefix_input.text().strip()
        
        if not sheet_name or not prefix:
            print("Missing sheet name or prefix")
            QMessageBox.warning(self, "Missing Input", "Please provide both sheet name and prefix.")
            return
            
        self.running = True
        self.completed = False
        self.progress.setValue(0)
        
        # Start processing in a separate thread
        print(f"Starting thread for row {self.index}")
        self.thread = threading.Thread(target=self.process)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        print(f"Stopping row {self.index}")
        self.running = False
        self.completed = True
        self.info_label.setText("Stopped")
    
    def scrape_katom(self, model_number, prefix):
        print(f"Scraping Katom for model: {model_number}, prefix: {prefix}")
        model_number = ''.join(e for e in model_number if e.isalnum()).upper()
        if model_number.endswith("HC"):
            model_number = model_number[:-2]

        url = f"https://www.katom.com/{prefix}-{model_number}.html"
        print(f"🔍 Fetching: {url}")
        sys.stdout.flush()

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={UserAgent().random}')
        
        try:
            print("Starting Chrome WebDriver")
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"Error starting ChromeDriver: {e}")
            traceback.print_exc()
            return "Title not found", "Description not found"

        title, description = "Title not found", "Description not found"
        item_found = False

        try:
            print(f"Navigating to {url}")
            driver.get(url)
            
            # Check if we got a 404 or product not found page
            if "404" in driver.title or "not found" in driver.title.lower():
                print(f"⚠️ Product not found at {url}")
                return title, description
                
            try:
                # Wait for the product name to appear
                print("Waiting for product name to appear")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name.mb-0"))
                )
                
                title_element = driver.find_element(By.CSS_SELECTOR, "h1.product-name.mb-0")
                title = title_element.text.strip()
                if title:
                    item_found = True
                    print(f"Found title: {title[:30]}...")
            except Exception as title_error:
                print(f"⚠️ Title element not found at {url}: {title_error}")

            if item_found:
                try:
                    print("Looking for description")
                    tab_content = driver.find_element(By.CLASS_NAME, "tab-content")
                    paragraphs = tab_content.find_elements(By.TAG_NAME, "p")
                    filtered = [
                        f"<p>{p.text.strip()}</p>" for p in paragraphs
                        if p.text.strip() and not p.text.lower().startswith("*free") and "video" not in p.text.lower()
                    ]
                    description = "".join(filtered) if filtered else "Description not found"
                    print(f"Found description: {len(description)} characters")
                except NoSuchElementException as desc_error:
                    print(f"⚠️ Description (tab-content) not found at {url}: {desc_error}")

        except Exception as e:
            print(f"[Scrape Error] {url} – {e}")
            traceback.print_exc()

        finally:
            print("Closing Chrome WebDriver")
            driver.quit()

        return title, description

    def save_current_results(self):
        """Save the current results to the output file"""
        print(f"Saving current results to {self.output_path}")
        if self.output_df is not None and self.output_path is not None:
            try:
                self.output_df.to_excel(self.output_path, index=False)
                print(f"💾 Saved intermediate results to {self.output_path}")
                sys.stdout.flush()
            except Exception as e:
                print(f"Error saving intermediate results: {e}")
                traceback.print_exc()
                sys.stdout.flush()
        else:
            print("Nothing to save - output_df or output_path is None")

    def process(self):
        print(f"Starting process for row {self.index}")
        try:
            # Get input values
            sheet_name = self.filename_input.text().strip()
            prefix = self.prefix_input.text().strip()
            if not sheet_name or not prefix:
                raise ValueError("Missing sheet name or prefix")

            # Debug output
            print(f"Processing sheet: {sheet_name} with prefix: {prefix}")
            sys.stdout.flush()

            # Open the Google Sheet - Case insensitive search for the sheet
            try:
                # Get a list of all available sheets
                print("Getting list of available sheets")
                all_sheets = self.parent.auth.list_spreadsheet_files()
                print(f"Found {len(all_sheets)} sheets")
                
                # Look for a case-insensitive match
                sheet_id = None
                found_sheet_name = None
                for sheet_info in all_sheets:
                    if sheet_info['name'].lower() == sheet_name.lower():
                        sheet_id = sheet_info['id']
                        found_sheet_name = sheet_info['name']
                        print(f"Found matching sheet: {found_sheet_name} (ID: {sheet_id})")
                        break
                
                if not sheet_id:
                    print(f"Sheet '{sheet_name}' not found in available sheets")
                    raise ValueError(f"Sheet '{sheet_name}' not found")
                
                # Open the sheet using the ID
                print(f"Opening sheet with ID: {sheet_id}")
                sheet = self.parent.auth.open_by_key(sheet_id)
                records = sheet.sheet1.get_all_records()
                df = pd.DataFrame(records)
                print(f"Sheet loaded with {len(df)} rows and {len(df.columns)} columns")
                print(f"Column names: {df.columns.tolist()}")
                
                # Use the found sheet name with original case for output
                sheet_name = found_sheet_name
                
                print(f"✓ Opened sheet: {found_sheet_name} (ID: {sheet_id})")
            except Exception as sheet_error:
                print(f"Error opening sheet: {sheet_error}")
                traceback.print_exc()
                raise ValueError(f"Failed to open or read sheet '{sheet_name}': {sheet_error}")

            # Auto-detect model column
            model_col = self.detect_model_column(df)
            
            if not model_col:
                print("No suitable model column found")
                raise ValueError("Could not detect a suitable column for model numbers")

            print(f"Using model column: {model_col}")
            print(f"Total rows to process: {len(df)}")
            sys.stdout.flush()

            total_rows = len(df)
            results = []
            
            # Create a directory for this sheet
            sheet_dir = os.path.expanduser(f"~/GoogleDriveMount/Web/{found_sheet_name}")
            print(f"Creating directory: {sheet_dir}")
            os.makedirs(sheet_dir, exist_ok=True)  # Create directory if it doesn't exist

            # Set the output path to be inside this directory
            self.output_path = os.path.join(sheet_dir, f"final_{found_sheet_name}.xlsx")
            print(f"Output path set to: {self.output_path}")
            
            # Initialize output dataframe
            self.output_df = pd.DataFrame(columns=["Model Column", "Model Number", "Title", "Description"])
            
            # Save an initial empty file to establish the file
            self.save_current_results()

            # Process each row
            print("Starting to process rows")
            for i, row_data in df.iterrows():
                if not self.running:
                    print("Processing stopped by user")
                    # Save any remaining results
                    self.save_current_results()
                    return
                
                current_row = i + 1
                model = str(row_data[model_col])
                if not model or pd.isna(model) or model.lower() == 'nan':
                    print(f"Skipping row {current_row}: Empty model number")
                    continue
                    
                print(f"Processing row {current_row}/{total_rows}: Model {model}")
                sys.stdout.flush()
                
                try:
                    print(f"Scraping model {model} with prefix {prefix}")
                    title, desc = self.scrape_katom(model, prefix)
                    
                    # Skip rows where the item is not found
                    if title == "Title not found" or "not found" in title.lower():
                        print(f"⚠️ Skipping row {current_row}: Item not found")
                        continue
                    
                    # Add to results list and update the output dataframe
                    print(f"Adding result to dataframe: {title[:30]}...")
                    new_row = pd.DataFrame([[model_col, model, title, desc]], columns=["Model Column", "Model Number", "Title", "Description"])
                    self.output_df = pd.concat([self.output_df, new_row], ignore_index=True)
                    
                    # Save after each row is processed
                    self.save_current_results()
                    
                    print(f"✓ Row {current_row}: {title[:30]}...")
                except Exception as scrape_error:
                    print(f"Error scraping row {current_row}: {scrape_error}")
                    traceback.print_exc()
                    # Skip this row instead of recording the error
                    continue
                
                # Calculate and update progress
                percent = int((current_row / total_rows) * 100)
                print(f"Emitting progress signal: {current_row}/{total_rows} = {percent}%")
                self.signals.progress.emit(current_row, total_rows, percent)
                
                # Add a small delay to prevent overloading the server
                time.sleep(0.5)

            # Final save with completed data
            print("All rows processed, saving final results")
            self.save_current_results()
            
            # Final update to 100%
            print("Emitting final progress signal: 100%")
            self.signals.progress.emit(total_rows, total_rows, 100)
            self.completed = True
            print(f"✅ Process completed. Final data saved to {self.output_path}")
            
        except Exception as e:
            import traceback
            print(f"[Process error] {e}")
            traceback.print_exc()
            self.signals.progress.emit(0, 0, 0)
            self.info_label.setText(f"Error: {str(e)[:50]}...")
            self.completed = True

if __name__ == "__main__":
    try:
        print("Starting application")
        # Add QT format for printing to stdout
        os.environ["QT_LOGGING_RULES"] = "*.debug=true"
        
        # Create application
        print("Creating QApplication")
        app = QApplication(sys.argv)
        
        # Set application style
        print("Setting application style")
        app.setStyle("Fusion")
        
        # Create main window
        print("Creating main window")
        window = SheetProcessor()
        
        # Show window
        print("Showing window")
        window.show()
        
        # Add initial sheet row
        print("Adding initial row")
        window.add_row()
        
        # Run application
        print("Starting event loop")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        with open('/home/mkpie/GoogleSheetsProcessor/error_log.txt', 'w') as f:
            f.write(f"Error: {str(e)}\n")
            f.write(traceback.format_exc())
