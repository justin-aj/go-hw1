package main

import (
	"fmt"
	"runtime"
	"time"
)

const iterations = 1000000

// pingPong performs a ping-pong exchange over two channels
// for the specified number of iterations
func pingPong(iterations int) time.Duration {
	// Create two unbuffered channels for ping-pong
	ping := make(chan struct{})
	pong := make(chan struct{})
	done := make(chan struct{})

	// Record start time
	start := time.Now()

	// Goroutine 1: receives from ping, sends to pong
	go func() {
		for i := 0; i < iterations; i++ {
			<-ping             // Wait for ping
			pong <- struct{}{} // Send pong
		}
	}()

	// Goroutine 2: sends to ping, receives from pong
	go func() {
		for i := 0; i < iterations; i++ {
			ping <- struct{}{} // Send ping
			<-pong             // Wait for pong
		}
		done <- struct{}{} // Signal completion
	}()

	// Wait for goroutine 2 to finish (it completes last after final pong receive)
	<-done

	// Compute elapsed time
	elapsed := time.Since(start)
	return elapsed
}

// runExperiment runs the ping-pong test and calculates statistics
func runExperiment(name string, procs int) {
	fmt.Printf("=== %s ===\n", name)
	fmt.Printf("GOMAXPROCS: %d\n", procs)

	// Set the number of OS threads
	runtime.GOMAXPROCS(procs)

	// Run the ping-pong experiment
	elapsed := pingPong(iterations)

	// Calculate average context switch time
	// Total context switches = iterations * 2 (ping + pong = 2 switches per round-trip)
	totalSwitches := iterations * 2
	avgSwitchTime := elapsed.Nanoseconds() / int64(totalSwitches)

	fmt.Printf("Total iterations: %d\n", iterations)
	fmt.Printf("Total time: %v\n", elapsed)
	fmt.Printf("Total context switches: %d\n", totalSwitches)
	fmt.Printf("Average switch time: %d ns (%.3f µs)\n", avgSwitchTime, float64(avgSwitchTime)/1000.0)
	fmt.Println()
}

func main() {
	fmt.Println("Context Switching Experiment: Goroutine Switching Cost")
	fmt.Println("========================================================")
	fmt.Printf("Available CPU cores: %d\n\n", runtime.NumCPU())

	// Experiment 1: Single OS thread
	runExperiment("Single OS Thread (GOMAXPROCS=1)", 1)

	// Small delay between experiments
	time.Sleep(500 * time.Millisecond)

	// Experiment 2: Multiple OS threads (all available cores)
	numCPU := runtime.NumCPU()
	runExperiment("Multiple OS Threads (GOMAXPROCS=NumCPU)", numCPU)

	// Calculate and display comparison
	fmt.Println("=== Analysis ===")
	fmt.Println("Re-running for accurate comparison...")

	runtime.GOMAXPROCS(1)
	singleThreadTime := pingPong(iterations)

	runtime.GOMAXPROCS(numCPU)
	multiThreadTime := pingPong(iterations)

	singleAvg := singleThreadTime.Nanoseconds() / int64(iterations*2)
	multiAvg := multiThreadTime.Nanoseconds() / int64(iterations*2)

	fmt.Printf("\nSingle-threaded average: %d ns\n", singleAvg)
	fmt.Printf("Multi-threaded average:  %d ns\n", multiAvg)

	if singleAvg < multiAvg {
		ratio := float64(multiAvg) / float64(singleAvg)
		fmt.Printf("\n✓ Single-threaded is %.2fx FASTER\n", ratio)
	} else {
		ratio := float64(singleAvg) / float64(multiAvg)
		fmt.Printf("\n✓ Multi-threaded is %.2fx FASTER\n", ratio)
	}
}
