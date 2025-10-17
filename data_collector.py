import pymongo
from datetime import datetime
import uuid
import platform
import psutil
import time

client = pymongo.MongoClient("mongo_uri")
try:
    client.admin.command("ping")
    print("Connected to Mongo")
except Exception as e:
    print("Connection Failed",e)

db = client['system_monitoring']
collection = db['device_metrics']

DEVICE_ID = str(uuid.getnode())

def get_system_info():
    return {
        "device_id":DEVICE_ID,
        "system":platform.system(),
        "release":platform.release(),
        "version":platform.version(),
        "machine":platform.machine(),
        "processor":platform.processor(),
        "total_ram_gb":round(psutil.virtual_memory().total/(1024**3),2),
        "cpu_count":psutil.cpu_count(logical=True)
            }
SYSTEM_INFO = get_system_info()

def collect_metrics():
    cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
    avg_cpu = sum(cpu_per_core) / len(cpu_per_core)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    battery = psutil.sensors_battery()
    if battery:
        battery_percent = battery.percent
        battery_plugged = battery.power_plugged
        battery_secs_left = battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
    else:
        battery_percent = None
        battery_plugged = None
        battery_secs_left = None

    return {
        "timestamp": datetime.utcnow(),
        "device_id": DEVICE_ID,
        "avg_cpu_percent": avg_cpu,
        "cpu_per_core_percent": cpu_per_core,
        "ram_used_percent": mem.percent,
        "disk_used_percent": disk.percent,
        "network_sent_mb": psutil.net_io_counters().bytes_sent / (1024**2),
        "network_recv_mb": psutil.net_io_counters().bytes_recv / (1024**2),
        "battery_percent": battery_percent,
        "battery_plugged": battery_plugged,
        "battery_secs_left": battery_secs_left
    }

def standardize(metrics):
    metrics["cpu_normalized"] = metrics["avg_cpu_percent"] / 100
    metrics["ram_normalized"] = metrics["ram_used_percent"] / 100
    metrics["disk_normalized"] = metrics["disk_used_percent"] / 100
    return metrics

def main():
    print("Data Collection Started")
    collection.insert_one({"system_info":SYSTEM_INFO,"start_time":datetime.utcnow()})
    while True:
        try:
            metrics = collect_metrics()
            metrics = standardize(metrics)
            collection.insert_one(metrics)
            print(f"[{metrics['timestamp']}] CPU: {metrics['avg_cpu_percent']}% | RAM: {metrics['ram_used_percent']}% | "f"Battery: {metrics['battery_percent']}% | Plugged: {metrics['battery_plugged']}")
            # break
            time.sleep(5)
        except KeyboardInterrupt:
            print("Data collection Stopped")
            break
        except Exception as e:
            print("Error",e)
            time.sleep(5)



if __name__=="__main__":
    main()
