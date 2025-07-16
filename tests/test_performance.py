"""
Performance benchmarking and load testing for Fire Fighting Robot API
"""
import asyncio
import time
import statistics
import httpx
import concurrent.futures
from pathlib import Path
import sys
import json
import aiohttp
import numpy as np
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.api.documented_api import app
from app.core.authentication import auth_manager

class PerformanceTester:
    """Performance testing utilities"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    async def benchmark_endpoint(self, endpoint, method="GET", data=None, 
                                headers=None, num_requests=100, concurrent=10):
        """Benchmark a specific endpoint"""
        print(f"\n🔥 Benchmarking {method} {endpoint}")
        print(f"   Requests: {num_requests}, Concurrent: {concurrent}")
        
        response_times = []
        errors = 0
        
        async def make_request(client):
            try:
                start_time = time.time()
                if method == "GET":
                    response = await client.get(endpoint, headers=headers)
                elif method == "POST":
                    response = await client.post(endpoint, json=data, headers=headers)
                elif method == "PUT":
                    response = await client.put(endpoint, json=data, headers=headers)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
                if response.status_code >= 400:
                    return False
                return True
                
            except Exception as e:
                return False
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent)
        
        async def limited_request(client):
            async with semaphore:
                return await make_request(client)
        
        # Run benchmark
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            start_time = time.time()
            
            tasks = [limited_request(client) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
        
        # Calculate statistics
        successful_requests = sum(1 for r in results if r)
        errors = num_requests - successful_requests
        
        if response_times:
            stats = {
                "total_requests": num_requests,
                "successful_requests": successful_requests,
                "errors": errors,
                "total_time": total_time,
                "requests_per_second": num_requests / total_time,
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "p95_response_time": self._percentile(response_times, 95),
                "p99_response_time": self._percentile(response_times, 99)
            }
        else:
            stats = {"error": "No successful requests"}
        
        # Store results
        self.results[f"{method} {endpoint}"] = stats
        
        # Print results
        if "error" not in stats:
            print(f"   ✅ Success Rate: {(successful_requests/num_requests)*100:.1f}%")
            print(f"   🚀 RPS: {stats['requests_per_second']:.1f}")
            print(f"   ⏱️  Avg Response Time: {stats['avg_response_time']:.1f}ms")
            print(f"   📊 P95: {stats['p95_response_time']:.1f}ms, P99: {stats['p99_response_time']:.1f}ms")
        else:
            print(f"   ❌ Benchmark failed: {stats['error']}")
        
        return stats
    
    def _percentile(self, data, p):
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = (p / 100.0) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def generate_report(self):
        """Generate performance report"""
        print("\n" + "="*70)
        print("🔥 FIRE FIGHTING ROBOT - PERFORMANCE REPORT")
        print("="*70)
        
        for endpoint, stats in self.results.items():
            if "error" not in stats:
                print(f"\n📍 {endpoint}")
                print(f"   RPS: {stats['requests_per_second']:.1f}")
                print(f"   Avg: {stats['avg_response_time']:.1f}ms")
                print(f"   P95: {stats['p95_response_time']:.1f}ms")
                print(f"   Success: {(stats['successful_requests']/stats['total_requests'])*100:.1f}%")
        
        print("\n" + "="*70)

async def run_performance_tests():
    """Run comprehensive performance tests"""
    tester = PerformanceTester()
    
    # Test unauthenticated endpoints
    await tester.benchmark_endpoint("/", num_requests=200, concurrent=20)
    await tester.benchmark_endpoint("/health", num_requests=200, concurrent=20)
    
    # Get authentication token for authenticated tests
    print("\n🔐 Getting authentication token...")
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        try:
            response = await client.post("/auth/login", json={
                "username": "testuser",
                "password": "testpass123"
            })
            if response.status_code == 200:
                token = response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                print("   ✅ Authentication successful")
                
                # Test authenticated endpoints
                sensor_data = {
                    "temperature": 25.0,
                    "smoke_density": 100.0,
                    "gas_level": 50.0,
                    "humidity": 45.0
                }
                
                await tester.benchmark_endpoint(
                    "/api/v2/sensors/reading", 
                    method="POST", 
                    data=sensor_data,
                    headers=headers,
                    num_requests=100,
                    concurrent=10
                )
                
                movement_data = {
                    "direction": "forward",
                    "speed": 50.0,
                    "duration": 1.0
                }
                
                await tester.benchmark_endpoint(
                    "/api/v2/robot/move",
                    method="POST",
                    data=movement_data,
                    headers=headers,
                    num_requests=50,
                    concurrent=5
                )
                
                await tester.benchmark_endpoint(
                    "/api/v2/robot/status",
                    headers=headers,
                    num_requests=100,
                    concurrent=10
                )
                
            else:
                print("   ❌ Authentication failed - skipping authenticated tests")
                
        except Exception as e:
            print(f"   ❌ Authentication error: {e}")
    
    # Generate final report
    tester.generate_report()

class LoadTester:
    """Stress testing utilities"""
    
    @staticmethod
    async def stress_test_sensor_endpoints(duration_seconds=60):
        """Stress test sensor endpoints for specified duration"""
        print(f"\n🔥 Running stress test for {duration_seconds} seconds...")
        
        start_time = time.time()
        request_count = 0
        error_count = 0
        
        async def send_sensor_data():
            nonlocal request_count, error_count
            
            try:
                async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                    # Get token
                    auth_response = await client.post("/auth/login", json={
                        "username": "testuser",
                        "password": "testpass123"
                    })
                    
                    if auth_response.status_code != 200:
                        error_count += 1
                        return
                    
                    token = auth_response.json()["access_token"]
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    while time.time() - start_time < duration_seconds:
                        sensor_data = {
                            "temperature": 20.0 + (request_count % 30),
                            "smoke_density": 50.0 + (request_count % 200),
                            "gas_level": 30.0 + (request_count % 100),
                            "humidity": 40.0 + (request_count % 40)
                        }
                        
                        response = await client.post(
                            "/api/v2/sensors/reading",
                            json=sensor_data,
                            headers=headers
                        )
                        
                        request_count += 1
                        if response.status_code >= 400:
                            error_count += 1
                        
                        await asyncio.sleep(0.1)  # Small delay between requests
                        
            except Exception as e:
                error_count += 1
        
        # Run multiple concurrent stress testers
        tasks = [send_sensor_data() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        rps = request_count / total_time
        error_rate = (error_count / request_count * 100) if request_count > 0 else 0
        
        print(f"   📊 Stress Test Results:")
        print(f"   Total Requests: {request_count}")
        print(f"   Total Errors: {error_count}")
        print(f"   Error Rate: {error_rate:.2f}%")
        print(f"   Average RPS: {rps:.1f}")

def benchmark_ml_inference():
    """Benchmark machine learning inference performance"""
    print("\n🤖 Benchmarking ML Inference...")
    
    try:
        from vision.object_detector import ObjectDetector
        import numpy as np
        from PIL import Image
        
        detector = ObjectDetector()
        
        # Create dummy image data for testing
        dummy_image = Image.fromarray(np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8))
        
        # Benchmark inference
        num_inferences = 50
        times = []
        
        for i in range(num_inferences):
            start_time = time.time()
            results = detector.detect_objects(dummy_image)
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"   🎯 ML Inference Results:")
        print(f"   Average Time: {avg_time:.1f}ms")
        print(f"   Min Time: {min_time:.1f}ms") 
        print(f"   Max Time: {max_time:.1f}ms")
        print(f"   Throughput: {1000/avg_time:.1f} FPS")
        
    except Exception as e:
        print(f"   ❌ ML Inference benchmark failed: {e}")

def benchmark_database_operations():
    """Benchmark database operations"""
    print("\n💾 Benchmarking Database Operations...")
    
    try:
        import sqlite3
        from pathlib import Path
        
        db_path = Path("app/firebot.db")
        if not db_path.exists():
            print("   ❌ Database not found")
            return
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Benchmark sensor reading inserts
        num_operations = 1000
        start_time = time.time()
        
        for i in range(num_operations):
            cursor.execute("""
                INSERT INTO sensor_readings (temperature, smoke_density, gas_level, humidity, timestamp)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (25.0 + i % 50, 100.0 + i % 200, 50.0 + i % 100, 45.0 + i % 40))
        
        conn.commit()
        end_time = time.time()
        
        insert_time = (end_time - start_time) * 1000
        ops_per_second = num_operations / (end_time - start_time)
        
        print(f"   📝 Insert Performance:")
        print(f"   {num_operations} inserts in {insert_time:.1f}ms")
        print(f"   {ops_per_second:.1f} operations/second")
        
        # Benchmark queries
        start_time = time.time()
        for _ in range(100):
            cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 10")
            cursor.fetchall()
        end_time = time.time()
        
        query_time = (end_time - start_time) * 1000
        queries_per_second = 100 / (end_time - start_time)
        
        print(f"   🔍 Query Performance:")
        print(f"   100 queries in {query_time:.1f}ms")
        print(f"   {queries_per_second:.1f} queries/second")
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Database benchmark failed: {e}")

async def test_api_endpoint(url: str, session: aiohttp.ClientSession) -> Dict:
    """Test single API endpoint performance"""
    start_time = time.time()
    try:
        async with session.get(url) as response:
            await response.text()
            end_time = time.time()
            return {
                'url': url,
                'status': response.status,
                'response_time': end_time - start_time,
                'success': response.status == 200
            }
    except Exception as e:
        end_time = time.time()
        return {
            'url': url,
            'status': 0,
            'response_time': end_time - start_time,
            'success': False,
            'error': str(e)
        }

async def load_test_api(base_url: str = "http://localhost:8000", 
                       concurrent_requests: int = 10, 
                       total_requests: int = 100) -> Dict:
    """Perform load testing on API endpoints"""
    
    endpoints = [
        "/",
        "/health",
        "/api/v1/status",
        "/video"  # This might be slower
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"Testing {url}...")
            
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def limited_request():
                async with semaphore:
                    return await test_api_endpoint(url, session)
            
            # Run requests
            tasks = [limited_request() for _ in range(total_requests)]
            endpoint_results = await asyncio.gather(*tasks)
            
            # Calculate statistics
            response_times = [r['response_time'] for r in endpoint_results if r['success']]
            success_rate = sum(1 for r in endpoint_results if r['success']) / len(endpoint_results)
            
            if response_times:
                stats = {
                    'endpoint': endpoint,
                    'total_requests': total_requests,
                    'successful_requests': len(response_times),
                    'success_rate': success_rate,
                    'avg_response_time': statistics.mean(response_times),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                    'median_response_time': statistics.median(response_times),
                    'p95_response_time': np.percentile(response_times, 95) if len(response_times) > 1 else response_times[0]
                }
            else:
                stats = {
                    'endpoint': endpoint,
                    'total_requests': total_requests,
                    'successful_requests': 0,
                    'success_rate': 0,
                    'error': 'No successful requests'
                }
            
            results.append(stats)
            print(f"✅ {endpoint}: {stats.get('success_rate', 0):.2%} success rate")
    
    return results

def test_vision_processing_performance():
    """Test vision processing performance"""
    from vision.object_detector import ObjectDetector
    from vision.fire_segmentation import FireSegmentation
    
    # Create test image
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Initialize components
    try:
        detector = ObjectDetector()
        segmentation = FireSegmentation()
        
        # Test object detection speed
        start_time = time.time()
        for _ in range(10):
            detections = detector.detect_objects(test_frame)
        detection_time = (time.time() - start_time) / 10
        
        # Test segmentation speed
        start_time = time.time()
        for _ in range(10):
            mask = segmentation.get_fire_mask(test_frame)
        segmentation_time = (time.time() - start_time) / 10
        
        print(f"🔍 Vision Performance:")
        print(f"  Object Detection: {detection_time:.3f}s per frame ({1/detection_time:.1f} FPS)")
        print(f"  Fire Segmentation: {segmentation_time:.3f}s per frame ({1/segmentation_time:.1f} FPS)")
        
        return {
            'object_detection_fps': 1/detection_time,
            'segmentation_fps': 1/segmentation_time,
            'combined_fps': 1/(detection_time + segmentation_time)
        }
        
    except Exception as e:
        print(f"❌ Vision performance test failed: {e}")
        return None

async def main():
    """Main performance testing function"""
    print("🔥 FIRE FIGHTING ROBOT - PERFORMANCE TESTING SUITE")
    print("="*60)
    
    # Run API performance tests
    await run_performance_tests()
    
    # Run stress tests
    await LoadTester.stress_test_sensor_endpoints(duration_seconds=30)
    
    # Run ML inference benchmarks
    benchmark_ml_inference()
    
    # Run database benchmarks
    benchmark_database_operations()
    
    # Test API performance
    print("\n📊 API Load Testing...")
    api_results = await load_test_api(concurrent_requests=5, total_requests=50)
    
    print("\n📈 API Performance Results:")
    for result in api_results:
        if 'avg_response_time' in result:
            print(f"  {result['endpoint']}:")
            print(f"    Success Rate: {result['success_rate']:.2%}")
            print(f"    Avg Response: {result['avg_response_time']:.3f}s")
            print(f"    P95 Response: {result['p95_response_time']:.3f}s")
        else:
            print(f"  {result['endpoint']}: FAILED - {result.get('error', 'Unknown error')}")
    
    # Test vision performance
    print("\n🔍 Vision System Performance...")
    vision_results = test_vision_processing_performance()
    
    # Overall assessment
    print("\n🎯 Performance Assessment:")
    
    # Check API performance
    api_healthy = all(r.get('success_rate', 0) > 0.95 for r in api_results)
    api_fast = all(r.get('avg_response_time', float('inf')) < 1.0 for r in api_results)
    
    print(f"  API Reliability: {'✅ GOOD' if api_healthy else '⚠️ NEEDS IMPROVEMENT'}")
    print(f"  API Speed: {'✅ GOOD' if api_fast else '⚠️ SLOW'}")
    
    if vision_results:
        vision_fps = vision_results.get('combined_fps', 0)
        vision_good = vision_fps >= 10  # At least 10 FPS for real-time
        print(f"  Vision Speed: {'✅ GOOD' if vision_good else '⚠️ SLOW'} ({vision_fps:.1f} FPS)")
    
    print("\n✅ Performance testing completed!")

if __name__ == "__main__":
    asyncio.run(main())
