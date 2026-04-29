import argparse
import json
from pathlib import Path
import statistics
from collections import Counter

def analyze_depth(depth_file: Path, graph_file: Path):
    print(f"Loading data from {depth_file} ...")
    with open(depth_file, "r", encoding="utf-8") as f:
        depth_data = json.load(f)

    if not depth_data:
        print("No data found in the file.")
        return

    print(f"Loading graph data from {graph_file} ...")
    with open(graph_file, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    # Calculate total unique categories in the graph (keys + all parents)
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

    print("\n--- Category Reachability & Depth Statistics ---")
    print(f"Total categories in graph:  {total_in_graph:,}")
    print(f"Total categories reachable: {total_categories:,} ({reachable_percentage:.2f}% of graph)")
    print(f"Maximum depth:              {max_depth}")
    print(f"Minimum depth:              {min_depth}")
    print(f"Average (Mean) depth:       {avg_depth:.2f}")
    print(f"Median depth:               {median_depth}")
    print(f"Mode depth:                 {mode_depth}")
    
    print("\n--- Depth Distribution ---")
    depth_counts = Counter(depths)
    
    print(f"{'Depth':>6} | {'Count':>12} | {'Percentage':>10}")
    print("-" * 36)
    
    for d in sorted(depth_counts.keys()):
        count = depth_counts[d]
        percentage = (count / total_categories) * 100
        print(f"{d:>6} | {count:>12,} | {percentage:>9.2f}%")

def main():
    parser = argparse.ArgumentParser(description="Analyze the category depth JSON file.")
    parser.add_argument(
        "--depth-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "categories" / "category_depth.json",
        help="Path to the category_depth.json file",
    )
    parser.add_argument(
        "--graph-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "categories" / "category_graph.json",
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
