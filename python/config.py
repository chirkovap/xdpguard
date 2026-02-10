"""Configuration management for XDPGuard"""

import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration loader and manager"""
    
    def __init__(self, config_path="/etc/xdpguard/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.load()
    
    def load(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def save(self):
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def get(self, path, default=None):
        """Get nested config value by dot notation (e.g., 'network.interface')"""
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        
        return value
    
    def set(self, path, value):
        """Set nested config value by dot notation"""
        keys = path.split('.')
        target = self.config
        
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        
        target[keys[-1]] = value
    
    def validate(self):
        """Validate configuration"""
        required_keys = [
            'network.interface',
            'protection.enabled',
            'web.host',
            'web.port',
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                raise ValueError(f"Missing required config key: {key}")
        
        logger.info("Configuration validation passed")
        return True
