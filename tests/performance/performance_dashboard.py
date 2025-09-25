"""
Performance Dashboard and Real-time Monitoring
Provides real-time performance metrics and historical analysis

Features:
- Real-time performance monitoring
- Historical trend analysis
- Bottleneck identification
- GTM readiness scorecard
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psutil


class PerformanceDashboard:
    """Real-time performance monitoring dashboard"""

    def __init__(self):
        self.metrics_history = []
        self.performance_thresholds = {
            "agent_creation_ms": 100,
            "message_send_ms": 100,
            "websocket_connection_ms": 1000,
            "database_query_ms": 50,
            "vision_chunking_ms": 5000,
            "memory_usage_mb": 2000,
            "cpu_usage_percent": 80,
        }
        self.dashboard_data = {
            "current_metrics": {},
            "alerts": [],
            "trend_data": {},
            "production_readiness": {"score": 0, "components": {}},
        }

    def capture_system_metrics(self) -> dict[str, Any]:
        """Capture current system performance metrics"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB

            return {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_total_gb": memory.total / (1024**3),
                    "memory_available_gb": memory.available / (1024**3),
                    "memory_used_percent": memory.percent,
                    "process_memory_mb": process_memory,
                },
                "performance": {
                    "agent_creation_ms": None,  # To be updated by tests
                    "message_send_ms": None,
                    "websocket_connection_ms": None,
                    "database_query_ms": None,
                    "vision_chunking_ms": None,
                },
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": f"Failed to capture metrics: {e}",
                "system": {},
                "performance": {},
            }

    def update_performance_metric(self, metric_name: str, value: float):
        """Update a specific performance metric"""
        current_time = datetime.now().isoformat()

        if not self.dashboard_data["current_metrics"]:
            self.dashboard_data["current_metrics"] = self.capture_system_metrics()

        # Update the specific metric
        self.dashboard_data["current_metrics"]["performance"][metric_name] = value
        self.dashboard_data["current_metrics"]["timestamp"] = current_time

        # Check thresholds and generate alerts
        self._check_thresholds(metric_name, value)

        # Update trend data
        self._update_trend_data(metric_name, value)

    def _check_thresholds(self, metric_name: str, value: float):
        """Check if metric exceeds thresholds and generate alerts"""
        threshold = self.performance_thresholds.get(metric_name)
        if threshold and value > threshold:
            alert = {
                "timestamp": datetime.now().isoformat(),
                "type": "PERFORMANCE_WARNING",
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "severity": "HIGH" if value > threshold * 2 else "MEDIUM",
                "message": f"{metric_name} ({value:.2f}) exceeds threshold ({threshold})",
            }
            self.dashboard_data["alerts"].append(alert)

            # Keep only last 50 alerts
            self.dashboard_data["alerts"] = self.dashboard_data["alerts"][-50:]

    def _update_trend_data(self, metric_name: str, value: float):
        """Update historical trend data"""
        if metric_name not in self.dashboard_data["trend_data"]:
            self.dashboard_data["trend_data"][metric_name] = []

        trend_point = {"timestamp": datetime.now().isoformat(), "value": value}

        self.dashboard_data["trend_data"][metric_name].append(trend_point)

        # Keep only last 100 data points per metric
        self.dashboard_data["trend_data"][metric_name] = self.dashboard_data["trend_data"][metric_name][-100:]

    def calculate_production_readiness_score(self) -> dict[str, Any]:
        """Calculate overall production readiness score"""
        current_metrics = self.dashboard_data["current_metrics"]
        if not current_metrics.get("performance"):
            return {"score": 0, "components": {}}

        performance = current_metrics["performance"]
        components = {}
        total_score = 0
        component_count = 0

        # Agent Performance (25% weight)
        if performance.get("agent_creation_ms") is not None:
            agent_score = (
                100
                if performance["agent_creation_ms"] <= 100
                else max(0, 100 - (performance["agent_creation_ms"] - 100))
            )
            components["agent_performance"] = {
                "score": agent_score,
                "weight": 0.25,
                "status": "GOOD" if agent_score >= 80 else "POOR",
            }
            total_score += agent_score * 0.25
            component_count += 1

        # Message Queue Performance (25% weight)
        if performance.get("message_send_ms") is not None:
            message_score = (
                100 if performance["message_send_ms"] <= 100 else max(0, 100 - (performance["message_send_ms"] - 100))
            )
            components["message_performance"] = {
                "score": message_score,
                "weight": 0.25,
                "status": "GOOD" if message_score >= 80 else "POOR",
            }
            total_score += message_score * 0.25
            component_count += 1

        # WebSocket Performance (20% weight)
        if performance.get("websocket_connection_ms") is not None:
            ws_score = (
                100
                if performance["websocket_connection_ms"] <= 1000
                else max(0, 100 - (performance["websocket_connection_ms"] - 1000) / 20)
            )
            components["websocket_performance"] = {
                "score": ws_score,
                "weight": 0.20,
                "status": "GOOD" if ws_score >= 80 else "POOR",
            }
            total_score += ws_score * 0.20
            component_count += 1

        # Database Performance (20% weight)
        if performance.get("database_query_ms") is not None:
            db_score = (
                100
                if performance["database_query_ms"] <= 50
                else max(0, 100 - (performance["database_query_ms"] - 50) * 2)
            )
            components["database_performance"] = {
                "score": db_score,
                "weight": 0.20,
                "status": "GOOD" if db_score >= 80 else "POOR",
            }
            total_score += db_score * 0.20
            component_count += 1

        # Vision Processing Performance (10% weight)
        if performance.get("vision_chunking_ms") is not None:
            vision_score = (
                100
                if performance["vision_chunking_ms"] <= 5000
                else max(0, 100 - (performance["vision_chunking_ms"] - 5000) / 100)
            )
            components["vision_performance"] = {
                "score": vision_score,
                "weight": 0.10,
                "status": "GOOD" if vision_score >= 80 else "POOR",
            }
            total_score += vision_score * 0.10
            component_count += 1

        # System Health (bonus points)
        system = current_metrics.get("system", {})
        cpu_health = 100 - max(0, system.get("cpu_percent", 0) - 80)
        memory_health = 100 - max(0, system.get("memory_used_percent", 0) - 90)

        components["system_health"] = {
            "cpu_score": cpu_health,
            "memory_score": memory_health,
            "overall_score": (cpu_health + memory_health) / 2,
            "status": "GOOD" if (cpu_health + memory_health) / 2 >= 80 else "POOR",
        }

        overall_score = total_score if component_count > 0 else 0

        return {
            "score": round(overall_score, 1),
            "components": components,
            "status": self._get_status_label(overall_score),
        }

    def _get_status_label(self, score: float) -> str:
        """Get status label based on score"""
        if score >= 90:
            return "PRODUCTION_READY"
        if score >= 75:
            return "MOSTLY_READY"
        if score >= 50:
            return "NEEDS_IMPROVEMENT"
        return "NOT_READY"

    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard for web viewing"""
        readiness = self.calculate_production_readiness_score()
        current_metrics = self.dashboard_data["current_metrics"]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GiljoAI MCP Performance Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .score-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .metric-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                .metric-label {{ color: #7f8c8d; font-size: 14px; margin-bottom: 5px; }}
                .status-good {{ color: #27ae60; }}
                .status-poor {{ color: #e74c3c; }}
                .status-warning {{ color: #f39c12; }}
                .alert {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 5px 0; }}
                .alert-high {{ background: #f8d7da; border-color: #f5c6cb; }}
                .progress-bar {{ width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }}
                .progress-fill {{ height: 100%; background: linear-gradient(90deg, #e74c3c 0%, #f39c12 50%, #27ae60 100%); transition: width 0.3s; }}
                .timestamp {{ color: #95a5a6; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 GiljoAI MCP Performance Dashboard</h1>
                    <p>Production Readiness Monitoring for 100+ Concurrent Agents</p>
                    <div class="timestamp">Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>

                <div class="score-card">
                    <h2>Production Readiness Score</h2>
                    <div class="metric-value status-{"good" if readiness["score"] >= 75 else "poor"}">
                        {readiness["score"]:.1f}%
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {readiness["score"]}%"></div>
                    </div>
                    <p><strong>Status:</strong> <span class="status-{"good" if readiness["status"] == "PRODUCTION_READY" else "poor"}">{readiness["status"].replace("_", " ")}</span></p>
                </div>

                <div class="metric-grid">
        """

        # Add performance metrics
        if current_metrics.get("performance"):
            perf = current_metrics["performance"]

            metrics_to_show = [
                ("Agent Creation", "agent_creation_ms", "ms", 100),
                ("Message Send", "message_send_ms", "ms", 100),
                ("WebSocket Connection", "websocket_connection_ms", "ms", 1000),
                ("Database Query", "database_query_ms", "ms", 50),
                ("Vision Chunking", "vision_chunking_ms", "ms", 5000),
            ]

            for name, key, unit, threshold in metrics_to_show:
                value = perf.get(key)
                if value is not None:
                    status_class = "status-good" if value <= threshold else "status-poor"
                    html += f"""
                    <div class="metric-card">
                        <div class="metric-label">{name}</div>
                        <div class="metric-value {status_class}">{value:.2f} {unit}</div>
                        <div>Threshold: {threshold} {unit}</div>
                    </div>
                    """

        # Add system metrics
        if current_metrics.get("system"):
            sys = current_metrics["system"]

            html += f"""
            <div class="metric-card">
                <div class="metric-label">CPU Usage</div>
                <div class="metric-value status-{"good" if sys.get("cpu_percent", 0) < 80 else "poor"}">{sys.get("cpu_percent", 0):.1f}%</div>
                <div>Threshold: 80%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Memory Usage</div>
                <div class="metric-value status-{"good" if sys.get("memory_used_percent", 0) < 90 else "poor"}">{sys.get("memory_used_percent", 0):.1f}%</div>
                <div>Available: {sys.get("memory_available_gb", 0):.1f}GB</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Process Memory</div>
                <div class="metric-value status-{"good" if sys.get("process_memory_mb", 0) < 2000 else "poor"}">{sys.get("process_memory_mb", 0):.1f} MB</div>
                <div>Threshold: 2000 MB</div>
            </div>
            """

        html += """
                </div>
        """

        # Add alerts section
        if self.dashboard_data["alerts"]:
            html += """
            <div class="score-card">
                <h2>Recent Alerts</h2>
            """

            for alert in self.dashboard_data["alerts"][-10:]:  # Show last 10 alerts
                alert_class = "alert-high" if alert.get("severity") == "HIGH" else "alert"
                html += f"""
                <div class="{alert_class}">
                    <strong>{alert.get("type", "ALERT")}:</strong> {alert.get("message", "Unknown alert")}
                    <div class="timestamp">{alert.get("timestamp", "Unknown time")}</div>
                </div>
                """

            html += "</div>"

        # Add component breakdown
        if readiness.get("components"):
            html += """
            <div class="score-card">
                <h2>Component Performance Breakdown</h2>
                <div class="metric-grid">
            """

            for component, data in readiness["components"].items():
                if component != "system_health":
                    score = data.get("score", 0)
                    status_class = "status-good" if score >= 80 else "status-poor"
                    html += f"""
                    <div class="metric-card">
                        <div class="metric-label">{component.replace("_", " ").title()}</div>
                        <div class="metric-value {status_class}">{score:.1f}%</div>
                        <div>Weight: {data.get("weight", 0) * 100:.0f}%</div>
                    </div>
                    """

            html += "</div></div>"

        html += """
            </div>
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(() => location.reload(), 30000);
            </script>
        </body>
        </html>
        """

        return html

    def save_dashboard_html(self, filename: str = "performance_dashboard.html"):
        """Save dashboard as HTML file"""
        html_content = self.generate_dashboard_html()

        dashboard_file = Path(filename)
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return dashboard_file

    def export_metrics_json(self, filename: str = "performance_metrics.json"):
        """Export all metrics to JSON file"""
        # Update production readiness before export
        self.dashboard_data["production_readiness"] = self.calculate_production_readiness_score()

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "dashboard_data": self.dashboard_data,
            "thresholds": self.performance_thresholds,
        }

        json_file = Path(filename)
        with open(json_file, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return json_file

    def print_realtime_summary(self):
        """Print real-time summary to console"""
        self.calculate_production_readiness_score()
        current_metrics = self.dashboard_data["current_metrics"]


        if current_metrics.get("performance"):
            perf = current_metrics["performance"]

            for metric, value in perf.items():
                if value is not None:
                    self.performance_thresholds.get(metric, 0)

        if current_metrics.get("system"):
            current_metrics["system"]

        # Show recent alerts
        recent_alerts = [
            a
            for a in self.dashboard_data["alerts"]
            if datetime.fromisoformat(a["timestamp"]) > datetime.now() - timedelta(minutes=5)
        ]

        if recent_alerts:
            for _alert in recent_alerts[-3:]:  # Show last 3
                pass


class PerformanceMonitor:
    """Continuous performance monitoring"""

    def __init__(self, dashboard: PerformanceDashboard):
        self.dashboard = dashboard
        self.monitoring = False

    async def start_monitoring(self, interval_seconds: int = 5):
        """Start continuous performance monitoring"""
        self.monitoring = True

        while self.monitoring:
            try:
                # Capture current metrics
                metrics = self.dashboard.capture_system_metrics()
                self.dashboard.dashboard_data["current_metrics"] = metrics

                # Print summary every 30 seconds
                if int(time.time()) % 30 == 0:
                    self.dashboard.print_realtime_summary()

                # Save dashboard every 60 seconds
                if int(time.time()) % 60 == 0:
                    self.dashboard.save_dashboard_html()

                await asyncio.sleep(interval_seconds)

            except Exception:
                await asyncio.sleep(interval_seconds)

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False


# Example usage and testing
async def demo_dashboard():
    """Demonstrate dashboard functionality"""
    dashboard = PerformanceDashboard()
    PerformanceMonitor(dashboard)

    # Simulate some performance metrics
    dashboard.update_performance_metric("agent_creation_ms", 85.5)
    dashboard.update_performance_metric("message_send_ms", 45.2)
    dashboard.update_performance_metric("websocket_connection_ms", 750.0)
    dashboard.update_performance_metric("database_query_ms", 35.1)
    dashboard.update_performance_metric("vision_chunking_ms", 4200.0)

    # Generate dashboard
    dashboard.save_dashboard_html()
    dashboard.export_metrics_json()
    dashboard.print_realtime_summary()



if __name__ == "__main__":
    # Run dashboard demo
    asyncio.run(demo_dashboard())
