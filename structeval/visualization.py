import json
import matplotlib.pyplot as plt
import argparse
import os

def load_data(file_path):
    """Load JSON data from a file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def plot_histogram(scores, output_dir):
    """Plot and save a histogram of final evaluation scores."""
    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=10, edgecolor="black", alpha=0.7)
    plt.xlabel("Final Evaluation Score")
    plt.ylabel("Frequency")
    plt.title("Distribution of Final Evaluation Scores")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # Save plot
    hist_path = os.path.join(output_dir, "histogram.png")
    plt.savefig(hist_path)
    plt.close()
    print(f"Histogram saved to {hist_path}")

def plot_boxplot(scores, output_dir):
    """Plot and save a boxplot of final evaluation scores."""
    plt.figure(figsize=(8, 5))
    plt.boxplot(scores, vert=False, patch_artist=True, boxprops=dict(facecolor="lightblue"))
    plt.xlabel("Final Evaluation Score")
    plt.title("Boxplot of Final Evaluation Scores")
    plt.grid(axis="x", linestyle="--", alpha=0.7)

    # Save plot
    boxplot_path = os.path.join(output_dir, "boxplot.png")
    plt.savefig(boxplot_path)
    plt.close()
    print(f"Boxplot saved to {boxplot_path}")

def main():
    parser = argparse.ArgumentParser(description="Visualize evaluation results from JSON and save plots as PNG.")
    parser.add_argument("json_file", type=str, help="Path to the evaluation results JSON file")
    parser.add_argument("--output_dir", type=str, default="visualizations", help="Directory to save the output plots")

    args = parser.parse_args()

    # Load data
    data = load_data(args.json_file)

    # Extract final evaluation scores
    final_scores = [item.get("final_eval_score", 0) for item in data]

    if not final_scores:
        print("No final evaluation scores found in the JSON file.")
        return

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate and save visualizations
    plot_histogram(final_scores, args.output_dir)
    plot_boxplot(final_scores, args.output_dir)

if __name__ == "__main__":
    main()
