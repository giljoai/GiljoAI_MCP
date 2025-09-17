#!/usr/bin/env python3
"""
GiljoAI MCP Development Control Panel

A Flask-based web dashboard for managing all GiljoAI MCP services during development.
Provides service control, cache management, and real-time log viewing.

Port: 5500 (avoids conflicts with AKE-MCP ports 5000-5002)
"""

import os
import sys
import subprocess
import psutil
import threading
import time
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

app = Flask(__name__)
app.secret_key = 'dev-control-panel-secret-key'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service definitions
SERVICES = {
    'mcp_server': {
        'name': 'MCP Server',
        'port': 6001,
        'command': [sys.executable, '-m', 'src.giljo_mcp', '--mode', 'server'],
        'cwd': Path(__file__).parent,
        'log_file': 'logs/mcp_server.log'
    },
    'api_server': {
        'name': 'REST API Server',
        'port': 6002,
        'command': [sys.executable, '-m', 'api.main'],
        'cwd': Path(__file__).parent,
        'log_file': 'logs/api_server.log'
    },
    'websocket_server': {
        'name': 'WebSocket Server',
        'port': 6003,
        'command': [sys.executable, '-m', 'api.websocket_service'],
        'cwd': Path(__file__).parent,
        'log_file': 'logs/websocket_server.log'
    },
    'frontend': {
        'name': 'Frontend (Vue/Vite)',
        'port': 6000,
        'command': ['npm', 'run', 'dev'],
        'cwd': Path(__file__).parent / 'frontend',
        'log_file': 'logs/frontend.log'
    }
}

# Global variables for process management
processes = {}
log_threads = {}

# Cache status tracking
cache_status = {
    'last_operation': None,
    'status': 'idle',  # idle, success, failed
    'timestamp': None,
    'message': 'No cache operations performed yet',
    'details': ''
}

def check_port(port):
    """Check if a port is in use"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return True
    return False

def check_postgresql():
    """Check PostgreSQL service status"""
    try:
        # Check if PostgreSQL process is running
        for proc in psutil.process_iter(['pid', 'name']):
            if 'postgres' in proc.info['name'].lower():
                return True
        return False
    except:
        return False

def get_service_status(service_key):
    """Get the status of a service"""
    service = SERVICES[service_key]

    # Check if process is running
    if service_key in processes and processes[service_key].poll() is None:
        return 'running'

    # Check if port is in use (might be external process)
    if check_port(service['port']):
        return 'external'

    return 'stopped'

def start_service(service_key):
    """Start a service"""
    service = SERVICES[service_key]

    if get_service_status(service_key) in ['running', 'external']:
        return False, f"Service {service['name']} is already running"

    try:
        # Ensure log directory exists
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)

        # Start the process
        log_file = log_dir / f"{service_key}.log"

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n=== Service started at {datetime.now()} ===\n")

            processes[service_key] = subprocess.Popen(
                service['command'],
                cwd=service['cwd'],
                stdout=f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )

        logger.info(f"Started {service['name']} (PID: {processes[service_key].pid})")
        return True, f"Started {service['name']}"

    except Exception as e:
        logger.error(f"Failed to start {service['name']}: {e}")
        return False, f"Failed to start {service['name']}: {e}"

def stop_service(service_key):
    """Stop a service"""
    service = SERVICES[service_key]

    try:
        # Kill our managed process
        if service_key in processes:
            proc = processes[service_key]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            del processes[service_key]

        # Kill any process using the port
        for conn in psutil.net_connections():
            if conn.laddr.port == service['port']:
                try:
                    process = psutil.Process(conn.pid)
                    process.terminate()
                    logger.info(f"Terminated process on port {service['port']}")
                except:
                    pass

        return True, f"Stopped {service['name']}"

    except Exception as e:
        logger.error(f"Failed to stop {service['name']}: {e}")
        return False, f"Failed to stop {service['name']}: {e}"

def restart_service(service_key):
    """Restart a service"""
    stop_success, stop_msg = stop_service(service_key)
    time.sleep(2)  # Wait for clean shutdown
    start_success, start_msg = start_service(service_key)

    if start_success:
        return True, f"Restarted {SERVICES[service_key]['name']}"
    else:
        return False, f"Failed to restart: {start_msg}"

def write_cache_log(message):
    """Write to cache operations log file"""
    try:
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        cache_log_file = log_dir / 'cache_operations.log'

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(cache_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        logger.error(f"Failed to write cache log: {e}")

def clear_python_cache():
    """Clear all Python cache files"""
    global cache_status

    # Update status to indicate operation starting
    cache_status.update({
        'last_operation': 'clear_cache',
        'status': 'running',
        'timestamp': datetime.now(),
        'message': 'Cache clearing in progress...',
        'details': ''
    })

    # Log to cache log file
    write_cache_log("Cache clearing operation started")

    try:
        cache_count = 0
        cleared_items = []
        root_path = Path(__file__).parent

        # Remove __pycache__ directories
        pycache_count = 0
        for pycache_dir in root_path.rglob('__pycache__'):
            if pycache_dir.is_dir():
                shutil.rmtree(pycache_dir)
                pycache_count += 1
                cache_count += 1
        if pycache_count > 0:
            cleared_items.append(f"{pycache_count} __pycache__ directories")

        # Remove .pyc and .pyo files
        pyc_count = 0
        for cache_file in root_path.rglob('*.pyc'):
            cache_file.unlink()
            pyc_count += 1
            cache_count += 1

        pyo_count = 0
        for cache_file in root_path.rglob('*.pyo'):
            cache_file.unlink()
            pyo_count += 1
            cache_count += 1

        if pyc_count > 0 or pyo_count > 0:
            cleared_items.append(f"{pyc_count + pyo_count} bytecode files (.pyc/.pyo)")

        # Remove pytest cache
        pytest_cache = root_path / '.pytest_cache'
        if pytest_cache.exists():
            shutil.rmtree(pytest_cache)
            cache_count += 1
            cleared_items.append("pytest cache")

        # Remove mypy cache
        mypy_cache = root_path / '.mypy_cache'
        if mypy_cache.exists():
            shutil.rmtree(mypy_cache)
            cache_count += 1
            cleared_items.append("mypy cache")

        # Remove ruff cache
        ruff_cache = root_path / '.ruff_cache'
        if ruff_cache.exists():
            shutil.rmtree(ruff_cache)
            cache_count += 1
            cleared_items.append("ruff cache")

        # Update status to success
        success_message = f"Successfully cleared {cache_count} cache items"
        details = "Cleared: " + ", ".join(cleared_items) if cleared_items else "No cache items found to clear"

        cache_status.update({
            'status': 'success',
            'timestamp': datetime.now(),
            'message': success_message,
            'details': details
        })

        # Log success
        write_cache_log(f"SUCCESS: {success_message}")
        write_cache_log(f"Details: {details}")

        logger.info(f"Cache cleared: {cache_count} items")
        return True, success_message

    except Exception as e:
        # Update status to failed
        error_message = f"Failed to clear cache: {e}"
        cache_status.update({
            'status': 'failed',
            'timestamp': datetime.now(),
            'message': error_message,
            'details': str(e)
        })

        # Log error
        write_cache_log(f"ERROR: {error_message}")
        logger.error(f"Cache clear failed: {e}")
        return False, error_message

def get_log_tail(service_key, lines=50):
    """Get the last N lines from a service log"""
    service = SERVICES[service_key]
    log_file = Path(__file__).parent / service['log_file']

    if not log_file.exists():
        return f"Log file not found: {log_file}"

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading log: {e}"

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GiljoAI MCP Development Control Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .service-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .service-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
        }
        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status.running { background: #d4edda; color: #155724; }
        .status.stopped { background: #f8d7da; color: #721c24; }
        .status.external { background: #fff3cd; color: #856404; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 2px;
            font-size: 12px;
        }
        .btn.start { background: #28a745; color: white; }
        .btn.stop { background: #dc3545; color: white; }
        .btn.restart { background: #17a2b8; color: white; }
        .btn.cache { background: #ffc107; color: black; }
        .btn.logs { background: #6c757d; color: white; }
        .btn:hover { opacity: 0.8; }
        .maintenance {
            background: #e9ecef;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .log-viewer {
            background: #000;
            color: #0f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }
        .actions {
            text-align: center;
            margin: 20px 0;
        }
        .actions .btn {
            padding: 12px 24px;
            font-size: 14px;
            margin: 5px;
        }
        .flash {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .flash.success { background: #d4edda; color: #155724; }
        .flash.error { background: #f8d7da; color: #721c24; }
        .timestamp {
            font-size: 11px;
            color: #666;
            margin-top: 10px;
        }
        .cache-status {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }
        .cache-status-display {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .cache-status-indicator {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        }
        .cache-status-indicator.success {
            background: #d4edda;
            color: #155724;
        }
        .cache-status-indicator.failed {
            background: #f8d7da;
            color: #721c24;
        }
        .cache-status-indicator.running {
            background: #d1ecf1;
            color: #0c5460;
        }
        .cache-status-indicator.idle {
            background: #e9ecef;
            color: #495057;
        }
        .cache-timestamp {
            font-size: 12px;
            color: #6c757d;
        }
        .cache-message {
            font-weight: bold;
            margin: 5px 0;
        }
        .cache-details {
            font-size: 12px;
            color: #666;
            background: #f1f3f4;
            padding: 8px;
            border-radius: 4px;
            margin: 5px 0;
        }
    </style>
    <script>
        function executeAction(action, service = null) {
            const url = service ? `/api/${action}/${service}` : `/api/${action}`;
            fetch(url, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showFlash(data.message, 'success');
                    } else {
                        showFlash(data.message, 'error');
                    }
                    setTimeout(() => location.reload(), 1000);
                })
                .catch(error => {
                    showFlash('Action failed: ' + error, 'error');
                });
        }

        function showFlash(message, type) {
            const flash = document.createElement('div');
            flash.className = `flash ${type}`;
            flash.textContent = message;
            document.querySelector('.container').insertBefore(flash, document.querySelector('.section'));
            setTimeout(() => flash.remove(), 5000);
        }

        function showLogs(service) {
            fetch(`/api/logs/${service}`)
                .then(response => response.text())
                .then(data => {
                    document.getElementById('log-content').textContent = data;
                    document.getElementById('log-viewer').style.display = 'block';
                    document.getElementById('log-service').textContent = service;
                });
        }

        function hideLogs() {
            document.getElementById('log-viewer').style.display = 'none';
        }

        function showCacheLogs() {
            fetch('/api/cache_logs')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('log-content').textContent = data;
                    document.getElementById('log-viewer').style.display = 'block';
                    document.getElementById('log-service').textContent = 'Cache Operations';
                });
        }

        // Auto-refresh every 5 seconds
        setInterval(() => {
            const urlParams = new URLSearchParams(window.location.search);
            if (!urlParams.has('no_refresh')) {
                location.reload();
            }
        }, 5000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 GiljoAI MCP Development Control Panel</h1>
            <p>Service Management & Development Tools</p>
            <div class="timestamp">Last updated: {{ current_time }}</div>
        </div>

        <div class="section">
            <h2>🔧 System Services</h2>
            <div class="service-grid">
                {% for key, service in services.items() %}
                <div class="service-card">
                    <div class="service-header">
                        <h3>{{ service.name }}</h3>
                        <span class="status {{ statuses[key] }}">
                            {% if statuses[key] == 'running' %}🟢 Running
                            {% elif statuses[key] == 'external' %}🟡 External
                            {% else %}🔴 Stopped{% endif %}
                        </span>
                    </div>
                    <p><strong>Port:</strong> {{ service.port }}</p>
                    <p><strong>Command:</strong> {{ service.command|join(' ') }}</p>
                    <div style="margin-top: 10px;">
                        <button class="btn start" onclick="executeAction('start', '{{ key }}')">Start</button>
                        <button class="btn stop" onclick="executeAction('stop', '{{ key }}')">Stop</button>
                        <button class="btn restart" onclick="executeAction('restart', '{{ key }}')">Restart</button>
                        <button class="btn logs" onclick="showLogs('{{ key }}')">Logs</button>
                    </div>
                </div>
                {% endfor %}

                <div class="service-card">
                    <div class="service-header">
                        <h3>PostgreSQL Database</h3>
                        <span class="status {% if postgresql_status %}running{% else %}stopped{% endif %}">
                            {% if postgresql_status %}🟢 Running{% else %}🔴 Stopped{% endif %}
                        </span>
                    </div>
                    <p><strong>Port:</strong> 5432</p>
                    <p><strong>Database:</strong> ai_assistant</p>
                    <div style="margin-top: 10px;">
                        <button class="btn logs" onclick="alert('PostgreSQL logs: See Windows Services')">Info</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🧹 Maintenance Tools</h2>

            <!-- Cache Status Indicator -->
            <div class="cache-status">
                <h3>Cache Operations Status</h3>
                <div class="cache-status-display">
                    <span class="cache-status-indicator {{ cache_status.status }}">
                        {% if cache_status.status == 'success' %}✅ SUCCESS
                        {% elif cache_status.status == 'failed' %}❌ FAILED
                        {% elif cache_status.status == 'running' %}🔄 RUNNING
                        {% else %}⏸️ IDLE{% endif %}
                    </span>
                    <span class="cache-timestamp">
                        {% if cache_status.timestamp %}
                            Last operation: {{ cache_status.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}
                        {% else %}
                            No operations performed yet
                        {% endif %}
                    </span>
                </div>
                <div class="cache-message">{{ cache_status.message }}</div>
                {% if cache_status.details %}
                <div class="cache-details">{{ cache_status.details }}</div>
                {% endif %}
                <button class="btn logs" onclick="showCacheLogs()">View Cache Logs</button>
            </div>

            <div class="maintenance">
                <h3>Cache Management</h3>
                <p>Clear Python bytecode cache to ensure code changes take effect</p>
                <button class="btn cache" onclick="executeAction('clear_cache')">Clear Python Cache</button>
                <button class="btn restart" onclick="executeAction('clear_and_restart')">Clear Cache & Restart All</button>
            </div>
        </div>

        <div class="actions">
            <h2>🎮 Quick Actions</h2>
            <button class="btn start" onclick="executeAction('start_all')">Start All Services</button>
            <button class="btn stop" onclick="executeAction('stop_all')">Stop All Services</button>
            <button class="btn restart" onclick="executeAction('restart_all')">Restart All Services</button>
        </div>

        <div id="log-viewer" class="section" style="display: none;">
            <h2>📋 Logs - <span id="log-service"></span></h2>
            <button class="btn" onclick="hideLogs()">Hide Logs</button>
            <div class="log-viewer" id="log-content"></div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    """Main dashboard"""
    statuses = {}
    for key in SERVICES:
        statuses[key] = get_service_status(key)

    postgresql_status = check_postgresql()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template_string(
        HTML_TEMPLATE,
        services=SERVICES,
        statuses=statuses,
        postgresql_status=postgresql_status,
        current_time=current_time,
        cache_status=cache_status
    )

@app.route('/api/start/<service_key>', methods=['POST'])
def api_start_service(service_key):
    """Start a specific service"""
    if service_key not in SERVICES:
        return jsonify({'success': False, 'message': 'Unknown service'})

    success, message = start_service(service_key)
    return jsonify({'success': success, 'message': message})

@app.route('/api/stop/<service_key>', methods=['POST'])
def api_stop_service(service_key):
    """Stop a specific service"""
    if service_key not in SERVICES:
        return jsonify({'success': False, 'message': 'Unknown service'})

    success, message = stop_service(service_key)
    return jsonify({'success': success, 'message': message})

@app.route('/api/restart/<service_key>', methods=['POST'])
def api_restart_service(service_key):
    """Restart a specific service"""
    if service_key not in SERVICES:
        return jsonify({'success': False, 'message': 'Unknown service'})

    success, message = restart_service(service_key)
    return jsonify({'success': success, 'message': message})

@app.route('/api/start_all', methods=['POST'])
def api_start_all():
    """Start all services"""
    results = []
    for service_key in SERVICES:
        success, message = start_service(service_key)
        results.append(f"{SERVICES[service_key]['name']}: {message}")

    return jsonify({'success': True, 'message': '; '.join(results)})

@app.route('/api/stop_all', methods=['POST'])
def api_stop_all():
    """Stop all services"""
    results = []
    for service_key in SERVICES:
        success, message = stop_service(service_key)
        results.append(f"{SERVICES[service_key]['name']}: {message}")

    return jsonify({'success': True, 'message': '; '.join(results)})

@app.route('/api/restart_all', methods=['POST'])
def api_restart_all():
    """Restart all services"""
    # Stop all first
    for service_key in SERVICES:
        stop_service(service_key)

    time.sleep(3)  # Wait for clean shutdown

    # Start all
    results = []
    for service_key in SERVICES:
        success, message = start_service(service_key)
        results.append(f"{SERVICES[service_key]['name']}: {message}")

    return jsonify({'success': True, 'message': '; '.join(results)})

@app.route('/api/clear_cache', methods=['POST'])
def api_clear_cache():
    """Clear Python cache"""
    success, message = clear_python_cache()
    return jsonify({'success': success, 'message': message})

@app.route('/api/clear_and_restart', methods=['POST'])
def api_clear_and_restart():
    """Clear cache and restart all services"""
    global cache_status

    # Update cache status for combined operation
    cache_status.update({
        'last_operation': 'clear_and_restart',
        'status': 'running',
        'timestamp': datetime.now(),
        'message': 'Clearing cache and restarting all services...',
        'details': ''
    })

    write_cache_log("Clear cache and restart all services operation started")

    # Clear cache first
    cache_success, cache_message = clear_python_cache()

    if not cache_success:
        # Cache status already updated by clear_python_cache function
        return jsonify({'success': False, 'message': f"Cache clear failed: {cache_message}"})

    # Stop all services
    for service_key in SERVICES:
        stop_service(service_key)

    time.sleep(3)  # Wait for clean shutdown

    # Start all services
    results = [f"Cache: {cache_message}"]
    for service_key in SERVICES:
        success, message = start_service(service_key)
        results.append(f"{SERVICES[service_key]['name']}: {message}")

    # Update final cache status
    final_message = "Cache cleared and all services restarted"
    cache_status.update({
        'status': 'success',
        'timestamp': datetime.now(),
        'message': final_message,
        'details': '; '.join(results)
    })

    write_cache_log(f"SUCCESS: {final_message}")
    write_cache_log(f"Results: {'; '.join(results)}")

    return jsonify({'success': True, 'message': '; '.join(results)})

@app.route('/api/logs/<service_key>')
def api_get_logs(service_key):
    """Get logs for a service"""
    if service_key not in SERVICES:
        return "Unknown service", 404

    return get_log_tail(service_key)

@app.route('/api/cache_logs')
def api_get_cache_logs():
    """Get cache operations log"""
    log_file = Path(__file__).parent / 'logs' / 'cache_operations.log'

    if not log_file.exists():
        return "No cache operations logged yet"

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            # Return last 50 lines
            return ''.join(all_lines[-50:])
    except Exception as e:
        return f"Error reading cache log: {e}"

if __name__ == '__main__':
    # Ensure logs directory exists
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    print("🚀 Starting GiljoAI MCP Development Control Panel")
    print("📋 Dashboard available at: http://localhost:5500")
    print("🔧 Service ports: MCP(6001), API(6002), WebSocket(6003), Frontend(6000)")
    print("⏹️  Press Ctrl+C to stop")

    # Start Flask app
    app.run(
        host='127.0.0.1',
        port=5500,
        debug=False,  # Disable debug to avoid auto-reload conflicts
        use_reloader=False
    )