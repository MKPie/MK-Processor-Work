#!/usr/bin/env python3
# Save this as config_manager.py

import os
import json
import traceback

DEFAULT_CONFIG = {
    "app": {
        "window_title": "MK Processor 3.0.4",
        "window_size": [800, 600]
    },
    "scraping": {
        "timeout": 30,
        "retry_attempts": 2,
        "user_agent_rotation": True
    },
    "output": {
        "output_dir": "~/GoogleDriveMount/Web/Completed/Final",
        "prefix": "final_"
    },
    "ui": {
        "button_primary_color": "#4285f4",
        "button_secondary_color": "#f0f0f0"
    },
    "common_spec_fields": [
        "manufacturer", "food type", "frypot style", "heat", "hertz", "nema", 
        "number of fry pots", "oil capacity/fryer (lb)", "phase", "product", 
        "product type", "rating", "special features", "type", "voltage", 
        "warranty", "weight"
    ]
}

class ConfigManager:
    """Configuration manager for the MK Processor application"""
    
    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file if it exists"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    
                    # Merge loaded config with default config
                    # This ensures any new config options get default values
                    self._deep_update(self.config, loaded_config)
                    
                print(f"Configuration loaded from {self.config_file}")
            else:
                # No config file exists, create one with defaults
                self.save_config()
                print(f"Created new configuration file at {self.config_file}")
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print(traceback.format_exc())
            
            # If loading fails, fallback to defaults
            self.config = DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            print(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            print(traceback.format_exc())
            return False
    
    def get(self, section, key=None):
        """Get a configuration value"""
        try:
            if key is None:
                return self.config.get(section, {})
            else:
                return self.config.get(section, {}).get(key)
        except Exception as e:
            print(f"Error getting config value {section}.{key}: {e}")
            return None
    
    def set(self, section, key, value):
        """Set a configuration value"""
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            return True
        except Exception as e:
            print(f"Error setting config value {section}.{key}: {e}")
            return False
    
    def _deep_update(self, target, source):
        """Recursively update nested dictionaries"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
