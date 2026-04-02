from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

def read_corpes(filepath):
    frequencies = []
    with filepath.open('r', encoding='utf-8') as f:
        f.readline()  # skip header
        for line in f:
            parts = line.strip('\n').split('\t')
            if len(parts) >= 2:
                try:
                    frequencies.append(int(parts[1]))
                except ValueError:
                    pass
    return sorted(frequencies, reverse=True)

def read_eswiki(filepath):
    frequencies = []
    with filepath.open('r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip('\n').split('\t')
            if len(parts) >= 2:
                try:
                    frequencies.append(int(parts[1]))
                except ValueError:
                    pass
    return sorted(frequencies, reverse=True)

def to_arrays(frequencies):
    freq = np.array(frequencies)
    ranks = np.arange(1, len(freq) + 1)
    rel_freq = freq / freq.sum()
    return ranks, rel_freq

def plot_zipf():
    script_dir   = Path(__file__).resolve().parent
    corpes_path  = (script_dir / '../../data/frequency/frecuencia_formas_ortograficas_1_4.txt').resolve()
    eswiki_path  = next((script_dir / '../../data/frequency').resolve().glob('eswiki*.txt'), None)
    output_path  = script_dir / 'zipf_plot.png'

    if not corpes_path.exists():
        print(f"Error: CORPES file not found at {corpes_path}")
        return
    if eswiki_path is None or not eswiki_path.exists():
        print("Error: No eswiki frequency file found in data/frequency/")
        return

    print(f"Reading CORPES: {corpes_path}")
    corpes_ranks, corpes_rel = to_arrays(read_corpes(corpes_path))

    print(f"Reading eswiki: {eswiki_path}")
    eswiki_ranks, eswiki_rel = to_arrays(read_eswiki(eswiki_path))

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.loglog(corpes_ranks, corpes_rel, color='blue',   linewidth=1, label='CORPES')
    ax.loglog(eswiki_ranks, eswiki_rel, color='orange', linewidth=1, label='eswiki', alpha=0.8)

    ax.set_xlabel('Rank', fontsize=12)
    ax.set_ylabel('Relative frequency', fontsize=12)
    ax.set_title('Zipf distribution — Orthographic forms', fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, which='both', linestyle=':', linewidth=0.5, alpha=0.7)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Graph saved to: {output_path}")

if __name__ == '__main__':
    plot_zipf()