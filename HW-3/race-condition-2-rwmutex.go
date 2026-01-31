package main

import (
	"fmt"
	"sync"
	"time"
)

// SafeMap wraps a map with an RWMutex for thread-safe access
type SafeMap struct {
	mu sync.RWMutex
	m  map[int]int
}

// Write safely writes a key-value pair to the map
func (sm *SafeMap) Write(key, value int) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	sm.m[key] = value
}

// Len safely returns the length of the map
func (sm *SafeMap) Len() int {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return len(sm.m)
}

func main() {
	// Create a SafeMap with RWMutex protection
	safeMap := &SafeMap{
		m: make(map[int]int),
	}

	// WaitGroup to wait for all goroutines to finish
	var wg sync.WaitGroup

	// Start timing
	startTime := time.Now()

	// Spawn 50 goroutines
	for g := 0; g < 50; g++ {
		wg.Add(1)
		go func(goroutineID int) {
			defer wg.Done()

			// Run 1000 iterations in each goroutine
			for i := 0; i < 1000; i++ {
				safeMap.Write(goroutineID*1000+i, i)
			}
		}(g)
	}

	// Wait for all goroutines to finish
	wg.Wait()

	// Calculate elapsed time
	elapsed := time.Since(startTime)

	// Print the length of the map and time taken
	fmt.Printf("Length of map: %d\n", safeMap.Len())
	fmt.Printf("Total time taken: %v\n", elapsed)
}
