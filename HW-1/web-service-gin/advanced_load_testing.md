# Load Testing Methods Comparison

## Session Test (Sequential + Connection Pooling)

- Sends **one request at a time** in a loop
- Reuses TCP connections (avoids connection overhead)
- Simple, single-threaded
- **Performance**: ~100-200 requests in 30 seconds
- **Use when**: Testing from a single-user perspective

## Thread Pool Test (Parallel Threads)

- Spawns **10 separate threads**, each making requests
- Each thread blocks while waiting for response
- OS manages thread scheduling
- **Performance**: ~500-1000 requests in 30 seconds
- **Use when**: Simulating multiple concurrent users
- **Limitation**: Thread overhead (~100-1000 threads max)

## Async/Await Test (Non-blocking I/O)

- Launches **10 requests simultaneously** without blocking
- While waiting for responses, immediately sends more requests
- Single thread with event loop - no thread overhead
- Can handle thousands of concurrent connections
- **Performance**: ~2000-5000+ requests in 30 seconds
- **Use when**: Maximum throughput testing, production-grade load testing
- Most efficient for I/O-bound operations

## Key Difference

- **Session**: 1 request → wait → 1 request → wait... *(sequential)*
- **Threads**: 10 parallel requests → wait → 10 more *(parallel but blocking)*
- **Async**: 10 concurrent requests → immediately send 10 more while waiting *(concurrent non-blocking)*

**Winner**: Async wins because it doesn't waste CPU time waiting for network responses.

---

## Load Testing Results
## Load Testing Results

### 1. Session Test (Connection Pooling)

```
Starting session-based load test with connection pooling...
```

**Statistics:**
- **Total requests**: 322
- **Requests/second**: 1,625.76
- **Average response**: 93.25ms
- **Median response**: 89.45ms
- **Min response**: 80.00ms
- **Max response**: 198.06ms
- **95th percentile**: 115.22ms
- **99th percentile**: 128.65ms
- **Std deviation**: 12.38ms

---

### 2. Thread Pool Test (10 workers)

```
Starting threaded load test with 10 workers...
```

**Statistics:**
- **Total requests**: 1,320
- **Requests/second**: 4,441.13
- **Average response**: 216.23ms
- **Median response**: 210.69ms
- **Min response**: 173.59ms
- **Max response**: 297.22ms
- **95th percentile**: 264.83ms
- **99th percentile**: 294.95ms
- **Std deviation**: 23.70ms

---

### 3. Async/Await Test (10 concurrent)

```
Starting async load test with 10 concurrent requests...
```

**Statistics:**
- **Total requests**: 2,920
- **Requests/second**: 14,468.16
- **Average response**: 99.26ms
- **Median response**: 94.08ms
- **Min response**: 77.70ms
- **Max response**: 201.82ms
- **95th percentile**: 125.17ms
- **99th percentile**: 177.15ms
- **Std deviation**: 16.23ms

---

## Final Comparison

| Method | Requests | Requests/sec | Avg Response |
|--------|----------|--------------|--------------|
| Session | 322 | 1,625 | 93.25ms |
| Threaded | 1,320 | 4,441 | 216.23ms |
| **Async** | **2,920** | **14,468** | **99.26ms** |

### Key Insight
**Async approach handled 9.1x more requests than Session and achieved the best throughput!**