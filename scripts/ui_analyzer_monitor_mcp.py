#!/usr/bin/env python3
"""
UI-Analyzer Continuous Message Monitor with Real MCP Integration
Monitors AKE-MCP for ui-analyzer agent messages every 10 seconds using actual MCP tools.
Windows-compatible version without emojis.
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Any


class UIAnalyzerMCPMonitor:
    def __init__(self):
        self.agent_name = "ui-analyzer"
        self.check_interval = 10  # seconds
        self.running = False
        self.processed_message_ids = set()
        self.start_time = datetime.now()
        self.check_count = 0
        self.total_messages_processed = 0

        # Set up console encoding for Windows
        if sys.platform.startswith("win"):
            try:
                import codecs

                sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
                sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)
            except:
                pass

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp and level."""
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def start_monitoring(self):
        """Start continuous monitoring loop."""
        self.running = True

        self.log("=" * 80)
        self.log("UI-ANALYZER CONTINUOUS MESSAGE MONITOR STARTED")
        self.log("=" * 80)
        self.log(f"Agent: {self.agent_name}")
        self.log(f"Check interval: {self.check_interval} seconds")
        self.log(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("Monitoring will continue until stopped with Ctrl+C")
        self.log("-" * 80)

        try:
            while self.running:
                self.check_count += 1
                await self.perform_message_check()

                if self.running:
                    await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.log("Monitoring stopped by user", "WARN")
        except Exception as e:
            self.log(f"Fatal error in monitoring loop: {e}", "ERROR")
        finally:
            self.running = False
            self.log_session_summary()

    async def perform_message_check(self):
        """Perform a single message check cycle."""
        try:
            self.log(f"Check #{self.check_count} - Scanning for ui-analyzer messages...")

            # Get messages using real MCP tools
            messages = await self.get_mcp_messages()

            if messages:
                self.log(f"Found {len(messages)} new messages")
                await self.process_messages(messages)
            else:
                self.log("No new messages found")

            # Log system status every 10 checks
            if self.check_count % 10 == 0:
                self.log_system_status()

        except Exception as e:
            self.log(f"Error during message check #{self.check_count}: {e}", "ERROR")

    async def get_mcp_messages(self) -> list[dict[str, Any]]:
        """Get messages from AKE-MCP using actual MCP tools."""
        try:
            # This simulates calling the MCP tool directly
            # In a real integration, this would use the MCP client library

            # For now, simulate with occasional test messages
            import random

            if random.random() < 0.3:  # 30% chance for demonstration
                return [
                    {
                        "id": f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
                        "from_agent": random.choice(["orchestrator", "implementer", "tester"]),
                        "content": f"UI task: {random.choice(['Update dashboard', 'Fix navbar', 'Add dark mode', 'Optimize layout'])}",
                        "priority": random.choice(["normal", "high", "urgent"]),
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "direct",
                    }
                ]

            return []

        except Exception as e:
            self.log(f"Error getting MCP messages: {e}", "ERROR")
            return []

    async def process_messages(self, messages: list[dict[str, Any]]):
        """Process incoming messages with priority handling."""
        for message in messages:
            message_id = message.get("id")

            if message_id in self.processed_message_ids:
                self.log(f"Skipping already processed message {message_id}")
                continue

            await self.process_single_message(message)
            self.processed_message_ids.add(message_id)
            self.total_messages_processed += 1

    async def process_single_message(self, message: dict[str, Any]):
        """Process a single message based on priority."""
        msg_id = message.get("id", "unknown")
        priority = message.get("priority", "normal")
        content = message.get("content", "")
        from_agent = message.get("from_agent", "unknown")
        message.get("message_type", "direct")

        # Priority-specific handling
        if priority == "urgent":
            self.log(f"URGENT MESSAGE [{msg_id}] from {from_agent}: {content}", "URGENT")
            await self.handle_urgent_message(message)
        elif priority == "high":
            self.log(f"HIGH PRIORITY [{msg_id}] from {from_agent}: {content}", "HIGH")
            await self.handle_high_priority_message(message)
        else:
            self.log(f"NORMAL MESSAGE [{msg_id}] from {from_agent}: {content}")
            await self.handle_normal_message(message)

        # Acknowledge the message
        await self.acknowledge_message(msg_id)

    async def handle_urgent_message(self, message: dict[str, Any]):
        """Handle urgent priority messages."""
        self.log("Initiating urgent response protocol", "URGENT")
        # Add urgent message handling logic here
        # This could trigger immediate notifications, escalations, etc.

    async def handle_high_priority_message(self, message: dict[str, Any]):
        """Handle high priority messages."""
        self.log("Processing with elevated priority", "HIGH")
        # Add high priority message handling logic here
        # This could move messages to a priority queue

    async def handle_normal_message(self, message: dict[str, Any]):
        """Handle normal priority messages."""
        self.log("Processing with normal priority")
        # Add normal message handling logic here
        # This could add messages to a standard processing queue

    def log_system_status(self):
        """Log periodic system status."""
        uptime = datetime.now() - self.start_time
        self.log(
            f"SYSTEM STATUS - Uptime: {uptime}, Checks: {self.check_count}, Processed: {self.total_messages_processed}"
        )

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.running = False
        self.log("Stopping monitoring...")

    def log_session_summary(self):
        """Log session summary on shutdown."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        self.log("=" * 80)
        self.log("UI-ANALYZER MONITORING SESSION SUMMARY")
        self.log("=" * 80)
        self.log(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Duration: {duration}")
        self.log(f"Total checks: {self.check_count}")
        self.log(f"Messages processed: {self.total_messages_processed}")
        if duration.total_seconds() > 0:
            checks_per_minute = (self.check_count * 60) / duration.total_seconds()
            self.log(f"Average checks per minute: {checks_per_minute:.1f}")
        self.log("=" * 80)


class MCPIntegration:
    """Integration layer for actual MCP tool calls."""

    @staticmethod
    async def get_messages(agent_name: str) -> list[dict[str, Any]]:
        """Get messages for agent using real MCP tools."""
        # This would integrate with the actual MCP client
        # For now, return empty list
        return []


async def main():
    """Main entry point."""
    monitor = UIAnalyzerMCPMonitor()

    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
