import os
import json
import uuid
import psutil
import httpx
import asyncio
import socket
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "https://qewr.link/api/ping" # Production
SERVER_NAME = socket.gethostname()

def get_mac_address():
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        
        # Priority 1: Integrated/PCI Ethernet (eno, enp, eth)
        priority_prefixes = ['eno', 'enp', 'eth']
        for prefix in priority_prefixes:
            for interface in sorted(addrs.keys()):
                if interface.startswith(prefix):
                    for addr in addrs[interface]:
                        if hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:
                            return addr.address.lower()
                        elif addr.family == socket.AF_PACKET: # Fallback for some linux envs
                            return addr.address.lower()

        # Priority 2: Any other physical-looking ethernet or wifi (en, wl)
        for interface in sorted(addrs.keys()):
            if interface.startswith(('en', 'wl')):
                for addr in addrs[interface]:
                    if hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:
                        return addr.address.lower()
                    elif addr.family == socket.AF_PACKET:
                        return addr.address.lower()
    except Exception as e:
        print(f"Error determining MAC: {e}")

    # Final Fallback: uuid.getnode()
    return ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8*6, 8)][::-1])

def get_public_ip():
    try:
        # Get public IP via ipify
        with httpx.Client(timeout=2.0) as client:
            return client.get('https://api.ipify.org').text
    except:
        return "unknown"

def get_all_ips():
    ips = []
    try:
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    ips.append(f"{interface}:{addr.address}")
    except:
        pass
    return ", ".join(ips)

def get_uptime():
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        now = datetime.now()
        delta = now - boot_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"up {days}d {hours}h {minutes}m"
    except:
        return "unknown"

def get_detailed_specs():
    specs = {
        "CPU Model": "Unknown",
        "CPU Cores": psutil.cpu_count(logical=True),
        "Total RAM": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        "Disk Size": f"{round(psutil.disk_usage('/').total / (1024**3), 2)} GB",
        "OS": os.uname().sysname + " " + os.uname().release,
        "All IPs": get_all_ips()
    }
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    specs["CPU Model"] = line.split(":")[1].strip()
                    break
    except:
        pass

    # Check git repository version for nmap_multi_v1
    git_version = "Not Installed"
    for base_dir in ["/home/ubuntu", "/root"]:
        repo_path = os.path.join(base_dir, "nmap_multi_v1")
        if os.path.exists(os.path.join(repo_path, ".git")):
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "-C", repo_path, "log", "-1", "--format=%h (%ad) - %s", "--date=short"],
                    capture_output=True, text=True, check=True
                )
                git_version = result.stdout.strip()
                break
            except Exception as e:
                git_version = f"Error: {str(e)}"
                break
    specs["nmap_multi_v1 version"] = git_version

    return specs

async def send_ping():
    public_ip = get_public_ip()
    data = {
        "hardware_id": get_mac_address(),
        "server_name": SERVER_NAME,
        "ip_address": public_ip if public_ip != "unknown" else socket.gethostbyname(SERVER_NAME),
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
