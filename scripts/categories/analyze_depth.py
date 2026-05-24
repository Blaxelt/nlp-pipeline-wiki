import argparse
import json
from pathlib import Path
import statistics
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def analyze_depth(depth_file: Path, graph_file: Path):
    with open(depth_file, "r", encoding="utf-8") as f:
        depth_data = json.load(f)

    if not depth_data:
        print("No data found in the file.")
        return

    with open(graph_file, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    all_categories = set(graph_data.keys())
    for parents in graph_data.values():
        all_categories.update(parents)

    total_in_graph = len(all_categories)

    depths = list(depth_data.values())

    total_categories = len(depths)
    reachable_percentage = (total_categories / total_in_graph * 100) if total_in_graph > 0 else 0
    max_depth = max(depths)
    min_depth = min(depths)
    avg_depth = sum(depths) / total_categories
    median_depth = statistics.median(depths)

    try:
        mode_depth = statistics.mode(depths)
    except statistics.StatisticsError:
        mode_depth = max(set(depths), key=depths.count)

    depth_counts = Counter(depths)
    sorted_depths = sorted(depth_counts.keys())
    counts = [depth_counts[d] for d in sorted_depths]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(sorted_depths, counts, edgecolor="black", linewidth=0.5)

    for bar, d in zip(bars, sorted_depths):
        percentage = (depth_counts[d] / total_categories) * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{percentage:.1f}%",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    ax.set_xlabel("Depth")
    ax.set_ylabel("Number of Categories")
    ax.set_title(
        f"Category Depth Distribution\n"
    )
    ax.set_xticks(sorted_depths)
    ax.tick_params(axis="x", rotation=45 if len(sorted_depths) > 20 else 0)

    plt.tight_layout()
    out_path = depth_file.parent / "depth_distribution.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved plot to {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Analyze the category depth JSON file.")
    parser.add_argument(
        "--depth-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "data" / "categories" / "category_depth.json",
        help="Path to the category_depth.json file",
    )
    parser.add_argument(
        "--graph-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "data" / "categories" / "category_graph.json",
        help="Path to the category_graph.json file",
    )
    args = parser.parse_args()

    if not args.depth_file.exists():
        print(f"Error: The file {args.depth_file} does not exist.")
        return

    if not args.graph_file.exists():
        print(f"Error: The file {args.graph_file} does not exist.")
        return

    analyze_depth(args.depth_file, args.graph_file)


if __name__ == "__main__":
    main()