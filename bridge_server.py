import asyncio
import json
import os
from datetime import datetime

class BridgeServer:
    """
    A lightweight, zero-dependency HTTP server bridge between the CLI and Tauri.
    Allows the Tauri app to send commands and receive logs via local files/memory.
    """
    
    def __init__(self, port: int = 5001):
        self.port = port
        self.command_queue = asyncio.Queue()
        
        # Absolute path for reliability
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.public_dir = os.path.join(base_dir, "dashboard", "public")
        self.logs_path = os.path.join(self.public_dir, "logs.json")
        
        self._logs = []
        self._running = False
        
        # Ensure directory exists and logs are initialized
        os.makedirs(self.public_dir, exist_ok=True)
        self._write_logs([])

    def add_log(self, sender: str, text: str):
        """Add a log message to the dashboard buffer."""
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender": sender,
            "text": text
        }
        self._logs.append(log_entry)
        # Keep last 100 messages
        if len(self._logs) > 100:
            self._logs = self._logs[-100:]
        self._write_logs(self._logs)

    def _write_logs(self, logs):
        try:
            with open(self.logs_path, "w") as f:
                json.dump(logs, f)
        except Exception as e:
            print(f"BRIDGE: Error writing logs: {e}")

    async def start(self):
        """Start the minimal HTTP server to listen for commands."""
        self._running = True
        server = await asyncio.start_server(self._handle_client, '127.0.0.1', self.port)
        addr = server.sockets[0].getsockname()
        print(f"BRIDGE: 🌉 Command bridge active on {addr[0]}:{addr[1]}")
        
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer):
        """Handle incoming simple HTTP POST requests."""
        try:
            data = await reader.read(4096)
            request = data.decode('utf-8')
            
            # Simple HTTP Parsing (looking for POST /cmd)
            if "POST /cmd" in request:
                # Find body (after \r\n\r\n)
                parts = request.split("\r\n\r\n")
                if len(parts) > 1:
                    body = parts[1]
                    try:
                        payload = json.loads(body)
                        command = payload.get("command")
                        if command:
                            print(f"BRIDGE: 🗳️ Received command: '{command}'")
                            await self.command_queue.put(command)
                            
                            # Send 200 OK
                            response = "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}"
                            writer.write(response.encode())
                    except:
                        pass
            
            # Handle Preflight OPTIONS for CORS
            elif "OPTIONS" in request:
                response = "HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: POST, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n\r\n"
                writer.write(response.encode())
            
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception as e:
             # Silently fail for malformed requests
             pass
