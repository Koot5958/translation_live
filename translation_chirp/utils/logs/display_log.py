import json
import sys
import matplotlib.pyplot as plt
from datetime import datetime
import os

FOLDER = 'translation_chirp'


def load_log(filepath):
    """Charge un fichier JSON contenant les logs mémoire."""
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        sys.exit(1)

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Erreur lecture JSON : {e}")
        sys.exit(1)


def plot_log(logs, source_file):
    """Génère un graphique à partir des logs mémoire et l'enregistre."""
    timestamps = [datetime.fromtimestamp(e["timestamp"]) for e in logs]

    cpu_ram = [e.get("cpu_ram_mb") for e in logs]
    gpu_total = [e.get("gpu_total_mb") for e in logs]
    gpu_allocated = [e.get("gpu_allocated_mb") for e in logs]
    gpu_reserved = [e.get("gpu_reserved_mb") for e in logs]
    gpu_free = [e.get("gpu_free_mb") for e in logs]
    gpu_fragmentation = [e.get("gpu_fragmentation_mb") for e in logs]

    plt.figure(figsize=(14, 7))

    # CPU
    plt.plot(timestamps, cpu_ram, label="CPU RAM (MB)", linewidth=2)

    # GPU
    if any(x is not None for x in gpu_total):
        plt.plot(timestamps, gpu_total, label="GPU Total (MB)", linestyle="--")
    if any(x is not None for x in gpu_allocated):
        plt.plot(timestamps, gpu_allocated, label="GPU Allocated (MB)", linestyle="-.")
    if any(x is not None for x in gpu_reserved):
        plt.plot(timestamps, gpu_reserved, label="GPU Reserved (MB)", linestyle=":")
    if any(x is not None for x in gpu_free):
        plt.plot(timestamps, gpu_free, label="GPU Free (MB)", linestyle="--")
    if any(x is not None for x in gpu_fragmentation):
        plt.plot(timestamps, gpu_fragmentation, label="GPU Fragmentation (MB)", linestyle=":")

    plt.title(f"Memory usage over time\n{source_file}")
    plt.xlabel("Time")
    plt.ylabel("Memory (MB)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    # --- Enregistrement automatique ---
    output_dir = os.path.join(FOLDER, "logs", "plots")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(source_file))[0]
    output_path = os.path.join(output_dir, f"{base_name}.png")
    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"📁 Graph enregistré : {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Utilisation : python plot_memory_log.py <fichier_log.json> | all | delete")
        sys.exit(1)

    arg = sys.argv[1].lower()

    # -----------------------------
    # MODE DELETE
    # -----------------------------
    if arg == "delete":
        log_dirs = [
            os.path.join(FOLDER, "logs"),
            os.path.join(FOLDER, "logs", "plots"),
        ]

        total_deleted = 0
        for directory in log_dirs:
            if not os.path.exists(directory):
                print(f"⚠️ Dossier introuvable : {directory}")
                continue

            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    total_deleted += 1
                    print(f"🗑️ Supprimé : {filepath}")

        print(f"✅ Suppression terminée. {total_deleted} fichiers supprimés.")
        sys.exit(0)

    # -----------------------------
    # MODE ALL : générer tous les plots
    # -----------------------------
    if arg == "all":
        log_dir = os.path.join(FOLDER, "logs")
        if not os.path.exists(log_dir):
            print(f"⚠️ Dossier introuvable : {log_dir}")
            sys.exit(1)

        found = False
        for filename in os.listdir(log_dir):
            if filename.startswith("memory_log_") and filename.endswith(".json"):
                found = True
                filepath = os.path.join(log_dir, filename)
                logs = load_log(filepath)
                plot_log(logs, filename)

        if not found:
            print("⚠️ Aucun fichier memory_log_*.json trouvé dans logs/")
        else:
            print("✅ Tous les graphes ont été générés.")
        sys.exit(0)

    # -----------------------------
    # MODE fichier unique
    # -----------------------------
    filepath = os.path.join(FOLDER, "logs", arg)
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        sys.exit(1)

    logs = load_log(filepath)
    plot_log(logs, os.path.basename(filepath))
