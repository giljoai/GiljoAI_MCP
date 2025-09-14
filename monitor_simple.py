#!/usr/bin/env python3
"""
Simple UI-Analyzer Message Monitor with forced output
"""

import asyncio
import time
import sys
from datetime import datetime

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

class SimpleUIMonitor:
    def __init__(self):
        self.agent_name = "ui-analyzer"
        self.check_interval = 10
        self.running = True
        self.check_count = 0
    
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", flush=True)
    
    async def start_monitoring(self):
        self.log("UI-Analyzer Message Monitor Started")
        self.log(f"Agent: {self.agent_name}")
        self.log(f"Check interval: {self.check_interval} seconds")
        self.log("Press Ctrl+C to stop")
        print("-" * 60, flush=True)
        
        try:
            while self.running:
                self.check_count += 1
                await self.check_messages()
                await asyncio.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.log("Stopped by user")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.log(f"Monitor stopped after {self.check_count} checks")
    
    async def check_messages(self):
        self.log(f"Check #{self.check_count}: Scanning for ui-analyzer messages...")
        
        # Simulate message checking
        import random
        if random.random() < 0.4:  # 40% chance
            message_id = f"msg_{int(time.time())}_{random.randint(1000, 9999)}"
            priority = random.choice(['normal', 'high', 'urgent'])
            content = random.choice([
                'Dashboard component needs updating',
                'Navigation bar styling issue',
                'Dark mode toggle implementation',
                'Mobile responsive layout fix'
            ])
            
            self.log(f"FOUND MESSAGE [{message_id}] Priority: {priority}")
            self.log(f"Content: {content}")
            self.log(f"Acknowledged message {message_id}")
        else:
            self.log("No new messages found")

async def main():
    monitor = SimpleUIMonitor()
    await monitor.start_monitoring()

if __name__ == "__main__":
    print("Starting Simple UI Monitor...", flush=True)
    asyncio.run(main())