# Scaling Experiment Output

```
PS C:\Users\ajinf\Documents\CS 6650\CS6650-HW\HW-4\mapreduce> python orchestrator.py scale

============================================================
SCALING EXPERIMENT
============================================================

--- Testing with 1 chunk(s) ---

============================================================
MapReduce Pipeline — 1 chunks, 1 mapper(s)
============================================================

Phase 1: Splitting...
  Splitter succeeded in 0.596s (attempt 1)
  Created 1 chunks

Phase 2: Mapping...
  Mapper (chunk 0) succeeded in 0.553s (attempt 1)
  Map phase wall time: 0.557s

Phase 3: Reducing...
  Reducer succeeded in 0.335s (attempt 1)

============================================================
PIPELINE COMPLETE
============================================================
  Split time:    0.596s
  Map time:      0.557s (wall clock, 1 chunks)
  Reduce time:   0.335s
  Total time:    1.489s
  Unique words:  4837
  Output:        s3://ajin-mapreduce-bucket/results/final_counts.json

--- Testing with 2 chunk(s) ---

============================================================
MapReduce Pipeline — 2 chunks, 1 mapper(s)
============================================================

Phase 1: Splitting...
  Splitter succeeded in 0.305s (attempt 1)
  Created 2 chunks

Phase 2: Mapping...
  Mapper (chunk 1) succeeded in 0.183s (attempt 1)
  Mapper (chunk 0) succeeded in 0.334s (attempt 1)
  Map phase wall time: 0.334s

Phase 3: Reducing...
  Reducer succeeded in 0.252s (attempt 1)

============================================================
PIPELINE COMPLETE
============================================================
  Split time:    0.305s
  Map time:      0.334s (wall clock, 2 chunks)
  Reduce time:   0.252s
  Total time:    0.894s
  Unique words:  4837
  Output:        s3://ajin-mapreduce-bucket/results/final_counts.json

--- Testing with 3 chunk(s) ---

============================================================
MapReduce Pipeline — 3 chunks, 1 mapper(s)
============================================================

Phase 1: Splitting...
  Splitter succeeded in 0.428s (attempt 1)
  Created 3 chunks

Phase 2: Mapping...
  Mapper (chunk 1) succeeded in 0.178s (attempt 1)
  Mapper (chunk 0) succeeded in 0.260s (attempt 1)
  Mapper (chunk 2) succeeded in 0.303s (attempt 1)
  Map phase wall time: 0.305s

Phase 3: Reducing...
  Reducer succeeded in 0.298s (attempt 1)

============================================================
PIPELINE COMPLETE
============================================================
  Split time:    0.428s
  Map time:      0.305s (wall clock, 3 chunks)
  Reduce time:   0.298s
  Total time:    1.033s
  Unique words:  4837
  Output:        s3://ajin-mapreduce-bucket/results/final_counts.json

--- Testing with 5 chunk(s) ---

============================================================
MapReduce Pipeline — 5 chunks, 1 mapper(s)
============================================================

Phase 1: Splitting...
  Splitter succeeded in 0.536s (attempt 1)
  Created 5 chunks

Phase 2: Mapping...
  Mapper (chunk 1) succeeded in 0.170s (attempt 1)
  Mapper (chunk 0) succeeded in 0.196s (attempt 1)
  Mapper (chunk 2) succeeded in 0.258s (attempt 1)
  Mapper (chunk 4) succeeded in 0.256s (attempt 1)
  Mapper (chunk 3) succeeded in 0.272s (attempt 1)
  Map phase wall time: 0.276s

Phase 3: Reducing...
  Reducer succeeded in 0.373s (attempt 1)

============================================================
PIPELINE COMPLETE
============================================================
  Split time:    0.536s
  Map time:      0.276s (wall clock, 5 chunks)
  Reduce time:   0.373s
  Total time:    1.187s
  Unique words:  4837
  Output:        s3://ajin-mapreduce-bucket/results/final_counts.json

--- Testing with 10 chunk(s) ---

============================================================
MapReduce Pipeline — 10 chunks, 1 mapper(s)
============================================================

Phase 1: Splitting...
  Splitter succeeded in 0.808s (attempt 1)
  Created 10 chunks

Phase 2: Mapping...
  Mapper (chunk 2) succeeded in 0.171s (attempt 1)
  Mapper (chunk 4) succeeded in 0.175s (attempt 1)
  Mapper (chunk 6) succeeded in 0.173s (attempt 1)
  Mapper (chunk 0) succeeded in 0.198s (attempt 1)
  Mapper (chunk 7) succeeded in 0.228s (attempt 1)
  Mapper (chunk 5) succeeded in 0.236s (attempt 1)
  Mapper (chunk 9) succeeded in 0.240s (attempt 1)
  Mapper (chunk 1) succeeded in 0.253s (attempt 1)
  Mapper (chunk 3) succeeded in 0.262s (attempt 1)
  Mapper (chunk 8) succeeded in 0.355s (attempt 1)
  Map phase wall time: 0.369s

Phase 3: Reducing...
  Reducer succeeded in 0.729s (attempt 1)

============================================================
PIPELINE COMPLETE
============================================================
  Split time:    0.808s
  Map time:      0.369s (wall clock, 10 chunks)
  Reduce time:   0.729s
  Total time:    1.908s
  Unique words:  4837
  Output:        s3://ajin-mapreduce-bucket/results/final_counts.json

============================================================
SCALING SUMMARY
============================================================
Chunks     Map Time     Total Time
----------------------------------
1          0.557        1.489
2          0.334        0.894
3          0.305        1.033
5          0.276        1.187
10         0.369        1.908
```

Here's a summary of the key discussion points from the orchestrator experiments:

**What we built:** An orchestrator that automates the full MapReduce pipeline with two improvements over the original — dynamic chunk count (configurable via `num_chunks`) and retry logic for mapper failures (3 attempts with 2-second delays).

**Retry demo:** The orchestrator successfully detected a dead mapper (port 9999), retried 3 times, and gracefully reported the failure. In production, it would spin up a replacement ECS task.

**Scaling experiment results:** We ran the pipeline with 1, 2, 3, 5, and 10 chunks locally through a single mapper container. Map time improved from 1→5 chunks, but at 10 chunks both map time and total time got worse.

**Why 10 chunks was slower:** Even though your machine has 16 CPU cores, the bottleneck isn't CPU — it's **S3 network I/O**. Each chunk requires an S3 download and upload, so 10 chunks means 20 S3 round trips vs 10 for 5 chunks. The mapper spends most of its time waiting on network calls, not computing. More local threads just means more concurrent network requests competing for bandwidth.

**Key insight — CPU-bound vs I/O-bound:** Word counting is I/O-bound at this scale. Adding more local threads past a certain point adds overhead without speedup. Separate machines (like the ECS deployment) help because each has its own network connection to S3, which is why the ECS run showed a clean 2.89x map phase speedup while local scaling plateaued.

**Auto-scaling discussion:** True auto-scaling would calculate chunk count based on file size (e.g., target 128MB per chunk), then spin up that many ECS tasks via the AWS SDK. This is how production systems like Hadoop/Spark work.