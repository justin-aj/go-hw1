import time
import requests
import concurrent.futures
import json
import sys

# ============================================
# UPDATE THESE WITH YOUR ACTUAL IPs/PORTS
# For local testing, all services run on localhost
# but on different ports
# ============================================
SPLITTER_URL = "http://localhost:8080"
MAPPER_URL = "http://localhost:8081"   # Single mapper for local testing
REDUCER_URL = "http://localhost:8082"

BUCKET = "ajin-mapreduce-bucket"
INPUT_KEY = "shakespeare-hamlet.txt"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def call_with_retry(url, description, max_retries=MAX_RETRIES):
    """Call a URL with retry logic. Returns (response_json, elapsed_time) or raises."""
    for attempt in range(1, max_retries + 1):
        try:
            start = time.time()
            resp = requests.get(url, timeout=30)
            elapsed = time.time() - start

            if resp.status_code == 200:
                print(f"  ✅ {description} succeeded in {elapsed:.3f}s (attempt {attempt})")
                return resp.json(), elapsed
            else:
                print(f"  ❌ {description} failed with status {resp.status_code} (attempt {attempt})")
                print(f"     Response: {resp.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {description} error (attempt {attempt}): {e}")

        if attempt < max_retries:
            print(f"  🔄 Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)

    raise Exception(f"FAILED after {max_retries} attempts: {description}")


def run_pipeline(num_chunks=3, mapper_urls=None):
    """
    Run the full MapReduce pipeline with configurable chunks and retry logic.
    
    Args:
        num_chunks: Number of chunks to split into (= number of mappers needed)
        mapper_urls: List of mapper URLs. If fewer than num_chunks, 
                     chunks are distributed round-robin across available mappers.
    """
    if mapper_urls is None:
        mapper_urls = [MAPPER_URL]

    print(f"\n{'='*60}")
    print(f"MapReduce Pipeline — {num_chunks} chunks, {len(mapper_urls)} mapper(s)")
    print(f"{'='*60}")
    pipeline_start = time.time()

    # ---- Phase 1: Split ----
    print("\n📄 Phase 1: Splitting...")
    split_url = f"{SPLITTER_URL}/split?bucket={BUCKET}&key={INPUT_KEY}&num_chunks={num_chunks}"
    split_resp, split_time = call_with_retry(split_url, "Splitter")
    chunk_keys = [f"chunks/chunk_{i}.txt" for i in range(num_chunks)]
    print(f"  Created {len(chunk_keys)} chunks")

    # ---- Phase 2: Map (parallel with retry) ----
    print("\n🔧 Phase 2: Mapping...")
    map_start = time.time()
    mapper_results = {}  # chunk_index -> output_key
    failed_chunks = []

    def map_chunk(chunk_index):
        """Map a single chunk, assigning to a mapper round-robin."""
        mapper_url = mapper_urls[chunk_index % len(mapper_urls)]
        url = (f"{mapper_url}/map?bucket={BUCKET}"
               f"&key=chunks/chunk_{chunk_index}.txt"
               f"&output_key=results/mapper_{chunk_index}.json")
        return chunk_index, call_with_retry(url, f"Mapper (chunk {chunk_index})")

    # Run all mappers in parallel using threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_chunks) as executor:
        futures = {executor.submit(map_chunk, i): i for i in range(num_chunks)}

        for future in concurrent.futures.as_completed(futures):
            chunk_idx = futures[future]
            try:
                idx, (resp, elapsed) = future.result()
                mapper_results[idx] = f"results/mapper_{idx}.json"
            except Exception as e:
                print(f"  💀 Chunk {chunk_idx} PERMANENTLY FAILED: {e}")
                failed_chunks.append(chunk_idx)

    map_time = time.time() - map_start
    print(f"  Map phase wall time: {map_time:.3f}s")

    if failed_chunks:
        print(f"\n⚠️  WARNING: {len(failed_chunks)} chunk(s) failed: {failed_chunks}")
        print("  Pipeline cannot produce correct results without all mapper outputs.")
        print("  In production, an orchestrator would spin up replacement tasks.")
        return None

    # ---- Phase 3: Reduce ----
    print("\n📊 Phase 3: Reducing...")
    output_keys = ",".join([mapper_results[i] for i in range(num_chunks)])
    reduce_url = f"{REDUCER_URL}/reduce?bucket={BUCKET}&keys={output_keys}"
    reduce_resp, reduce_time = call_with_retry(reduce_url, "Reducer")

    pipeline_total = time.time() - pipeline_start

    # ---- Summary ----
    print(f"\n{'='*60}")
    print(f"✅ PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Split time:    {split_time:.3f}s")
    print(f"  Map time:      {map_time:.3f}s (wall clock, {num_chunks} chunks)")
    print(f"  Reduce time:   {reduce_time:.3f}s")
    print(f"  Total time:    {pipeline_total:.3f}s")
    print(f"  Unique words:  {reduce_resp.get('unique_words', 'N/A')}")
    print(f"  Output:        {reduce_resp.get('output', 'N/A')}")

    return {
        "num_chunks": num_chunks,
        "num_mappers": len(mapper_urls),
        "split_time": split_time,
        "map_time": map_time,
        "reduce_time": reduce_time,
        "total_time": pipeline_total,
        "unique_words": reduce_resp.get("unique_words"),
    }


def demo_retry():
    """Demonstrate retry behavior with a bad URL."""
    print("\n" + "="*60)
    print("🧪 DEMO: Retry Logic")
    print("="*60)
    print("Calling a non-existent mapper to demonstrate retry behavior...\n")

    try:
        call_with_retry(
            "http://localhost:9999/map?bucket=test&key=test&output_key=test",
            "Bad Mapper",
            max_retries=3
        )
    except Exception as e:
        print(f"\n  Orchestrator caught the failure: {e}")
        print("  In production: would launch a new ECS task and retry.")


def scaling_experiment():
    """Run pipeline with different chunk counts to show scaling behavior."""
    print("\n" + "="*60)
    print("📈 SCALING EXPERIMENT")
    print("="*60)

    results = []
    for num_chunks in [1, 2, 3, 5, 10]:
        print(f"\n--- Testing with {num_chunks} chunk(s) ---")
        result = run_pipeline(num_chunks=num_chunks)
        if result:
            results.append(result)

    if results:
        print(f"\n{'='*60}")
        print("SCALING SUMMARY")
        print(f"{'='*60}")
        print(f"{'Chunks':<10} {'Map Time':<12} {'Total Time':<12}")
        print("-" * 34)
        for r in results:
            print(f"{r['num_chunks']:<10} {r['map_time']:<12.3f} {r['total_time']:<12.3f}")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "retry-demo":
        demo_retry()
    elif len(sys.argv) > 1 and sys.argv[1] == "scale":
        scaling_experiment()
    else:
        # Default: run with 3 chunks
        num = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        run_pipeline(num_chunks=num)