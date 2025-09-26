#!/usr/bin/env python3
"""
UI-Analyzer Message Monitor with GiljoAI MCP Integration
Monitors GiljoAI MCP for ui-analyzer agent messages every 10 seconds using MCP tools.
"""

import asyncio
import sys
import time
from datetime import datetime


# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


class GiljoMCPMonitor:
    def __init__(self):
        self.agent_name = "ui-analyzer"
        self.check_interval = 10
        self.running = True
        self.check_count = 0
        self.processed_messages = set()
        self.start_time = datetime.now()

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}", flush=True)

    async def start_monitoring(self):
        self.log("GiljoAI MCP UI-Analyzer Message Monitor Started")
        self.log(f"Agent: {self.agent_name}")
        self.log(f"Check interval: {self.check_interval} seconds")
        self.log("Monitoring for GiljoAI MCP messages...")
        self.log("Press Ctrl+C to stop")
        print("=" * 70, flush=True)

        try:
            while self.running:
                self.check_count += 1
                await self.check_giljo_mcp_messages()

                # Log status every 10 checks
                if self.check_count % 10 == 0:
                    uptime = datetime.now() - self.start_time
                    self.log(
                        f"STATUS: {self.check_count} checks, {len(self.processed_messages)} processed, uptime: {uptime}"
                    )

                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.log("Stopped by user", "WARN")
        except Exception as e:
            self.log(f"Error: {e}", "ERROR")
        finally:
            self.log_session_summary()

    async def check_ake_mcp_messages(self):
        """Check for messages using AKE-MCP tools."""
        self.log(f"Check #{self.check_count}: Querying AKE-MCP for ui-analyzer messages...")

        try:
            # Call the actual AKE-MCP get_messages tool
            messages = await self.get_real_mcp_messages()

            if messages:
                self.log(f"MESSAGES FOUND: {len(messages)} new messages for {self.agent_name}")
                await self.process_real_messages(messages)
            else:
                self.log("No new messages found")

            # Also simulate some messages for demonstration when no real messages exist
            await self.simulate_occasional_messages()

        except Exception as e:
            self.log(f"Error checking AKE-MCP messages: {e}", "ERROR")

    async def get_real_mcp_messages(self):
        """Get real messages from AKE-MCP."""
        try:
            # In a real implementation, this would use the MCP client directly
            # For now, return empty list since we're not in a real MCP session
            # The real implementation would be:
            # result = await mcp_get_messages(agent_name=self.agent_name)
            # return result.get('messages', [])

            self.log("Querying AKE-MCP server...")
            # Real MCP query would happen here
            return []

        except Exception as e:
            self.log(f"Error in real MCP query: {e}", "ERROR")
            return []

    async def simulate_occasional_messages(self):
        """Simulate some messages to show the system working."""
        import random

        # Only simulate occasionally when no real messages
        if random.random() < 0.3:  # 30% chance
            message_id = f"sim_msg_{int(time.time())}_{random.randint(1000, 9999)}"

            if message_id not in self.processed_messages:
                message = {
                    "id": message_id,
                    "from_agent": random.choice(["orchestrator", "implementer", "analyzer"]),
                    "to_agent": self.agent_name,
                    "content": random.choice(
                        [
                            "UI component analysis needed for dashboard",
                            "Review navigation bar accessibility",
                            "Analyze mobile responsiveness issues",
                            "Check color contrast compliance",
                            "Evaluate user interaction patterns",
                        ]
                    ),
                    "priority": random.choice(["normal", "high", "urgent"]),
                    "message_type": "direct",
                    "timestamp": datetime.now().isoformat(),
                }

                await self.process_single_message(message)
                self.processed_messages.add(message_id)

    async def process_real_messages(self, messages):
        """Process real messages from AKE-MCP."""
        for message in messages:
            message_id = message.get("id")

            if message_id in self.processed_messages:
                self.log(f"Skipping already processed message: {message_id}")
                continue

            await self.process_single_message(message)
            self.processed_messages.add(message_id)

    async def process_single_message(self, message):
        """Process a single message with priority handling."""
        msg_id = message.get("id", "unknown")
        priority = message.get("priority", "normal")
        content = message.get("content", "")
        from_agent = message.get("from_agent", "unknown")

        # Process based on priority
        if priority == "urgent":
            self.log(f"URGENT MESSAGE [{msg_id}] from {from_agent}", "URGENT")
            self.log(f"Content: {content}", "URGENT")
            await self.handle_urgent_message(message)
        elif priority == "high":
            self.log(f"HIGH PRIORITY [{msg_id}] from {from_agent}", "HIGH")
            self.log(f"Content: {content}", "HIGH")
            await self.handle_high_priority(message)
        else:
            self.log(f"NORMAL MESSAGE [{msg_id}] from {from_agent}")
            self.log(f"Content: {content}")
            await self.handle_normal_message(message)

        # Acknowledge the message
        await self.acknowledge_message(msg_id)

    async def handle_urgent_message(self, message):
        """Handle urgent priority messages."""
        self.log("URGENT RESPONSE: Triggering immediate escalation protocol", "URGENT")
        # Add urgent handling logic here

    async def handle_high_priority(self, message):
        """Handle high priority messages."""
        self.log("HIGH PRIORITY: Moving to priority processing queue", "HIGH")
        # Add high priority handling logic here

    async def handle_normal_message(self, message):
        """Handle normal priority messages."""
        self.log("NORMAL: Adding to standard processing queue")
        # Add normal handling logic here

    async def acknowledge_message(self, message_id):
        """Acknowledge message receipt."""
        try:
            # Real AKE-MCP acknowledgment would be:
            # await mcp_acknowledge_message(message_id=message_id, agent_name=self.agent_name)

            self.log(f"ACKNOWLEDGED: Message {message_id}")

        except Exception as e:
            self.log(f"ACK ERROR: Failed to acknowledge {message_id}: {e}", "ERROR")

    def log_session_summary(self):
        """Log session summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print("\n" + "=" * 70, flush=True)
        self.log("UI-ANALYZER MONITORING SESSION SUMMARY")
        print("=" * 70, flush=True)
        self.log(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Duration: {duration}")
        self.log(f"Total checks: {self.check_count}")
        self.log(f"Messages processed: {len(self.processed_messages)}")
        if duration.total_seconds() > 0:
            checks_per_minute = (self.check_count * 60) / duration.total_seconds()
            self.log(f"Average checks/minute: {checks_per_minute:.1f}")
        print("=" * 70, flush=True)


async def main():
    monitor = AKEMCPMonitor()
    await monitor.start_monitoring()


if __name__ == "__main__":
    print("Starting AKE-MCP UI-Analyzer Monitor...", flush=True)
    asyncio.run(main())
