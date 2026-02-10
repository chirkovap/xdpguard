"""Flask web application for XDPGuard control panel"""

from flask import Flask, render_template, jsonify, request
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.config import Config
from python.xdpmanager import XDPManager
from python.stats import StatsCollector

logger = logging.getLogger(__name__)

# Global instances
config = None
xdp_manager = None
stats_collector = None


def create_app(config_path='/etc/xdpguard/config.yaml'):
    """Create and configure Flask application"""
    global config, xdp_manager, stats_collector
    
    app = Flask(__name__)
    
    # Load configuration
    config = Config(config_path)
    app.config['SECRET_KEY'] = config.get('web.secret_key', 'dev-secret-key')
    
    # Initialize XDP manager and stats collector
    xdp_manager = XDPManager(config)
    stats_collector = StatsCollector(config.get('database.path', '/var/lib/xdpguard/stats.db'))
    
    @app.route('/')
    def index():
        """Main dashboard"""
        return render_template('dashboard.html')
    
    @app.route('/api/status')
    def api_status():
        """Get system status"""
        try:
            stats = xdp_manager.get_statistics()
            blocked_ips = xdp_manager.get_blocked_ips()
            
            return jsonify({
                'status': 'running',
                'protection_enabled': config.get('protection.enabled', True),
                'interface': config.get('network.interface', 'eth0'),
                'stats': stats,
                'blocked_count': len(blocked_ips),
                'blocked_ips': blocked_ips[:20]  # Return max 20 IPs
            })
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """Get or update configuration"""
        if request.method == 'GET':
            return jsonify(config.config)
        
        elif request.method == 'POST':
            try:
                data = request.json
                # Update specific config values
                for key, value in data.items():
                    config.set(key, value)
                config.save()
                return jsonify({'success': True, 'message': 'Configuration updated'})
            except Exception as e:
                logger.error(f"Error updating config: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/block', methods=['POST'])
    def api_block_ip():
        """Block an IP address"""
        try:
            data = request.json
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP required'}), 400
            
            success = xdp_manager.block_ip(ip)
            
            if success:
                stats_collector.log_blocked_ip(ip, reason="manual")
            
            return jsonify({'success': success})
        except Exception as e:
            logger.error(f"Error blocking IP: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/unblock', methods=['POST'])
    def api_unblock_ip():
        """Unblock an IP address"""
        try:
            data = request.json
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP required'}), 400
            
            success = xdp_manager.unblock_ip(ip)
            
            if success:
                stats_collector.log_unblocked_ip(ip)
            
            return jsonify({'success': success})
        except Exception as e:
            logger.error(f"Error unblocking IP: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/blocked')
    def api_blocked_list():
        """Get list of blocked IPs with details"""
        try:
            recent_blocks = stats_collector.get_recent_blocks(limit=100)
            return jsonify(recent_blocks)
        except Exception as e:
            logger.error(f"Error getting blocked list: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/traffic')
    def api_traffic():
        """Get traffic statistics"""
        try:
            hours = request.args.get('hours', 24, type=int)
            history = stats_collector.get_traffic_history(hours=hours)
            return jsonify(history)
        except Exception as e:
            logger.error(f"Error getting traffic: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/attacks')
    def api_attacks():
        """Get attack events"""
        try:
            hours = request.args.get('hours', 24, type=int)
            events = stats_collector.get_attack_events(hours=hours)
            return jsonify(events)
        except Exception as e:
            logger.error(f"Error getting attacks: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clear-stats', methods=['POST'])
    def api_clear_stats():
        """Clear statistics"""
        try:
            xdp_manager.clear_statistics()
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error clearing stats: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False
    )
