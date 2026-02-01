# Locust Load Testing Experiment

## Overview
This experiment uses Locust to load test the album web service from HW-1, exploring performance characteristics of GET vs POST operations and understanding distributed load generation using green threads (user-level threads in Python).

## What is Locust?

**Locust** is a distributed load testing framework that uses:
- **Green threads (gevent)**: Lightweight, user-space threading (similar to Go's goroutines!)
- **Python**: Easy to write test scenarios
- **Master/Worker architecture**: Distributed load generation
- **Real-time web UI**: Live statistics and charts

### Green Threads vs OS Threads

| Feature | Green Threads (gevent) | OS Threads | Go Goroutines |
|---------|----------------------|------------|---------------|
| Context switch | ~100-200 ns | ~1-3 µs | ~108 ns (single-threaded) |
| Created in | User space | Kernel space | User space |
| Scheduled by | Application (gevent) | OS | Go runtime |
| Cost per thread | ~1-2 KB | ~1-8 MB | ~2 KB |
| Max concurrent | Millions | Thousands | Millions |

**Connection to HW-3**: Just like goroutines, green threads avoid OS-level context switching overhead!

## Setup Instructions

### Prerequisites
1. Docker and Docker Compose installed
2. Your Go web server from HW-1 running
3. Python (optional, for local testing)

### File Structure
```
HW-3/
├── locustfile.py              # Test scenarios
├── docker-compose-locust.yml  # Docker configuration
└── LOCUST_EXPERIMENT.md      # This file
```

### Starting Your Server

**Option 1: Run locally**
```powershell
cd ..\HW-1\web-service-gin
go run main.go
```

**Option 2: Run in Docker** (if you have a Dockerfile)
```powershell
cd ..\HW-1\web-service-gin
docker build -t album-service .
docker run -p 8080:8080 album-service
```

Verify server is running:
```powershell
curl http://localhost:8080/albums
```

### Starting Locust

```powershell
# From HW-3 directory
docker-compose -f docker-compose-locust.yml up

# To scale workers (e.g., 4 workers):
docker-compose -f docker-compose-locust.yml up --scale locust-worker=4
```

### Accessing the Web UI

1. Open browser to: http://localhost:8089
2. Enter configuration:
   - **Number of users**: 1 (start small)
   - **Spawn rate**: 1 user/second
   - **Host**: `http://host.docker.internal:8080` (Windows/Mac) or `http://172.17.0.1:8080` (Linux)
3. Click "Start swarming"

## Test Scenarios

### 1. Basic Test (Mixed Read/Write)
Uses `AlbumUser` class with task weights:
- **GET /albums**: Weight 3 (75% of requests if combined with task weight 2 for get by ID, actual 50%)
- **POST /albums**: Weight 1 (16.67% of requests)
- **GET /albums/:id**: Weight 2 (33.33% of requests)

**Simulates**: Realistic web traffic (read-heavy)

### 2. Read-Only Test
Uses `GetOnlyUser` class:
- Only GET requests
- Faster wait time (0.5-2 seconds)

**Simulates**: Read-heavy workloads (news sites, product catalogs)

### 3. Write-Only Test
Uses `PostOnlyUser` class:
- Only POST requests
- Faster wait time (0.5-2 seconds)

**Simulates**: Write-heavy workloads (logging, data collection)

## Understanding the Statistics

### Key Metrics

#### Request Count
- Total number of requests sent
- GET should be higher (weighted 3:1 or 2:1)

#### Response Time (ms)
- **Median (50th percentile)**: Half of requests are faster than this
- **Average**: Mean response time (can be skewed by outliers)
- **95th percentile**: 95% of requests are faster than this
- **99th percentile**: 99% of requests are faster than this
- **Max**: Slowest request

**Why percentiles matter**: 
- Average can be misleading (one slow request skews it)
- 95th/99th percentile shows "worst case" for most users
- SLAs typically use percentiles (e.g., "95% of requests < 100ms")

#### Requests per Second (RPS)
- Throughput of your system
- Higher is better (but watch for errors!)

#### Failures
- Should be **0** for a healthy system
- Any failures indicate problems

### Expected Results

#### GET vs POST Performance

**Hypothesis**: GET requests should be faster than POST

**Why?**
1. **No JSON parsing**: GET doesn't need to parse request body
2. **No allocation**: POST calls `append()`, which may trigger slice reallocation
3. **Simpler operation**: GET just returns existing data
4. **Read vs Write**: Reads are typically faster than writes

#### Your Server's Data Structure

Looking at your `main.go`:
```go
var albums = []album{...}  // Slice (array-backed)
```

**Current Implementation**:
- **Data structure**: Slice (dynamic array)
- **GET /albums**: O(1) - just return the slice
- **POST /albums**: O(1) amortized - append to slice (may trigger reallocation)
- **GET /albums/:id**: O(n) - linear search through slice

**Concurrency Issue** ⚠️:
```go
albums = append(albums, newAlbum)  // RACE CONDITION!
```

Your slice is **not thread-safe**! With concurrent POSTs:
- Multiple goroutines can append simultaneously
- Slice reallocation can cause data corruption
- No synchronization = **undefined behavior**

## Race Condition Analysis

### The Problem

From your HW-3 experiments, you know that:
1. **Unsynchronized access to shared data = race condition**
2. **Maps and slices are not thread-safe in Go**

Your current code:
```go
var albums = []album{...}  // Shared state

func postAlbums(c *gin.Context) {
    // ...
    albums = append(albums, newAlbum)  // Concurrent writes!
}
```

### Running With Race Detector

Test for race conditions:
```powershell
cd ..\HW-1\web-service-gin
go run -race main.go

# Then run Locust with POST requests
# You'll likely see: "WARNING: DATA RACE"
```

### Solutions (Based on HW-3 Knowledge)

#### Option 1: Mutex (Simple, Safe)
```go
var (
    albums      = []album{...}
    albumsMutex sync.RWMutex
)

func getAlbums(c *gin.Context) {
    albumsMutex.RLock()
    defer albumsMutex.RUnlock()
    c.IndentedJSON(http.StatusOK, albums)
}

func postAlbums(c *gin.Context) {
    var newAlbum album
    if err := c.BindJSON(&newAlbum); err != nil {
        return
    }
    
    albumsMutex.Lock()
    albums = append(albums, newAlbum)
    albumsMutex.Unlock()
    
    c.IndentedJSON(http.StatusCreated, newAlbum)
}
```

**Performance**: RWMutex allows multiple concurrent reads!

#### Option 2: sync.Map (For Key-Value Access)
```go
var albums sync.Map

func postAlbums(c *gin.Context) {
    var newAlbum album
    if err := c.BindJSON(&newAlbum); err != nil {
        return
    }
    albums.Store(newAlbum.ID, newAlbum)
    c.IndentedJSON(http.StatusCreated, newAlbum)
}
```

**Performance**: Better for high read:write ratios (from your RWMutex experiment!)

#### Option 3: Channel-Based (Actor Pattern)
```go
type albumStore struct {
    albums  []album
    getChan chan chan []album
    addChan chan album
}

func (s *albumStore) run() {
    for {
        select {
        case responseChan := <-s.getChan:
            responseChan <- s.albums
        case newAlbum := <-s.addChan:
            s.albums = append(s.albums, newAlbum)
        }
    }
}
```

**Performance**: Single goroutine = no locks, but potential bottleneck

## Tradeoffs: Data Structures for Web Services

### Real-World Usage Patterns

Most web services are **read-heavy**:
- **Reads (GET)**: 80-95% of traffic
- **Writes (POST/PUT/DELETE)**: 5-20% of traffic

Examples:
- **Twitter**: 99% reads (timeline viewing) vs 1% writes (tweets)
- **E-commerce**: 95% reads (browsing) vs 5% writes (purchases)
- **News sites**: 99.9% reads vs 0.1% writes

### Data Structure Choice Impact

| Structure | GET All | GET by ID | POST | Concurrency | Use Case |
|-----------|---------|-----------|------|-------------|----------|
| **Slice** | O(1) ✅ | O(n) ❌ | O(1)* ✅ | ❌ Not safe | Small datasets |
| **Slice + Mutex** | O(1) ✅ | O(n) ⚠️ | O(1)* ⚠️ | ✅ Safe | Small, read-heavy |
| **Slice + RWMutex** | O(1) ✅ | O(n) ⚠️ | O(1)* ⚠️ | ✅✅ Better reads | Small, read-heavy |
| **Map** | O(n) ⚠️ | O(1) ✅ | O(1) ✅ | ❌ Not safe | Key-based access |
| **Map + RWMutex** | O(n) ⚠️ | O(1) ✅ | O(1) ✅ | ✅✅ Better reads | Medium, read-heavy |
| **sync.Map** | O(n) ⚠️ | O(1) ✅ | O(1) ✅ | ✅✅✅ Lock-free reads | Large, read-heavy |
| **Database** | O(n) | O(1)** ✅ | O(1)** ✅ | ✅✅✅ ACID | Production |

*Amortized; **With index

### Recommendation

For your album service:

**Development/Testing**:
```go
var (
    albums      = []album{...}
    albumsMutex sync.RWMutex  // Allow concurrent reads
)
```

**Production**:
- Use a database (PostgreSQL, MySQL)
- Indexed by ID for fast lookups
- Built-in concurrency control
- Persistence (data survives restarts)

## Expected Experimental Results

### Hypothesis 1: GET Faster Than POST

**Expected observations**:
- GET median: ~1-5ms
- POST median: ~2-10ms
- POST requires JSON parsing + append operation

**Confirmation**: Check Locust statistics tab

### Hypothesis 2: Percentiles Show Outliers

**Expected observations**:
- Median (50th): Low and stable
- 95th percentile: Slightly higher
- 99th percentile: Much higher (GC pauses, context switches)
- Max: Very high (occasional slow request)

**Why**: 
- From HW-3: Context switches, lock contention, cache misses
- Go GC pauses
- OS scheduler interference

### Hypothesis 3: Failure Rate

**Without mutex**: May see failures under concurrent load
- Race conditions can cause panics
- Data corruption

**With mutex**: Zero failures (safe concurrent access)

## Running the Experiments

### Experiment 1: Start Small (1 User, 1 Worker)

1. Start server: `go run main.go`
2. Start Locust: `docker-compose -f docker-compose-locust.yml up`
3. Configure:
   - Users: 1
   - Spawn rate: 1
   - Host: `http://host.docker.internal:8080`
4. Run for 1-2 minutes
5. **Screenshot**: Statistics tab (GET vs POST comparison)

**Look for**:
- Median response times
- 95th percentile
- Requests per second
- Failures (should be 0)

### Experiment 2: Increase Load (10 Users, 1 Worker)

1. Stop test, change to 10 users
2. Spawn rate: 2 users/second
3. Run for 1-2 minutes
4. **Screenshot**: Statistics + Charts tab

**Look for**:
- How do response times change?
- Any failures appear?
- RPS increase?

### Experiment 3: Add More Workers (10 Users, 4 Workers)

1. Stop Locust: `docker-compose -f docker-compose-locust.yml down`
2. Restart with more workers:
   ```powershell
   docker-compose -f docker-compose-locust.yml up --scale locust-worker=4
   ```
3. Run 10 users
4. **Screenshot**: Compare statistics

**Look for**:
- Does distributed load generation change results?
- Green threads spreading across workers

### Experiment 4: Race Condition (If Brave!)

1. Modify locustfile to use `PostOnlyUser`
2. Run with 50 users, high spawn rate
3. Watch for failures or panics in server logs

**Expected**: Without mutex, you'll see data corruption or panics!

## Questions to Answer

### 1. GET vs POST Performance
- Which is faster?
- By how much?
- Why?

### 2. Percentiles
- What's the difference between median and 99th percentile?
- What causes the long tail?
- How does this relate to SLAs?

### 3. Real-World Scenario
- Most web services are read-heavy (80-95% reads)
- How should this influence your data structure choice?
- Why is RWMutex better than Mutex for this?

### 4. Scaling
- What happens when you add more users?
- Where is the bottleneck?
- How would you optimize?

### 5. Green Threads
- How does Locust use green threads?
- How is this similar to Go's goroutines?
- Why can Locust generate load from a single machine?

## Connection to HW-3 Concepts

| HW-3 Concept | Locust Application |
|--------------|-------------------|
| **Goroutine switching** | Green thread switching (gevent) |
| **Race conditions** | Your album slice without mutex |
| **Mutex vs RWMutex** | Choosing the right lock for reads |
| **sync.Map** | Alternative for thread-safe storage |
| **Context switching cost** | Why green threads are cheap |
| **Batching** | Could batch POST requests |

## Advanced: Making It Spicier 🌶️

### Add Race Conditions
Implement the hashmap (map) version:
```go
var albumMap = make(map[string]album)  // Not thread-safe!
```

Run Locust with concurrent POSTs → watch it crash! 💥

### Add Thread-Safe Version
```go
var (
    albumMap   = make(map[string]album)
    albumMutex sync.RWMutex
)
```

Compare performance: map+RWMutex vs slice+RWMutex

### Add Artificial Delay
```go
func getAlbums(c *gin.Context) {
    time.Sleep(10 * time.Millisecond)  // Simulate database query
    c.IndentedJSON(http.StatusOK, albums)
}
```

How does this affect response times and RPS?

### Add More Workers
```powershell
docker-compose -f docker-compose-locust.yml up --scale locust-worker=10
```

Distributed load generation!

## Cleanup

Stop Locust:
```powershell
docker-compose -f docker-compose-locust.yml down
```

Stop server:
```powershell
# Ctrl+C in the terminal running your Go server
```

## Screenshot Checklist

Capture these for your report:
- [ ] Locust Web UI showing 1 user test
- [ ] Statistics tab: GET vs POST comparison (response times)
- [ ] Statistics tab: Request count breakdown
- [ ] Charts tab: Response time over time
- [ ] Charts tab: Requests per second
- [ ] Multiple users test results
- [ ] Failures (if testing race conditions)

## Discussion Points for Mock Interviews

1. **Why is GET faster than POST?**
   - JSON parsing overhead
   - Memory allocation in POST
   - Write operations are inherently more expensive

2. **What do percentiles tell us?**
   - Median = typical experience
   - 99th percentile = worst experience for most users
   - Long tail = outliers (GC, context switches, cache misses)

3. **Why use RWMutex instead of Mutex?**
   - Multiple concurrent readers
   - Only blocks on writes
   - Perfect for read-heavy workloads (based on HW-3!)

4. **How does Locust relate to HW-3?**
   - Green threads = lightweight, like goroutines
   - User-space scheduling = no OS overhead
   - Can simulate thousands of concurrent users from one machine

5. **What data structure is best?**
   - Depends on access patterns!
   - Read-heavy + small: Slice + RWMutex
   - Read-heavy + key-based: sync.Map
   - Production: Database with indexes

6. **How would you scale this system?**
   - Add caching (Redis)
   - Use read replicas (database)
   - Horizontal scaling (multiple servers)
   - Load balancer

## Next Steps

1. Run basic experiment (1 user)
2. Capture screenshots
3. Analyze GET vs POST differences
4. Think about data structure tradeoffs
5. Prepare to discuss in your group!

Good luck, and have fun load testing! 🚀
