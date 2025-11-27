import psutil
import torch
import json
import time
import os


LOG_FILENAME = f"translation_final/logs/memory_log_{time.strftime('%Y%m%d_%H%M%S')}.json"

if not os.path.exists(LOG_FILENAME):
    with open(LOG_FILENAME, "w") as f:
        json.dump([], f)


def log_memory():
    # Mesures CPU/GPU
    mem = psutil.Process().memory_info().rss / (1024 ** 2)

    if torch.cuda.is_available():
        gpu_mem = torch.cuda.memory_allocated() / (1024 ** 2)
        gpu_cached = torch.cuda.memory_reserved() / (1024 ** 2)
    else:
        gpu_mem = None
        gpu_cached = None

    # Objet JSON pour le log
    log_entry = {
        "timestamp": time.time(),
        "cpu_ram_mb": round(mem, 2),
        "gpu_mem_mb": round(gpu_mem, 2) if gpu_mem is not None else None,
        "gpu_cached_mb": round(gpu_cached, 2) if gpu_cached is not None else None,
    }

    # Append to JSON file
    with open(LOG_FILENAME, "r+") as f:
        data = json.load(f)
        data.append(log_entry)
        f.seek(0)
        json.dump(data, f, indent=2)