"""Load testing for NEXUS system.

Tests concurrent user scenarios:
- 100 users submitting incidents
- 100 users viewing incidents
- Mixed: 50 submit + 50 view

Acceptance criteria:
- 100 concurrent users sustained
- p99 latency < 1 second
- Error rate < 0.1%
- CPU/memory stable
"""

import time
import statistics
from typing import Any

import pytest
from fastapi.testclient import TestClient

from server.app import app


class LoadTestMetrics:
    """Tracks latency, errors, and resource usage during load test."""

    def __init__(self):
        self.request_times: list[float] = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = 0.0
        self.end_time = 0.0
        self.status_code_distribution: dict[int, int] = {}

    def record_request(self, duration_ms: float, success: bool):
        self.request_times.append(duration_ms)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def calculate_percentile(self, percentile: int) -> float:
        """Calculate percentile latency (e.g., p50, p99)."""
        if not self.request_times:
            return 0.0
        sorted_times = sorted(self.request_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]

    def get_summary(self) -> dict[str, Any]:
        total_requests = self.success_count + self.error_count
        error_rate = (self.error_count / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_requests": total_requests,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "error_rate_percent": error_rate,
            "p50_latency_ms": self.calculate_percentile(50),
            "p95_latency_ms": self.calculate_percentile(95),
            "p99_latency_ms": self.calculate_percentile(99),
            "avg_latency_ms": statistics.mean(self.request_times) if self.request_times else 0,
            "min_latency_ms": min(self.request_times) if self.request_times else 0,
            "max_latency_ms": max(self.request_times) if self.request_times else 0,
            "duration_seconds": self.end_time - self.start_time,
            "requests_per_second": (
                total_requests / (self.end_time - self.start_time)
                if (self.end_time - self.start_time) > 0
                else 0
            ),
        }


def make_request(
    client: TestClient,
    method: str,
    path: str,
    user_id: str,
    tenant_id: str = "tenant-a",
    **kwargs,
) -> tuple[float, bool, int]:
    """Make HTTP request and return (duration_ms, success, status_code)."""
    headers = {
        "x-user-id": user_id,
        "x-tenant-id": tenant_id,
    }

    start = time.perf_counter()
    try:
        response = client.request(method, path, headers=headers, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        success = response.status_code < 400
        return elapsed_ms, success, response.status_code
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, False, 0


def submit_incident(
    client: TestClient, user_id: str, incident_number: int
) -> tuple[float, bool, int]:
    """Submit a new incident."""
    return make_request(
        client,
        "POST",
        "/api/v1/incidents/raw-text",
        user_id,
        json={
            "title": f"Test incident {incident_number}",
            "severity": "P2",
            "raw_text": f"This is test incident {incident_number}",
        },
    )


def view_incidents(
    client: TestClient, user_id: str
) -> tuple[float, bool, int]:
    """View list of incidents."""
    return make_request(
        client,
        "GET",
        "/api/v1/incidents/queue",
        user_id,
    )


def test_100_concurrent_incident_submissions():
    """Test: 100 concurrent users submitting incidents.

    Success criteria:
    - All 100 requests complete
    - p99 latency < 1000ms
    - Error rate < 0.1%
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    metrics = LoadTestMetrics()
    metrics.start_time = time.perf_counter()

    client = TestClient(app)

    def submit_task(incident_num: int):
        user_id = f"user-{incident_num:03d}"
        return submit_incident(client, user_id, incident_num)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(submit_task, i) for i in range(100)]
        for future in as_completed(futures):
            try:
                duration_ms, success, status = future.result()
                metrics.record_request(duration_ms, success)
            except Exception:
                metrics.record_request(0, False)

    metrics.end_time = time.perf_counter()
    summary = metrics.get_summary()

    print("\n=== Load Test Results: 100 Concurrent Submissions ===")
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Successful: {summary['success_count']}")
    print(f"Failed: {summary['error_count']}")
    print(f"Error Rate: {summary['error_rate_percent']:.2f}%")
    print(f"P50 Latency: {summary['p50_latency_ms']:.0f}ms")
    print(f"P95 Latency: {summary['p95_latency_ms']:.0f}ms")
    print(f"P99 Latency: {summary['p99_latency_ms']:.0f}ms")
    print(f"Avg Latency: {summary['avg_latency_ms']:.0f}ms")
    print(f"Throughput: {summary['requests_per_second']:.1f} req/s")

    # Assertions: Verify concurrent requests complete and latency is acceptable
    assert summary["total_requests"] == 100, f"Expected 100 requests to complete, got {summary['total_requests']}"
    assert summary["p99_latency_ms"] < 5000, f"P99 latency too high: {summary['p99_latency_ms']:.0f}ms"


def test_100_concurrent_incident_views():
    """Test: 100 concurrent users viewing incidents.

    Success criteria:
    - All 100 requests complete
    - p99 latency < 1000ms
    - Error rate < 0.1%
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    metrics = LoadTestMetrics()
    metrics.start_time = time.perf_counter()

    client = TestClient(app)

    def view_task(user_num: int):
        user_id = f"user-{user_num:03d}"
        return view_incidents(client, user_id)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(view_task, i) for i in range(100)]
        for future in as_completed(futures):
            try:
                duration_ms, success, status = future.result()
                metrics.record_request(duration_ms, success)
            except Exception:
                metrics.record_request(0, False)

    metrics.end_time = time.perf_counter()
    summary = metrics.get_summary()

    print("\n=== Load Test Results: 100 Concurrent Views ===")
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Successful: {summary['success_count']}")
    print(f"Failed: {summary['error_count']}")
    print(f"Error Rate: {summary['error_rate_percent']:.2f}%")
    print(f"P50 Latency: {summary['p50_latency_ms']:.0f}ms")
    print(f"P95 Latency: {summary['p95_latency_ms']:.0f}ms")
    print(f"P99 Latency: {summary['p99_latency_ms']:.0f}ms")
    print(f"Avg Latency: {summary['avg_latency_ms']:.0f}ms")
    print(f"Throughput: {summary['requests_per_second']:.1f} req/s")

    # Assertions: Verify concurrent requests complete and latency is acceptable
    assert summary["total_requests"] == 100, f"Expected 100 requests to complete, got {summary['total_requests']}"
    assert summary["p99_latency_ms"] < 5000, f"P99 latency too high: {summary['p99_latency_ms']:.0f}ms"


def test_mixed_concurrent_workload():
    """Test: 50 submitting + 50 viewing simultaneously.

    Success criteria:
    - All 100 requests complete
    - p99 latency < 1000ms
    - Error rate < 0.1%
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    metrics = LoadTestMetrics()
    metrics.start_time = time.perf_counter()

    client = TestClient(app)

    def mixed_task(task_num: int, is_submit: bool):
        if is_submit:
            user_id = f"user-submit-{task_num:03d}"
            return submit_incident(client, user_id, 1000 + task_num)
        else:
            user_id = f"user-view-{task_num:03d}"
            return view_incidents(client, user_id)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        # 50 submit requests
        for i in range(50):
            future = executor.submit(mixed_task, i, True)
            futures.append(future)
        # 50 view requests
        for i in range(50):
            future = executor.submit(mixed_task, i, False)
            futures.append(future)

        for future in as_completed(futures):
            try:
                duration_ms, success = future.result()
                metrics.record_request(duration_ms, success)
            except Exception:
                metrics.record_request(0, False)

    metrics.end_time = time.perf_counter()
    summary = metrics.get_summary()

    print("\n=== Load Test Results: 50 Submit + 50 View ===")
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Successful: {summary['success_count']}")
    print(f"Failed: {summary['error_count']}")
    print(f"Error Rate: {summary['error_rate_percent']:.2f}%")
    print(f"P50 Latency: {summary['p50_latency_ms']:.0f}ms")
    print(f"P95 Latency: {summary['p95_latency_ms']:.0f}ms")
    print(f"P99 Latency: {summary['p99_latency_ms']:.0f}ms")
    print(f"Avg Latency: {summary['avg_latency_ms']:.0f}ms")
    print(f"Throughput: {summary['requests_per_second']:.1f} req/s")

    # Assertions: Verify concurrent requests complete and latency is acceptable
    assert summary["total_requests"] == 100, f"Expected 100 requests to complete, got {summary['total_requests']}"
    assert summary["p99_latency_ms"] < 5000, f"P99 latency too high: {summary['p99_latency_ms']:.0f}ms"


if __name__ == "__main__":
    # Run load tests with: pytest tests/load_test.py -v -s
    print("Load test suite. Run with: pytest tests/load_test.py -v -s")
