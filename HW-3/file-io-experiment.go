package main

import (
	"bufio"
	"fmt"
	"os"
	"time"
)

const iterations = 100000

// writeUnbuffered writes directly to the file on each iteration
func writeUnbuffered(filename string) time.Duration {
	// Open (or create) the output file
	f, err := os.Create(filename)
	if err != nil {
		panic(err)
	}
	defer f.Close()

	// Record start time
	start := time.Now()

	// Loop and write directly to file
	for i := 0; i < iterations; i++ {
		data := fmt.Sprintf("Line %d: This is unbuffered write data\n", i)
		_, err := f.Write([]byte(data))
		if err != nil {
			panic(err)
		}
	}

	// Compute elapsed time
	elapsed := time.Since(start)
	return elapsed
}

// writeBuffered uses bufio.Writer for buffered writes
func writeBuffered(filename string) time.Duration {
	// Open the file
	f, err := os.Create(filename)
	if err != nil {
		panic(err)
	}
	defer f.Close()

	// Wrap in bufio.Writer
	w := bufio.NewWriter(f)

	// Record start time
	start := time.Now()

	// Loop and write using buffered writer
	for i := 0; i < iterations; i++ {
		data := fmt.Sprintf("Line %d: This is buffered write data\n", i)
		_, err := w.WriteString(data)
		if err != nil {
			panic(err)
		}
	}

	// Flush the buffer to disk
	err = w.Flush()
	if err != nil {
		panic(err)
	}

	// Compute elapsed time
	elapsed := time.Since(start)
	return elapsed
}

func main() {
	fmt.Printf("File I/O Performance Experiment\n")
	fmt.Printf("Writing %d lines to disk...\n\n", iterations)

	// Test unbuffered writes
	fmt.Println("Running unbuffered write test...")
	unbufferedDuration := writeUnbuffered("unbuffered_output.txt")
	fmt.Printf("Unbuffered write time: %v\n\n", unbufferedDuration)

	// Test buffered writes
	fmt.Println("Running buffered write test...")
	bufferedDuration := writeBuffered("buffered_output.txt")
	fmt.Printf("Buffered write time:   %v\n\n", bufferedDuration)

	// Calculate speedup
	speedup := float64(unbufferedDuration) / float64(bufferedDuration)
	fmt.Printf("Speedup: %.2fx faster with buffering\n", speedup)

}
