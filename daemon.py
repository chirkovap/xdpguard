#!/usr/bin/env python3
"""XDPGuard Daemon - Main service process"""

import sys
import logging
import signal
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from python.config import Config
from python.xdpmanager import XDPManager
from python.stats import StatsCollector
from web.app import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/xdpguard.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class XDPGuardDaemon:
    """Main daemon for XDPGuard"""
    
    def __init__(self, config_path='/etc/xdpguard/config.yaml'):
        self.config = Config(config_path)
        self.xdp_manager = XDPManager(self.config)
        self.stats_collector = StatsCollector(
            self.config.get('database.path', '/var/lib/xdpguard/stats.db')
        )
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
    
    def start(self):
        """Start the daemon"""
        logger.info("="*50)
        logger.info("Starting XDPGuard Daemon...")
        logger.info("="*50)
        
        # Validate configuration
        try:
            self.config.validate()
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return
        
        # Initialize XDP program
        try:
            logger.info("Loading XDP program...")
            if not self.xdp_manager.load_program():
                logger.error("Failed to load XDP program")
                return
            logger.info("✓ XDP program loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize XDP: {e}")
            return
        
        # Start statistics collection thread
        import threading
        stats_thread = threading.Thread(target=self.collect_stats, daemon=True)
        stats_thread.start()
        logger.info("✓ Statistics collection started")
        
        # Start web interface
        web_host = self.config.get('web.host', '0.0.0.0')
        web_port = self.config.get('web.port', 8080)
        
        logger.info(f"Starting web interface on {web_host}:{web_port}...")
        logger.info(f"Access dashboard at: http://{web_host}:{web_port}")
        logger.info("="*50)
        logger.info("XDPGuard is running. Press Ctrl+C to stop.")
        logger.info("="*50)
        
        try:
            app = create_app(self.config.config_path)
            app.run(
                host=web_host,
                port=web_port,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"Web interface error: {e}")
    
    def collect_stats(self):
        """Periodically collect and store statistics"""
        interval = self.config.get('monitoring.stats_interval', 5)
        
        while self.running:
            try:
                # Get current statistics
                stats = self.xdp_manager.get_statistics()
                
                # Log to database
                self.stats_collector.log_traffic(
                    packets_in=stats['packets_total'],
                    packets_out=stats['packets_passed'],
                    packets_dropped=stats['packets_dropped'],
                    connections=0  # TODO: Implement connection tracking
                )
                
            except Exception as e:
                logger.error(f"Error collecting stats: {e}")
            
            time.sleep(interval)
    
    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        logger.info("="*50)
        logger.info("Shutting down XDPGuard...")
        self.running = False
        
        # Cleanup - optionally keep rules active
        if self.config.get('protection.cleanup_on_exit', False):
            logger.info("Removing XDP program...")
            self.xdp_manager.unload_program()
        else:
            logger.info("Keeping XDP program active")
        
        # Cleanup old data
        retention_days = self.config.get('monitoring.history_retention', 168) // 24
        self.stats_collector.cleanup_old_data(days=retention_days)
        
        logger.info("XDPGuard stopped")
        logger.info("="*50)
        sys.exit(0)


def main():
    """Main entry point"""
    # Check if running as root
    import os
    if os.geteuid() != 0:
        print("ERROR: XDPGuard must be run as root")
        sys.exit(1)
    
    # Parse command line arguments
    config_path = '/etc/xdpguard/config.yaml'
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Start daemon
    daemon = XDPGuardDaemon(config_path)
    daemon.start()


if __name__ == '__main__':
    main()
