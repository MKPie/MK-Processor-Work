#!/usr/bin/env python3
# Save this as webscraper_wrapper.py

import os
import sys
from webscraper_facade import WebScraperFacade

def create_webscraper_wrapper(sheet_row):
    """
    Creates a wrapper around the SheetRow class to use the WebScraperFacade
    without modifying the original code.
    
    Call this function at the start of your application to enhance scraping.
    """
    # Store the original method
    original_scrape_katom = sheet_row.scrape_katom
    
    # Create the facade
    config_manager = getattr(sheet_row.parent, 'config_manager', None)
    scraper = WebScraperFacade(config_manager)
    
    # Define the wrapper function
    def wrapped_scrape_katom(model_number, prefix):
        try:
            # Log the scraping attempt
            print(f"Enhanced scraping for model: {model_number} with prefix: {prefix}")
            
            # Use the facade to scrape
            return scraper.scrape_katom(model_number, prefix, sheet_row.signals)
        except Exception as e:
            print(f"Error in enhanced scraping, falling back to original method: {e}")
            # Fall back to original method if facade fails
            return original_scrape_katom(model_number, prefix)
    
    # Replace the original method with our wrapped version
    sheet_row.scrape_katom = wrapped_scrape_katom
    
    return sheet_row
