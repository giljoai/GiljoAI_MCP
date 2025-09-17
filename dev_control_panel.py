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
        'command': [sys.executable, '-m', 'giljo_mcp', '--mode', 'server'],
        'cwd': Path(__file__).parent / 'src',
        'log_file': 'logs/mcp_server.log'
    },
    'api_server': {
        'name': 'REST API + WebSocket Server',
        'port': 6002,
        'command': [sys.executable, '-m', 'api.main'],
        'cwd': Path(__file__).parent,
        'log_file': 'logs/api_server.log'
    },
    'frontend': {
        'name': 'Frontend (Vue/Vite)',
        'port': 6000,
        'command': ['npm.cmd', 'run', 'dev'],  # Use npm.cmd on Windows
        'cwd': Path(__file__).parent / 'frontend',
        'log_file': 'logs/frontend.log'
    }
}

# Global variables for process management
processes = {}
log_threads = {}
service_statuses = {}  # Cached service statuses
monitoring_active = False
monitoring_thread = None

def save_process_info(service_key, pid):
    """Save process info to file for persistence"""
    try:
        pid_file = Path(__file__).parent / 'logs' / f'{service_key}.pid'
        with open(pid_file, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        logger.error(f"Failed to save PID for {service_key}: {e}")

def load_process_info(service_key):
    """Load process info from file"""
    try:
        pid_file = Path(__file__).parent / 'logs' / f'{service_key}.pid'
        if pid_file.exists():
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
                # Check if process is still running
                if psutil.pid_exists(pid):
                    return pid
                else:
                    # Process is dead, remove stale PID file
                    pid_file.unlink()
    except Exception as e:
        logger.debug(f"Could not load PID for {service_key}: {e}")
    return None

def remove_process_info(service_key):
    """Remove process info file"""
    try:
        pid_file = Path(__file__).parent / 'logs' / f'{service_key}.pid'
        if pid_file.exists():
            pid_file.unlink()
    except Exception as e:
        logger.debug(f"Could not remove PID file for {service_key}: {e}")

def wait_for_service_startup(service_key, max_wait=10):
    """Wait for a service to start listening on its port"""
    service = SERVICES[service_key]
    port = service['port']

    for i in range(max_wait):
        if check_port(port):
            logger.info(f"Service {service['name']} is now listening on port {port}")
            return True
        time.sleep(1)

    logger.warning(f"Service {service['name']} did not start listening on port {port} within {max_wait} seconds")
    return False

def monitor_services():
    """Continuously monitor service health in background thread"""
    global monitoring_active, service_statuses

    while monitoring_active:
        try:
            for service_key in SERVICES:
                old_status = service_statuses.get(service_key, 'unknown')
                new_status = get_service_status_direct(service_key)

                # Only log status changes
                if old_status != new_status:
                    logger.info(f"Service {SERVICES[service_key]['name']} status changed: {old_status} → {new_status}")

                service_statuses[service_key] = new_status

            # Check PostgreSQL too
            old_pg_status = service_statuses.get('postgresql', False)
            new_pg_status = check_postgresql()
            if old_pg_status != new_pg_status:
                logger.info(f"PostgreSQL status changed: {old_pg_status} → {new_pg_status}")
            service_statuses['postgresql'] = new_pg_status

        except Exception as e:
            logger.error(f"Error in service monitoring: {e}")

        # Wait 3 seconds before next check
        time.sleep(3)

def get_service_status_direct(service_key):
    """Get service status without caching - for monitoring thread"""
    service = SERVICES[service_key]

    # Check if we have a tracked process in memory
    if service_key in processes and processes[service_key].poll() is None:
        return 'running'

    # Check for persistent PID info
    saved_pid = load_process_info(service_key)
    if saved_pid:
        try:
            proc = psutil.Process(saved_pid)
            if proc.is_running():
                # For MCP server, check if it's really the right process
                if service_key == 'mcp_server':
                    # Check if the process command line contains giljo_mcp
                    try:
                        cmdline = ' '.join(proc.cmdline())
                        if 'giljo_mcp' in cmdline:
                            return 'running'
                    except:
                        pass
                else:
                    return 'running'
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            remove_process_info(service_key)

    # Check if port is in use (might be external process or lost tracking)
    if check_port(service['port']):
        return 'external'

    return 'stopped'

def start_monitoring():
    """Start the background monitoring thread"""
    global monitoring_active, monitoring_thread

    if monitoring_active:
        return

    monitoring_active = True
    monitoring_thread = threading.Thread(target=monitor_services, daemon=True)
    monitoring_thread.start()
    logger.info("Started background service monitoring")

def stop_monitoring():
    """Stop the background monitoring thread"""
    global monitoring_active, monitoring_thread

    monitoring_active = False
    if monitoring_thread:
        monitoring_thread.join(timeout=5)
    logger.info("Stopped background service monitoring")

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
    try:
        connections = psutil.net_connections(kind='inet')
        for conn in connections:
            if (hasattr(conn, 'laddr') and conn.laddr and
                conn.laddr.port == port and
                conn.status in ['LISTEN', 'ESTABLISHED']):
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, Exception):
        # Fallback: try to bind to the port
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except:
            pass
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
    """Get the status of a service - uses cached status from monitoring thread if available"""
    global service_statuses

    # If monitoring is active and we have a cached status, use it
    if monitoring_active and service_key in service_statuses:
        return service_statuses[service_key]

    # Otherwise, check directly
    return get_service_status_direct(service_key)

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

            # For services that need to stay running, don't use CREATE_NEW_CONSOLE
            # Instead, use subprocess.DETACHED_PROCESS to create independent processes
            if os.name == 'nt':
                # Windows: Use DETACHED_PROCESS to create independent process
                processes[service_key] = subprocess.Popen(
                    service['command'],
                    cwd=service['cwd'],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: Use standard approach
                processes[service_key] = subprocess.Popen(
                    service['command'],
                    cwd=service['cwd'],
                    stdout=f,
                    stderr=subprocess.STDOUT
                )

        # Save PID for persistence
        save_process_info(service_key, processes[service_key].pid)

        # Give the service a moment to start
        time.sleep(2)

        # Check if the process is still running
        if processes[service_key].poll() is not None:
            # Process exited immediately
            logger.warning(f"Process for {service['name']} exited immediately")
            remove_process_info(service_key)
            if service_key in processes:
                del processes[service_key]

            # Still wait to see if service started despite process exit
            if wait_for_service_startup(service_key, max_wait=5):
                return True, f"Started {service['name']} (service detected)"
            else:
                return False, f"Service {service['name']} failed to start - check logs"

        # Process is still running, wait for it to start listening
        logger.info(f"Process started for {service['name']} (PID: {processes[service_key].pid})")

        # Wait for service to start listening
        if wait_for_service_startup(service_key, max_wait=8):
            return True, f"Started {service['name']} successfully"
        else:
            # Service process is running but not listening - might be starting up
            return True, f"Started {service['name']} (process running, port pending)"

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

        # Remove PID file
        remove_process_info(service_key)

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
            // Open logs in a new window
            const logWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes,resizable=yes');
            logWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Logs - ${service}</title>
                    <style>
                        body { font-family: 'Courier New', monospace; background: #000; color: #0f0; padding: 20px; margin: 0; }
                        .header { color: #fff; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 10px; }
                        .log-content { white-space: pre-wrap; font-size: 12px; line-height: 1.4; }
                        .refresh-btn { background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-left: 10px; }
                        .refresh-btn:hover { background: #0056b3; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>Service Logs - ${service}</h2>
                        <button class="refresh-btn" onclick="refreshLogs()">Refresh</button>
                        <button class="refresh-btn" onclick="window.close()">Close</button>
                    </div>
                    <div id="log-content" class="log-content">Loading logs...</div>
                    <script>
                        function refreshLogs() {
                            fetch('/api/logs/${service}')
                                .then(response => response.text())
                                .then(data => {
                                    document.getElementById('log-content').textContent = data;
                                    // Auto-scroll to bottom
                                    window.scrollTo(0, document.body.scrollHeight);
                                })
                                .catch(error => {
                                    document.getElementById('log-content').textContent = 'Error loading logs: ' + error;
                                });
                        }

                        // Load logs initially
                        refreshLogs();

                        // Auto-refresh every 5 seconds
                        setInterval(refreshLogs, 5000);
                    </script>
                </body>
                </html>
            `);
        }

        function hideLogs() {
            document.getElementById('log-viewer').style.display = 'none';
        }

        function showCacheLogs() {
            // Open cache logs in a new window
            const logWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes,resizable=yes');
            logWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Cache Operations Log</title>
                    <style>
                        body { font-family: 'Courier New', monospace; background: #000; color: #0f0; padding: 20px; margin: 0; }
                        .header { color: #fff; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 10px; }
                        .log-content { white-space: pre-wrap; font-size: 12px; line-height: 1.4; }
                        .refresh-btn { background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-left: 10px; }
                        .refresh-btn:hover { background: #0056b3; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>Cache Operations Log</h2>
                        <button class="refresh-btn" onclick="refreshLogs()">Refresh</button>
                        <button class="refresh-btn" onclick="window.close()">Close</button>
                    </div>
                    <div id="log-content" class="log-content">Loading cache logs...</div>
                    <script>
                        function refreshLogs() {
                            fetch('/api/cache_logs')
                                .then(response => response.text())
                                .then(data => {
                                    document.getElementById('log-content').textContent = data;
                                    // Auto-scroll to bottom
                                    window.scrollTo(0, document.body.scrollHeight);
                                })
                                .catch(error => {
                                    document.getElementById('log-content').textContent = 'Error loading cache logs: ' + error;
                                });
                        }

                        // Load logs initially
                        refreshLogs();

                        // Auto-refresh every 5 seconds
                        setInterval(refreshLogs, 5000);
                    </script>
                </body>
                </html>
            `);
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
            {% if monitoring_active %}
            <div class="monitoring-status" style="color: #90EE90; font-size: 14px; margin-top: 5px;">
                ✅ Real-time monitoring active (3-second intervals)
            </div>
            {% else %}
            <div class="monitoring-status" style="color: #FFB6C1; font-size: 14px; margin-top: 5px;">
                ⚠️ Real-time monitoring inactive
            </div>
            {% endif %}
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

    postgresql_status = service_statuses.get('postgresql', check_postgresql())
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template_string(
        HTML_TEMPLATE,
        services=SERVICES,
        statuses=statuses,
        postgresql_status=postgresql_status,
        current_time=current_time,
        cache_status=cache_status,
        monitoring_active=monitoring_active
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

@app.route('/api/status')
def api_get_status():
    """Get current status of all services"""
    statuses = {}
    for key in SERVICES:
        statuses[key] = get_service_status(key)

    return jsonify({
        'services': statuses,
        'postgresql': service_statuses.get('postgresql', check_postgresql()),
        'monitoring_active': monitoring_active,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    # Ensure logs directory exists
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Check for existing running services on startup
    print("🔍 Checking for existing services...")
    for service_key in SERVICES:
        status = get_service_status(service_key)
        if status != 'stopped':
            print(f"   {SERVICES[service_key]['name']}: {status.upper()}")

    print("🚀 Starting GiljoAI MCP Development Control Panel")
    print("📋 Dashboard available at: http://localhost:5500")
    print("🔧 Service ports: MCP(6001), API+WebSocket(6002), Frontend(6000)")
    print("🔄 Starting continuous service monitoring...")

    # Start background monitoring
    start_monitoring()

    print("⏹️  Press Ctrl+C to stop")

    try:
        # Start Flask app
        app.run(
            host='127.0.0.1',
            port=5500,
            debug=False,  # Disable debug to avoid auto-reload conflicts
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        # Stop monitoring on exit
        stop_monitoring()