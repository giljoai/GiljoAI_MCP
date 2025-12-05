#!/usr/bin/env python3
"""
Continuous UI-Analyzer Message Monitor
Monitors AKE-MCP for ui-analyzer agent messages every 10 seconds.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime


class ContinuousUIMonitor:
    def __init__(self):
        self.agent_name = "ui-analyzer"
        self.check_interval = 10  # seconds
        self.running = False
        self.processed_messages = set()
        self.start_time = datetime.now()
        self.check_count = 0

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(f"ui_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_monitoring()

    async def start_monitoring(self):
        """Start the continuous monitoring loop."""
        self.running = True
        self.logger.info("=" * 60)
        self.logger.info("🚀 UI-ANALYZER CONTINUOUS MESSAGE MONITOR STARTED")
        self.logger.info("=" * 60)
        self.logger.info(f"📍 Agent: {self.agent_name}")
        self.logger.info(f"⏱️  Check interval: {self.check_interval} seconds")
        self.logger.info(f"🕐 Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("🔄 Monitoring will continue until stopped with Ctrl+C")
        self.logger.info("-" * 60)

        try:
            while self.running:
                self.check_count += 1
                await self.perform_message_check()

                if self.running:
                    await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            self.logger.info("🛑 Monitoring cancelled")
        except Exception as e:
            self.logger.exception(f"❌ Fatal error in monitoring loop: {e}")
        finally:
            self.log_session_summary()

    async def perform_message_check(self):
        """Perform a single message check cycle."""
        try:
            datetime.now()
            self.logger.info(f"🔍 Check #{self.check_count} - Scanning for ui-analyzer messages...")

            # This would be the actual MCP call - for now we simulate
            # In real implementation, this would be replaced with:
            # messages = await self.get_mcp_messages()
            messages = await self.simulate_message_check()

            if messages:
                self.logger.info(f"📬 Found {len(messages)} new messages")
                await self.process_messages(messages)
            else:
                self.logger.info("📭 No new messages")

            # Log system status every 10 checks
            if self.check_count % 10 == 0:
                await self.log_system_status()

        except Exception as e:
            self.logger.exception(f"❌ Error during message check #{self.check_count}: {e}")

    async def simulate_message_check(self):
        """Simulate message checking - replace with actual MCP call."""
        # In production, this would be:
        # return await mcp_get_messages(agent_name=self.agent_name)

        # Simulate occasional messages for demonstration
        import random

        if random.random() < 0.2:  # 20% chance
            return [
                {
                    "id": f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
                    "from_agent": "orchestrator",
                    "content": f"UI analysis task #{random.randint(1, 100)}",
                    "priority": random.choice(["normal", "high", "urgent"]),
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        return []

    async def get_mcp_messages(self):
        """Get actual messages from MCP - placeholder for real implementation."""
        # This is where the actual MCP tool call would go:
        # result = await mcp_get_messages(agent_name=self.agent_name)
        # return result.get('messages', [])

    async def process_messages(self, messages):
        """Process incoming messages with priority handling."""
        for message in messages:
            message_id = message.get("id")

            if message_id in self.processed_messages:
                self.logger.debug(f"⏭️  Skipping already processed message {message_id}")
                continue

            await self.process_single_message(message)
            self.processed_messages.add(message_id)

    async def process_single_message(self, message):
        """Process a single message based on priority."""
        msg_id = message.get("id", "unknown")
        priority = message.get("priority", "normal")
        content = message.get("content", "")
        from_agent = message.get("from_agent", "unknown")

        # Priority-specific handling
        if priority == "urgent":
            self.logger.warning(f"🚨 URGENT [{msg_id}] from {from_agent}: {content}")
            await self.handle_urgent_message(message)
        elif priority == "high":
            self.logger.info(f"⚠️  HIGH [{msg_id}] from {from_agent}: {content}")
            await self.handle_high_priority_message(message)
        else:
            self.logger.info(f"📨 NORMAL [{msg_id}] from {from_agent}: {content}")
            await self.handle_normal_message(message)

        # Acknowledge the message
        await self.acknowledge_message(msg_id)

    async def handle_urgent_message(self, message):
        """Handle urgent priority messages."""
        self.logger.warning("⚡ Initiating urgent response protocol")
        # Add urgent message handling logic here

    async def handle_high_priority_message(self, message):
        """Handle high priority messages."""
        self.logger.info("🏃 Processing with elevated priority")
        # Add high priority message handling logic here

    async def handle_normal_message(self, message):
        """Handle normal priority messages."""
        self.logger.info("📝 Processing normally")
        # Add normal message handling logic here

    async def log_system_status(self):
        """Log periodic system status."""
        uptime = datetime.now() - self.start_time
        self.logger.info(
            f"📊 STATUS - Uptime: {uptime}, Checks: {self.check_count}, Processed: {len(self.processed_messages)}"
        )

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.running = False
        self.logger.info("🛑 Stopping monitoring...")

    def log_session_summary(self):
        """Log session summary on shutdown."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        self.logger.info("=" * 60)
        self.logger.info("📋 UI-ANALYZER MONITORING SESSION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"🕐 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"🕑 Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"⏱️  Duration: {duration}")
        self.logger.info(f"🔄 Total checks: {self.check_count}")
        self.logger.info(f"📨 Messages processed: {len(self.processed_messages)}")
        self.logger.info("=" * 60)


async def main():
    """Main entry point."""
    monitor = ContinuousUIMonitor()
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
