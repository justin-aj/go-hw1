# Map Race Condition Experiment

## Overview
This experiment demonstrates race conditions when writing to a Go map from multiple goroutines, and how to fix them using mutex locks.

## Experiment Setup

### Parameters
- **Goroutines**: 50
- **Iterations per goroutine**: 1,000
- **Total expected writes**: 50,000 (50 × 1,000)
- **Key formula**: `g*1000 + i` (ensures unique keys per goroutine)

## Part 1: Unsafe Map (race-condition-2.go)

### Implementation
```go
m := make(map[int]int)  // Plain map - NOT thread-safe

for g := 0; g < 50; g++ {
    go func(goroutineID int) {
        for i := 0; i < 1000; i++ {
            m[goroutineID*1000+i] = i  // Concurrent writes!
        }
    }(g)
}
```

### Problem: Why Does It Crash?

**Go maps are NOT thread-safe for concurrent writes**

When multiple goroutines write to a map simultaneously:
1. **Internal corruption** - Map's internal hash table structure gets corrupted
2. **Panic or segfault** - The program crashes with "concurrent map writes"
3. **Undefined behavior** - Even if it doesn't crash immediately, data can be lost or corrupted

### Race Detector Output
Running with `go run -race` immediately detects the race condition and reports it.

---

## Part 2: Mutex-Protected Map (race-condition-2-mutex.go)

### Implementation
```go
type SafeMap struct {
    mu sync.Mutex      // Protects the map
    m  map[int]int
}

func (sm *SafeMap) Write(key, value int) {
    sm.mu.Lock()           // Acquire lock
    defer sm.mu.Unlock()   // Release on function exit
    sm.m[key] = value      // Safe write
}
```

### Test Results (3 runs)

#### Run 1
```
Length of map: 50000
Total time taken: 7.5441ms
```

#### Run 2 (with -race)
```
Length of map: 50000
Total time taken: 32.437ms
```

#### Run 3
```
Length of map: 50000
Total time taken: 7.2ms
```

**Mean time (without race detector)**: ~7.37ms  
**With race detector**: ~32.4ms (4.4x slower)

### Results Analysis

✅ **Correctness**
- All 50,000 entries successfully written
- No crashes
- No race conditions detected
- No data loss

⚠️ **Performance Impact**
- Mutex creates serialization at the lock point
- 50 goroutines contend for a single lock 50,000 times
- What should be parallel becomes sequential during lock acquisition

---

## Key Concepts Explained

### Mutex (Mutual Exclusion)
- **Purpose**: Ensures only ONE goroutine can access the protected resource at a time
- **Lock()**: Acquires exclusive access (blocks if another goroutine holds it)
- **Unlock()**: Releases access so another goroutine can proceed

### defer Unlock Pattern
```go
mu.Lock()
defer mu.Unlock()  // Preferred: guarantees unlock even on panic
doSomething()
```

**Why defer?**
- ✅ Prevents deadlocks from forgetting to unlock
- ✅ Handles panic scenarios
- ✅ Idiomatic Go pattern
- Tiny overhead, but worth the safety

### Pointer Receivers (*SafeMap)
```go
func (sm *SafeMap) Write(...)  // Pointer receiver
```

**Why pointers?**
- Mutexes **must not be copied** - copying a locked mutex is undefined behavior
- All goroutines need access to the **same** map instance
- Methods can modify the struct

### Race Detector Overhead
The race detector (`-race` flag) instruments code to track every memory access:
- **4-10x slower** execution
- **10x more memory** usage
- Only use for **debugging**, never in production
- Invaluable for finding concurrency bugs

---

## Lessons Learned

### 1. **Go Maps Are Not Thread-Safe**
- Never write to a map from multiple goroutines without synchronization
- Even concurrent reads + writes are unsafe
- Only concurrent reads are safe

### 2. **Mutexes Provide Safety, Not Parallelism**
- Mutex = correctness at the cost of performance
- Creates a bottleneck where goroutines wait in line
- Trade-off: safety vs. concurrency

### 3. **Always Test with `-race`**
- Catches subtle bugs that might not crash immediately
- Should be part of your testing workflow
- Can reveal races even in "working" code

### 4. **Better Alternatives for High Concurrency**
When mutex becomes a bottleneck:
- **sync.Map** - Built-in concurrent map (specialized use cases)
- **Sharding** - Multiple maps with separate locks
- **Channels** - "Share memory by communicating"
- **Atomic operations** - For simple counters/flags
- **Lock-free data structures** - Advanced techniques

---

## Next Steps
Explore atomic operations as an alternative synchronization primitive for simpler operations like counters.
