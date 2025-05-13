#!/usr/bin/env python3
# Save this as webscraper_facade.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from fake_useragent import UserAgent
import re
import traceback
import math
import time

class WebScraperFacade:
    """
    Facade class for web scraping functionality to avoid modifying the main SheetRow class.
    This allows for extending scraping capabilities without affecting the core application.
    """
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        
        # Default config values if no config manager is provided
        self.timeout = 30
        self.retry_attempts = 2
        self.user_agent_rotation = True
        
        # Update from config if available
        if self.config_manager:
            self.timeout = self.config_manager.get("scraping", "timeout")
            self.retry_attempts = self.config_manager.get("scraping", "retry_attempts")
            self.user_agent_rotation = self.config_manager.get("scraping", "user_agent_rotation")
    
    def scrape_katom(self, model_number, prefix, signals=None):
        """Enhanced scrape_katom method with retries and better error handling"""
        # Clean model number
        model_number = ''.join(e for e in model_number if e.isalnum()).upper()
        if model_number.endswith("HC"):
            model_number = model_number[:-2]
        
        url = f"https://www.katom.com/{prefix}-{model_number}.html"
        
        # Set up Selenium
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # User agent handling
        if self.user_agent_rotation:
            options.add_argument(f'user-agent={UserAgent().random}')
        else:
            options.add_argument(f'user-agent={UserAgent().chrome}')
        
        driver = None
        title, description = "Title not found", "Description not found"
        specs_data = {}  # Dictionary to hold spec data
        specs_html = ""  # HTML table for other specs
        video_links = ""  # String to store video links
        item_found = False
        
        retry_count = 0
        while retry_count <= self.retry_attempts:
            try:
                if signals:
                    if retry_count > 0:
                        signals.update_status.emit(f"Retry {retry_count}/{self.retry_attempts} for model: {model_number}")
                
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(self.timeout)
                driver.get(url)
                
                # Check for 404
                if "404" in driver.title or "not found" in driver.title.lower():
                    if driver:
                        driver.quit()
                    break  # No need to retry for 404
                
                # Get title
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name.mb-0"))
                    )
                    
                    title_element = driver.find_element(By.CSS_SELECTOR, "h1.product-name.mb-0")
                    title = title_element.text.strip()
                    if title:
                        item_found = True
                except TimeoutException:
                    print(f"Timeout waiting for title element on {url}")
                    pass
                except Exception as e:
                    print(f"Error getting title: {e}")
                    pass
                
                # If item found, get the rest of the data
                if item_found:
                    # Get description
                    try:
                        tab_content = driver.find_element(By.CLASS_NAME, "tab-content")
                        paragraphs = tab_content.find_elements(By.TAG_NAME, "p")
                        filtered = [
                            f"<p>{p.text.strip()}</p>" for p in paragraphs
                            if p.text.strip() and not p.text.lower().startswith("*free") and "video" not in p.text.lower()
                        ]
                        description = "".join(filtered) if filtered else "Description not found"
                    except NoSuchElementException:
                        print(f"Tab content not found on {url}")
                        pass
                    except Exception as e:
                        print(f"Error getting description: {e}")
                        pass
                    
                    # Extract table data
                    specs_data, specs_html = self.extract_table_data(driver)
                    
                    # Extract video links
                    video_links = self.extract_video_links(driver)
                    
                    # If successful, break the retry loop
                    break
                else:
                    # Item not found, close driver and retry
                    if driver:
                        driver.quit()
                    retry_count += 1
                    
                    # Small delay before retry
                    time.sleep(1)
            
            except Exception as e:
                print(f"Error in scrape_katom (try {retry_count}): {e}")
                print(traceback.format_exc())
                
                # Close driver if it exists
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                
                # Increment retry count and try again
                retry_count += 1
                
                # Small delay before retry
                time.sleep(1)
                
                # If it's the last retry, propagate the error
                if retry_count > self.retry_attempts:
                    raise
        
        # Make sure driver is closed
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        return title, description, specs_data, specs_html, video_links
    
    def extract_table_data(self, driver):
        """Extract table data both as a dict and HTML table"""
        specs_dict = {}
        specs_html = ""
        
        try:
            # Try multiple approaches to find the table
            
            # First, try to get the original table HTML
            specs_tables = driver.find_elements(By.CSS_SELECTOR, "table.table.table-condensed.specs-table")
            
            if not specs_tables:
                # Try generic tables
                specs_tables = driver.find_elements(By.TAG_NAME, "table")
            
            if specs_tables:
                # Extract key-value pairs from the table
                table = specs_tables[0]
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                # Build a clean table with slim styling
                specs_html = '<table class="specs-table" cellspacing="0" cellpadding="4" border="1" style="margin-top:10px;border-collapse:collapse;width:auto;" align="left"><tbody>'
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        key = cells[0].text.strip()
                        value = cells[1].text.strip()
                        
                        # Check if this is a weight field and process accordingly
                        if "weight" in key.lower():
                            value = self.process_weight_value(value)
                        
                        # Add to the dictionary
                        if key and not key.lower() in specs_dict:
                            specs_dict[key.lower()] = value
                        
                        # Add to the HTML table
                        specs_html += f'<tr><td style="padding:3px 8px;"><b>{key}</b></td><td style="padding:3px 8px;">{value}</td></tr>'
                
                specs_html += "</tbody></table>"
            
            # If no table found or no HTML extracted, create an HTML table from the data we find
            if not specs_html or specs_html == "":
                # Start building an HTML table
                other_specs = []
                
                # Try to find spec elements in various ways
                
                # Method 1: Look for dedicated spec elements
                spec_rows = driver.find_elements(By.CSS_SELECTOR, ".specs-row, [class*='spec']")
                if spec_rows:
                    for row in spec_rows:
                        key_elem = row.find_elements(By.CSS_SELECTOR, ".spec-key, .spec-name, [class*='key'], [class*='name']")
                        val_elem = row.find_elements(By.CSS_SELECTOR, ".spec-value, .spec-val, [class*='value'], [class*='val']")
                        
                        if key_elem and val_elem:
                            key = key_elem[0].text.strip()
                            value = val_elem[0].text.strip()
                            
                            # Check if this is a weight field and process accordingly
                            if "weight" in key.lower():
                                value = self.process_weight_value(value)
                                
                            if key:
                                other_specs.append((key, value))
                                if not key.lower() in specs_dict:
                                    specs_dict[key.lower()] = value
                
                # Method 2: Look for definition lists
                if not other_specs:
                    dl_elements = driver.find_elements(By.TAG_NAME, "dl")
                    for dl in dl_elements:
                        terms = dl.find_elements(By.TAG_NAME, "dt")
                        definitions = dl.find_elements(By.TAG_NAME, "dd")
                        
                        for i in range(min(len(terms), len(definitions))):
                            key = terms[i].text.strip()
                            value = definitions[i].text.strip()
                            
                            # Check if this is a weight field and process accordingly
                            if "weight" in key.lower():
                                value = self.process_weight_value(value)
                                
                            if key:
                                other_specs.append((key, value))
                                if not key.lower() in specs_dict:
                                    specs_dict[key.lower()] = value
                
                # Method 3: Look for text patterns in all content
                if not other_specs:
                    # Get all elements that might contain specs
                    elements = driver.find_elements(By.CSS_SELECTOR, "p, div, li, span")
                    
                    # Common spec terms to look for - expand this list as needed
                    common_specs = [
                        "manufacturer", "food type", "frypot style", "heat", "hertz", "nema", 
                        "number of", "oil capacity", "phase", "product", "type", "rating", 
                        "special features", "voltage", "warranty", "weight", "dimensions"
                    ]
                    
                    for element in elements:
                        text = element.text.strip()
                        if not text or len(text) > 100:  # Skip empty or very long text
                            continue
                        
                        # Look for patterns like "Key: Value" or "Key - Value"
                        for pattern in [r'([^:]+):\s*(.+)', r'([^-]+)-\s*(.+)']: 
                            match = re.match(pattern, text)
                            if match:
                                key = match.group(1).strip()
                                value = match.group(2).strip()
                                
                                # Check if this is a weight field and process accordingly
                                if "weight" in key.lower():
                                    value = self.process_weight_value(value)
                                
                                # Check if this key is one of our common specs
                                if any(spec in key.lower() for spec in common_specs):
                                    other_specs.append((key, value))
                                    if not key.lower() in specs_dict:
                                        specs_dict[key.lower()] = value
                                    break
                
                # Create HTML table from the data we collected
                if other_specs:
                    specs_html = '<table class="specs-table" cellspacing="0" cellpadding="4" border="1" style="margin-top:10px;border-collapse:collapse;width:auto;" align="left"><tbody>'
                    for key, value in other_specs:
                        specs_html += f'<tr><td style="padding:3px 8px;"><b>{key}</b></td><td style="padding:3px 8px;">{value}</td></tr>'
                    specs_html += "</tbody></table>"
        
        except Exception as e:
            print(f"Error extracting table data: {e}")
        
        return specs_dict, specs_html
    
    def extract_video_links(self, driver):
        """Extract video links from the page"""
        video_links = ""
        
        try:
            # Find source tags with .mp4 files
            sources = driver.find_elements(By.CSS_SELECTOR, "source[src*='.mp4'], source[type*='video']")
            for source in sources:
                src = source.get_attribute("src")
                if src and src not in video_links:
                    video_links += f"{src}\n"
            
            # If no video sources found, look for video elements
            if not video_links:
                videos = driver.find_elements(By.TAG_NAME, "video")
                for video in videos:
                    # Try to get source elements within video tag
                    inner_sources = video.find_elements(By.TAG_NAME, "source")
                    for source in inner_sources:
                        src = source.get_attribute("src")
                        if src and src not in video_links:
                            video_links += f"{src}\n"
                            
            # Last resort - extract video URLs from the page source
            if not video_links:
                page_source = driver.page_source
                # Look for .mp4 URLs in the source
                mp4_pattern = r'https?://[^"\']+\.mp4'
                matches = re.findall(mp4_pattern, page_source)
                for match in matches:
                    if match not in video_links:
                        video_links += f"{match}\n"
        except Exception as e:
            print(f"Error extracting video links: {e}")
        
        return video_links
    
    def process_weight_value(self, value):
        """Process weight values: round up to whole number and add 5"""
        try:
            # Try to extract a number from the string
            # This handles cases like "22.93" or "22.93 lbs"
            number_match = re.search(r'(\d+(\.\d+)?)', str(value))
            if number_match:
                # Extract the number
                number = float(number_match.group(1))
                
                # Round up to nearest whole number
                rounded = math.ceil(number)
                
                # Add 5
                final = rounded + 5
                
                # If the original had units, keep them
                units_match = re.search(r'[^\d.]+$', str(value))
                units = units_match.group(0).strip() if units_match else ""
                
                return f"{final}{' ' + units if units else ''}"
            return value
        except:
            # If any error occurs, return the original value
            return value
