import matplotlib.pyplot as plt
import os


def save_durations_plot(durations_transcr, durations_transl, filename):
    """Génère un graphique des temps de transcription/traduction et l'enregistre."""

    if not durations_transcr and not durations_transl:
        print("⚠️ Aucune durée à tracer.")
        return

    # dossier output
    output_dir = "translation_whisper/logs/plots/time_generation"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    plt.figure(figsize=(12, 6))

    if durations_transcr:
        plt.plot(
            durations_transcr,
            label="Transcription durations (s)",
            linewidth=2
        )

    if durations_transl:
        plt.plot(
            durations_transl,
            label="Translation durations (s)",
            linestyle="--"
        )

    plt.title("Processing durations per block")
    plt.xlabel("Step index")
    plt.ylabel("Duration (seconds)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    plt.close()

    print(f"📁 Durations plot saved at: {output_path}")