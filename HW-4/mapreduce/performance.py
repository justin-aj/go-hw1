import time
import json
import requests
import matplotlib.pyplot as plt
import numpy as np

# ============================================
# UPDATE THESE WITH YOUR ACTUAL ECS TASK IPs
# ============================================
SPLITTER_IP = "54.242.77.54"
MAPPER_IPS = ["3.80.46.153", "44.210.242.179", "35.175.138.163"]
REDUCER_IP = "54.227.180.1"
BUCKET = "ajin-mapreduce-bucket"

def time_request(url):
    """Send GET request and return response time in seconds."""
    start = time.time()
    resp = requests.get(url)
    elapsed = time.time() - start
    return elapsed, resp.json()

def run_sequential():
    """Run all mapping through a single mapper (sequential)."""
    print("\n=== Sequential (1 Mapper) ===")
    
    # Split
    split_time, split_resp = time_request(
        f"http://{SPLITTER_IP}:8080/split?bucket={BUCKET}&key=shakespeare-hamlet.txt"
    )
    print(f"  Split: {split_time:.3f}s")

    # Map all 3 chunks through one mapper sequentially
    mapper_ip = MAPPER_IPS[0]
    total_map_time = 0
    for i in range(3):
        map_time, map_resp = time_request(
            f"http://{mapper_ip}:8080/map?bucket={BUCKET}&key=chunks/chunk_{i}.txt&output_key=results/seq_mapper_{i}.json"
        )
        total_map_time += map_time
        print(f"  Map chunk {i}: {map_time:.3f}s")

    # Reduce
    reduce_time, reduce_resp = time_request(
        f"http://{REDUCER_IP}:8080/reduce?bucket={BUCKET}&keys=results/seq_mapper_0.json,results/seq_mapper_1.json,results/seq_mapper_2.json"
    )
    print(f"  Reduce: {reduce_time:.3f}s")

    total = split_time + total_map_time + reduce_time
    print(f"  TOTAL: {total:.3f}s")
    return {
        "split": split_time,
        "map": total_map_time,
        "reduce": reduce_time,
        "total": total
    }

def run_parallel():
    """Run mapping across 3 separate mappers (parallel via sequential calls, but on different machines)."""
    import concurrent.futures

    print("\n=== Parallel (3 Mappers) ===")

    # Split
    split_time, split_resp = time_request(
        f"http://{SPLITTER_IP}:8080/split?bucket={BUCKET}&key=shakespeare-hamlet.txt"
    )
    print(f"  Split: {split_time:.3f}s")

    # Map in parallel using threads
    map_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i in range(3):
            url = f"http://{MAPPER_IPS[i]}:8080/map?bucket={BUCKET}&key=chunks/chunk_{i}.txt&output_key=results/par_mapper_{i}.json"
            futures.append(executor.submit(time_request, url))
        
        results = [f.result() for f in futures]
        for i, (t, resp) in enumerate(results):
            print(f"  Map chunk {i}: {t:.3f}s")
    
    total_map_time = time.time() - map_start
    print(f"  Map total (parallel wall time): {total_map_time:.3f}s")

    # Reduce
    reduce_time, reduce_resp = time_request(
        f"http://{REDUCER_IP}:8080/reduce?bucket={BUCKET}&keys=results/par_mapper_0.json,results/par_mapper_1.json,results/par_mapper_2.json"
    )
    print(f"  Reduce: {reduce_time:.3f}s")

    total = split_time + total_map_time + reduce_time
    print(f"  TOTAL: {total:.3f}s")
    return {
        "split": split_time,
        "map": total_map_time,
        "reduce": reduce_time,
        "total": total
    }

def run_experiments(num_runs=5):
    """Run multiple experiments and average the results."""
    seq_results = []
    par_results = []

    for i in range(num_runs):
        print(f"\n{'='*50}")
        print(f"Run {i+1}/{num_runs}")
        print(f"{'='*50}")
        seq_results.append(run_sequential())
        par_results.append(run_parallel())

    return seq_results, par_results

def plot_results(seq_results, par_results):
    """Create performance comparison plots."""
    
    # Average results
    avg_seq = {
        "split": np.mean([r["split"] for r in seq_results]),
        "map": np.mean([r["map"] for r in seq_results]),
        "reduce": np.mean([r["reduce"] for r in seq_results]),
        "total": np.mean([r["total"] for r in seq_results]),
    }
    avg_par = {
        "split": np.mean([r["split"] for r in par_results]),
        "map": np.mean([r["map"] for r in par_results]),
        "reduce": np.mean([r["reduce"] for r in par_results]),
        "total": np.mean([r["total"] for r in par_results]),
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # Plot 1: Stacked bar - Phase breakdown
    phases = ["Split", "Map", "Reduce"]
    seq_vals = [avg_seq["split"], avg_seq["map"], avg_seq["reduce"]]
    par_vals = [avg_par["split"], avg_par["map"], avg_par["reduce"]]

    x = np.arange(len(phases))
    width = 0.35
    axes[0].bar(x - width/2, seq_vals, width, label="Sequential (1 Mapper)", color="#e74c3c")
    axes[0].bar(x + width/2, par_vals, width, label="Parallel (3 Mappers)", color="#2ecc71")
    axes[0].set_xlabel("Phase")
    axes[0].set_ylabel("Time (seconds)")
    axes[0].set_title("Time per Phase: Sequential vs Parallel")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(phases)
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    # Plot 2: Total time comparison
    totals = [avg_seq["total"], avg_par["total"]]
    colors = ["#e74c3c", "#2ecc71"]
    bars = axes[1].bar(["Sequential", "Parallel"], totals, color=colors, width=0.5)
    axes[1].set_ylabel("Time (seconds)")
    axes[1].set_title("Total Pipeline Time")
    axes[1].grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, totals):
        axes[1].text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
                     f"{val:.3f}s", ha="center", va="bottom", fontweight="bold")

    # Plot 3: Speedup across runs
    speedups = [s["total"] / p["total"] for s, p in zip(seq_results, par_results)]
    axes[2].plot(range(1, len(speedups)+1), speedups, "bo-", linewidth=2, markersize=8)
    axes[2].axhline(y=np.mean(speedups), color="r", linestyle="--", label=f"Avg: {np.mean(speedups):.2f}x")
    axes[2].axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
    axes[2].set_xlabel("Run #")
    axes[2].set_ylabel("Speedup (Sequential / Parallel)")
    axes[2].set_title("Speedup per Run")
    axes[2].legend()
    axes[2].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig("mapreduce_performance.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("\nPlot saved as mapreduce_performance.png")

    # Print summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Avg Sequential Total: {avg_seq['total']:.3f}s")
    print(f"Avg Parallel Total:   {avg_par['total']:.3f}s")
    print(f"Avg Speedup:          {np.mean(speedups):.2f}x")
    print(f"Map Phase Speedup:    {avg_seq['map']/avg_par['map']:.2f}x")

if __name__ == "__main__":
    print("MapReduce Performance Experiment")
    print("================================")
    
    seq_results, par_results = run_experiments(num_runs=5)
    plot_results(seq_results, par_results)