import os
import json
import uuid
import psutil
import httpx
import asyncio
import socket
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "http://localhost:8000/api/ping" # Local testing
# SERVER_URL = "http://13.125.105.188:8000/api/ping" # Production (set via env or script)
SERVER_NAME = socket.gethostname()

def get_mac_address():
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])
    return mac

def get_uptime():
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    delta = now - boot_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"up {days}d {hours}h {minutes}m"

def get_detailed_specs():
    specs = {
        "CPU Model": "Unknown",
        "CPU Cores": psutil.cpu_count(logical=True),
        "Total RAM": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "Disk Size": f"{round(psutil.disk_usage('/').total / (1024**3), 2)} GB",
        "OS": os.uname().sysname + " " + os.uname().release
    }
    # Try to get CPU model on Linux
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    specs["CPU Model"] = line.split(":")[1].strip()
                    break
    except:
        pass
    return specs

async def send_ping():
    data = {
        "hardware_id": get_mac_address(),
        "server_name": SERVER_NAME,
        "ip_address": socket.gethostbyname(SERVER_NAME),
        "cpu_usage": psutil.cpu_percent(interval=1),
        "mem_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "uptime": get_uptime(),
        "specs": json.dumps(get_detailed_specs())
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SERVER_URL, json=data, timeout=10.0)
            print(f"Ping sent: {response.status_code}")
        except Exception as e:
            print(f"Error sending ping: {e}")

if __name__ == "__main__":
    asyncio.run(send_ping())
