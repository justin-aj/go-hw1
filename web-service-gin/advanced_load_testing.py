"""
Advanced Load Testing Methods
Demonstrates multiple efficient approaches for load testing
"""

import asyncio
import aiohttp
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from datetime import datetime
import matplotlib.pyplot as plt

# ============================================
# METHOD 1: Async/Await (Most Efficient)
# ============================================
async def async_load_test(url, duration_seconds=30, concurrent_requests=10):
    """
    Uses asyncio for non-blocking I/O - can handle thousands of concurrent requests
    """
    response_times = []
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    async def make_request(session):
        try:
            start_req = time.time()
            async with session.get(url, timeout=10) as response:
                await response.text()
                end_req = time.time()
                return (end_req - start_req) * 1000, response.status
        except Exception as e:
            return None, None
    
    print(f"Starting async load test with {concurrent_requests} concurrent requests...")
    
    async with aiohttp.ClientSession() as session:
        while time.time() < end_time:
            # Launch multiple concurrent requests
            tasks = [make_request(session) for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            
            for response_time, status in results:
                if response_time:
                    response_times.append(response_time)
    
    return response_times


# ============================================
# METHOD 2: Thread Pool (Good Balance)
# ============================================
def threaded_load_test(url, duration_seconds=30, workers=10):
    """
    Uses threading for parallel requests - good for moderate load
    """
    response_times = []
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    def make_request():
        try:
            start_req = time.time()
            response = requests.get(url, timeout=10)
            end_req = time.time()
            return (end_req - start_req) * 1000
        except Exception as e:
            return None
    
    print(f"Starting threaded load test with {workers} workers...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while time.time() < end_time:
            # Submit batch of requests
            futures = [executor.submit(make_request) for _ in range(workers)]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    response_times.append(result)
    
    return response_times


# ============================================
# METHOD 3: Session with Connection Pool
# ============================================
def session_load_test(url, duration_seconds=30):
    """
    Uses requests.Session for connection pooling - reuses TCP connections
    """
    response_times = []
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    print("Starting session-based load test with connection pooling...")
    
    # Session reuses connections
    with requests.Session() as session:
        while time.time() < end_time:
            try:
                start_req = time.time()
                response = session.get(url, timeout=10)
                end_req = time.time()
                
                response_time = (end_req - start_req) * 1000
                response_times.append(response_time)
                
            except Exception as e:
                print(f"Request failed: {e}")
    
    return response_times


# ============================================
# Utility Functions
# ============================================
def print_statistics(response_times, test_name="Test"):
    """Print comprehensive statistics"""
    if not response_times:
        print("No successful requests!")
        return
    
    print(f"\n{'='*50}")
    print(f"{test_name} Statistics:")
    print(f"{'='*50}")
    print(f"Total requests:       {len(response_times)}")
    print(f"Requests/second:      {len(response_times) / (max(response_times) / 1000):.2f}")
    print(f"Average response:     {np.mean(response_times):.2f}ms")
    print(f"Median response:      {np.median(response_times):.2f}ms")
    print(f"Min response:         {min(response_times):.2f}ms")
    print(f"Max response:         {max(response_times):.2f}ms")
    print(f"95th percentile:      {np.percentile(response_times, 95):.2f}ms")
    print(f"99th percentile:      {np.percentile(response_times, 99):.2f}ms")
    print(f"Std deviation:        {np.std(response_times):.2f}ms")


def create_interactive_plots(session_times, threaded_times, async_times):
    """Create interactive matplotlib plots with zoom and pan capabilities"""
    
    # Enable interactive mode
    plt.ion()
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Load Testing Comparison - Interactive Plots', fontsize=16, fontweight='bold')
    
    # Plot 1: Response time distributions (Histograms)
    ax1 = plt.subplot(3, 3, 1)
    if session_times:
        ax1.hist(session_times, bins=30, alpha=0.7, color='blue', edgecolor='black')
    ax1.set_title('Session Test - Distribution')
    ax1.set_xlabel('Response Time (ms)')
    ax1.set_ylabel('Frequency')
    ax1.grid(True, alpha=0.3)
    
    ax2 = plt.subplot(3, 3, 2)
    if threaded_times:
        ax2.hist(threaded_times, bins=30, alpha=0.7, color='orange', edgecolor='black')
    ax2.set_title('Threaded Test - Distribution')
    ax2.set_xlabel('Response Time (ms)')
    ax2.set_ylabel('Frequency')
    ax2.grid(True, alpha=0.3)
    
    ax3 = plt.subplot(3, 3, 3)
    if async_times:
        ax3.hist(async_times, bins=30, alpha=0.7, color='green', edgecolor='black')
    ax3.set_title('Async Test - Distribution')
    ax3.set_xlabel('Response Time (ms)')
    ax3.set_ylabel('Frequency')
    ax3.grid(True, alpha=0.3)
    
    # Plot 2: Response times over time (Scatter)
    ax4 = plt.subplot(3, 3, 4)
    if session_times:
        ax4.scatter(range(len(session_times)), session_times, alpha=0.5, s=10, color='blue')
    ax4.set_title('Session Test - Over Time')
    ax4.set_xlabel('Request Number')
    ax4.set_ylabel('Response Time (ms)')
    ax4.grid(True, alpha=0.3)
    
    ax5 = plt.subplot(3, 3, 5)
    if threaded_times:
        ax5.scatter(range(len(threaded_times)), threaded_times, alpha=0.5, s=10, color='orange')
    ax5.set_title('Threaded Test - Over Time')
    ax5.set_xlabel('Request Number')
    ax5.set_ylabel('Response Time (ms)')
    ax5.grid(True, alpha=0.3)
    
    ax6 = plt.subplot(3, 3, 6)
    if async_times:
        ax6.scatter(range(len(async_times)), async_times, alpha=0.5, s=10, color='green')
    ax6.set_title('Async Test - Over Time')
    ax6.set_xlabel('Request Number')
    ax6.set_ylabel('Response Time (ms)')
    ax6.grid(True, alpha=0.3)
    
    # Plot 3: Box plots for comparison
    ax7 = plt.subplot(3, 3, 7)
    data_to_plot = []
    labels = []
    if session_times:
        data_to_plot.append(session_times)
        labels.append('Session')
    if threaded_times:
        data_to_plot.append(threaded_times)
        labels.append('Threaded')
    if async_times:
        data_to_plot.append(async_times)
        labels.append('Async')
    
    if data_to_plot:
        bp = ax7.boxplot(data_to_plot, labels=labels, patch_artist=True)
        colors = ['blue', 'orange', 'green']
        for patch, color in zip(bp['boxes'], colors[:len(data_to_plot)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.5)
    ax7.set_title('Response Time Comparison')
    ax7.set_ylabel('Response Time (ms)')
    ax7.grid(True, alpha=0.3)
    
    # Plot 4: Cumulative distribution
    ax8 = plt.subplot(3, 3, 8)
    if session_times:
        sorted_session = np.sort(session_times)
        ax8.plot(sorted_session, np.arange(len(sorted_session))/len(sorted_session)*100, 
                label='Session', color='blue', linewidth=2)
    if threaded_times:
        sorted_threaded = np.sort(threaded_times)
        ax8.plot(sorted_threaded, np.arange(len(sorted_threaded))/len(sorted_threaded)*100, 
                label='Threaded', color='orange', linewidth=2)
    if async_times:
        sorted_async = np.sort(async_times)
        ax8.plot(sorted_async, np.arange(len(sorted_async))/len(sorted_async)*100, 
                label='Async', color='green', linewidth=2)
    ax8.set_title('Cumulative Distribution')
    ax8.set_xlabel('Response Time (ms)')
    ax8.set_ylabel('Percentile (%)')
    ax8.legend()
    ax8.grid(True, alpha=0.3)
    
    # Plot 5: Bar chart comparison
    ax9 = plt.subplot(3, 3, 9)
    metrics = ['Total\nRequests', 'Avg\nResponse', 'P95', 'P99']
    x_pos = np.arange(len(metrics))
    width = 0.25
    
    session_stats = [len(session_times), np.mean(session_times) if session_times else 0, 
                    np.percentile(session_times, 95) if session_times else 0,
                    np.percentile(session_times, 99) if session_times else 0]
    threaded_stats = [len(threaded_times), np.mean(threaded_times) if threaded_times else 0,
                     np.percentile(threaded_times, 95) if threaded_times else 0,
                     np.percentile(threaded_times, 99) if threaded_times else 0]
    async_stats = [len(async_times), np.mean(async_times) if async_times else 0,
                  np.percentile(async_times, 95) if async_times else 0,
                  np.percentile(async_times, 99) if async_times else 0]
    
    # Normalize for comparison (divide requests by 10 to fit on same scale)
    session_stats[0] = session_stats[0] / 10
    threaded_stats[0] = threaded_stats[0] / 10
    async_stats[0] = async_stats[0] / 10
    
    ax9.bar(x_pos - width, session_stats, width, label='Session', color='blue', alpha=0.7)
    ax9.bar(x_pos, threaded_stats, width, label='Threaded', color='orange', alpha=0.7)
    ax9.bar(x_pos + width, async_stats, width, label='Async', color='green', alpha=0.7)
    
    ax9.set_title('Performance Metrics Comparison')
    ax9.set_ylabel('Value (Requests/10, ms)')
    ax9.set_xticks(x_pos)
    ax9.set_xticklabels(metrics)
    ax9.legend()
    ax9.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    print("\n" + "="*50)
    print("Interactive Plot Controls:")
    print("="*50)
    print("- Pan: Hold left mouse button and drag")
    print("- Zoom: Use scroll wheel or zoom button")
    print("- Reset: Click home button")
    print("- Save: Click save button")
    print("="*50)
    
    plt.show(block=True)


# ============================================
# Main Execution
# ============================================
if __name__ == "__main__":
    EC2_URL = "http://54.200.242.229:8080/albums"
    TEST_DURATION = 30  # seconds
    
    print("Load Testing Comparison")
    print("=" * 50)
    
    # Test 1: Session with connection pooling
    print("\n1. Testing with Session (Connection Pooling)...")
    session_times = session_load_test(EC2_URL, TEST_DURATION)
    print_statistics(session_times, "Session Test")
    
    # Test 2: Threaded approach
    print("\n2. Testing with Thread Pool (10 workers)...")
    threaded_times = threaded_load_test(EC2_URL, TEST_DURATION, workers=10)
    print_statistics(threaded_times, "Threaded Test")
    
    # Test 3: Async approach (most efficient)
    print("\n3. Testing with Async/Await (10 concurrent)...")
    async_times = asyncio.run(async_load_test(EC2_URL, TEST_DURATION, concurrent_requests=10))
    print_statistics(async_times, "Async Test")
    
    # Comparison
    print(f"\n{'='*50}")
    print("COMPARISON")
    print(f"{'='*50}")
    print(f"Session Test:    {len(session_times):4d} requests")
    print(f"Threaded Test:   {len(threaded_times):4d} requests")
    print(f"Async Test:      {len(async_times):4d} requests")
    
    if len(session_times) > 0 and len(async_times) > 0:
        print(f"\nAsync approach handled {len(async_times) / len(session_times):.1f}x more requests!")
    
    # Create interactive visualizations
    create_interactive_plots(session_times, threaded_times, async_times)


"""
PROFESSIONAL LOAD TESTING TOOLS:
================================

1. **Locust** (Python, most popular)
   - Web UI for real-time monitoring
   - Distributed load testing
   - Install: pip install locust
   - Usage: Define user behavior in Python

2. **k6** (JavaScript, modern)
   - CLI tool with great reporting
   - Written in Go, very efficient
   - Great for CI/CD integration
   - Install: https://k6.io/docs/getting-started/installation/

3. **Apache JMeter** (Java, enterprise)
   - GUI for test planning
   - Extensive plugins
   - Industry standard

4. **Artillery** (Node.js)
   - Simple YAML config
   - Good for APIs
   - Install: npm install -g artillery

5. **Gatling** (Scala)
   - High performance
   - Great reports
   - Good for enterprise

6. **wrk** (C, lightweight)
   - Command-line only
   - Extremely fast
   - Install: https://github.com/wg/wrk

RECOMMENDATION:
- For learning/simple: Use this script's async method
- For professional: Use Locust or k6
- For CI/CD: Use k6 or Artillery
- For enterprise: Use JMeter or Gatling
"""
