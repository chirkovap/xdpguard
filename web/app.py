#!/usr/bin/env python3
"""
XDPGuard Flask Web Application

Provides REST API and web dashboard for XDP management.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import logging
import os

logger = logging.getLogger(__name__)


def create_app(config, xdp_manager):
    """Create and configure Flask application"""
    
    # Get the directory of this file for templates
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    
    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir)
    
    app.config['SECRET_KEY'] = config.get('web.secret_key', 'dev-secret-key')
    app.config['XDP_MANAGER'] = xdp_manager
    app.config['CONFIG'] = config

    # Routes
    @app.route('/')
    def index():
        """Main dashboard page"""
        return render_template('dashboard.html')

    @app.route('/api/status')
    def api_status():
        """Get system status and statistics"""
        try:
            stats = xdp_manager.get_statistics()
            blocked_ips = xdp_manager.get_blocked_ips()
            
            return jsonify({
                'status': 'running',
                'protection_enabled': config.get('protection.enabled', True),
                'stats': stats,
                'blocked_count': len(blocked_ips),
                'blocked_ips': blocked_ips[:20]  # Return first 20
            })
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/block', methods=['POST'])
    def api_block():
        """Block an IP address"""
        try:
            data = request.json
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP address required'}), 400
            
            success = xdp_manager.block_ip(ip)
            
            return jsonify({
                'success': success,
                'message': f'IP {ip} blocked' if success else 'Failed to block IP'
            })
        except Exception as e:
            logger.error(f"Failed to block IP: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/unblock', methods=['POST'])
    def api_unblock():
        """Unblock an IP address"""
        try:
            data = request.json
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP address required'}), 400
            
            success = xdp_manager.unblock_ip(ip)
            
            return jsonify({
                'success': success,
                'message': f'IP {ip} unblocked' if success else 'Failed to unblock IP'
            })
        except Exception as e:
            logger.error(f"Failed to unblock IP: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/blocked')
    def api_blocked():
        """Get list of blocked IPs"""
        try:
            blocked_ips = xdp_manager.get_blocked_ips()
            
            return jsonify({
                'blocked_ips': blocked_ips,
                'count': len(blocked_ips)
            })
        except Exception as e:
            logger.error(f"Failed to get blocked IPs: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/clear-rate-limits', methods=['POST'])
    def api_clear_rate_limits():
        """Clear rate limiting counters"""
        try:
            success = xdp_manager.clear_rate_limits()
            
            return jsonify({
                'success': success,
                'message': 'Rate limits cleared' if success else 'Failed to clear'
            })
        except Exception as e:
            logger.error(f"Failed to clear rate limits: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """Get or update configuration"""
        if request.method == 'GET':
            return jsonify(config.config)
        elif request.method == 'POST':
            try:
                data = request.json
                # Update config values
                for key, value in data.items():
                    config.set(key, value)
                
                config.save()
                
                return jsonify({
                    'success': True,
                    'message': 'Configuration updated'
                })
            except Exception as e:
                logger.error(f"Failed to update config: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    return app
