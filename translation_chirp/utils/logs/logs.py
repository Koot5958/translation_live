import psutil
import torch
import json
import time
import os


TIME = time.strftime('%Y%m%d_%H%M%S')
LOG_FILENAME = f"translation_chirp/logs/memory_log_{TIME}.json"

if not os.path.exists(LOG_FILENAME):
    with open(LOG_FILENAME, "w") as f:
        json.dump([], f)


def log_memory():
    # CPU RAM
    mem = psutil.Process().memory_info().rss / (1024 ** 2)

    log_entry = {
        "timestamp": time.time(),
        "cpu_ram_mb": round(mem, 2),
    }

    if torch.cuda.is_available():
        total = torch.cuda.get_device_properties(0).total_memory / (1024**2)
        allocated = torch.cuda.memory_allocated() / (1024**2)
        reserved = torch.cuda.memory_reserved() / (1024**2)
        free = total - allocated
        fragmentation = reserved - allocated

        log_entry.update({
            "gpu_total_mb": round(total, 2),
            "gpu_allocated_mb": round(allocated, 2),
            "gpu_reserved_mb": round(reserved, 2),
            "gpu_free_mb": round(free, 2),
            "gpu_fragmentation_mb": round(fragmentation, 2)
        })

    # Append to JSON file
    with open(LOG_FILENAME, "r+") as f:
        data = json.load(f)
        data.append(log_entry)
        f.seek(0)
        json.dump(data, f, indent=2)