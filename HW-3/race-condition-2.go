package main

import (
	"fmt"
	"sync"
)

func main() {
	// Create a plain map[int]int
	m := make(map[int]int)

	// WaitGroup to wait for all goroutines to finish
	var wg sync.WaitGroup

	// Spawn 50 goroutines
	for g := 0; g < 50; g++ {
		wg.Add(1)
		go func(goroutineID int) {
			defer wg.Done()

			// Run 1000 iterations in each goroutine
			for i := 0; i < 1000; i++ {
				m[goroutineID*1000+i] = i
			}
		}(g)
	}

	// Wait for all goroutines to finish
	wg.Wait()

	// Print the length of the map
	fmt.Printf("Length of map: %d\n", len(m))
}
