"""
Prometheus Metrics Exporter for YouTube MCP Server
==================================================

Exports operational metrics in Prometheus format for monitoring and alerting.

Metrics Categories:
1. Request Metrics: Total requests, errors, latency
2. Security Metrics: Prompt injection attempts, rate limit hits, CORS violations
3. YouTube API Metrics: Quota usage, API errors, cache hits
4. Resource Metrics: Memory usage, active connections

Author: Claude + Henry
Date: October 2025
Version: 1.0.0
"""

import time
import psutil
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from threading import Lock
from datetime import datetime, timedelta

@dataclass
class MetricValue:
    """Single metric value with timestamp"""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class Metric:
    """Prometheus metric definition"""
    name: str
    help_text: str
    metric_type: str  # counter, gauge, histogram
    values: List[MetricValue] = field(default_factory=list)
    
class PrometheusExporter:
    """
    Prometheus metrics exporter for YouTube MCP Server
    
    Thread-safe metric collection and exposition in Prometheus text format.
    """
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.lock = Lock()
        self.start_time = time.time()
        
        # Initialize core metrics
        self._init_metrics()
        
    def _init_metrics(self):
        """Initialize default metrics"""
        
        # Request metrics
        self.register_counter(
            "mcp_requests_total",
            "Total number of MCP requests"
        )
        self.register_counter(
            "mcp_errors_total",
            "Total number of errors"
        )
        self.register_histogram(
            "mcp_request_duration_seconds",
            "Request duration in seconds"
        )
        
        # Security metrics
        self.register_counter(
            "mcp_security_prompt_injection_attempts",
            "Prompt injection attempts detected"
        )
        self.register_counter(
            "mcp_security_rate_limit_hits",
            "Rate limit violations"
        )
        self.register_counter(
            "mcp_security_cors_violations",
            "CORS policy violations"
        )
        self.register_counter(
            "mcp_security_invalid_signatures",
            "Invalid request signatures"
        )
        
        # YouTube API metrics
        self.register_gauge(
            "mcp_youtube_quota_remaining",
            "Remaining YouTube API quota"
        )
        self.register_counter(
            "mcp_youtube_api_errors",
            "YouTube API errors"
        )
        self.register_counter(
            "mcp_cache_hits",
            "Cache hits"
        )
        self.register_counter(
            "mcp_cache_misses",
            "Cache misses"
        )
        
        # OAuth metrics
        self.register_counter(
            "mcp_oauth_token_refreshes",
            "OAuth token refresh operations"
        )
        self.register_counter(
            "mcp_oauth_errors",
            "OAuth authentication errors"
        )
        
        # System metrics
        self.register_gauge(
            "mcp_memory_usage_bytes",
            "Memory usage in bytes"
        )
        self.register_gauge(
            "mcp_cpu_usage_percent",
            "CPU usage percentage"
        )
        self.register_gauge(
            "mcp_uptime_seconds",
            "Server uptime in seconds"
        )
        
    def register_counter(self, name: str, help_text: str):
        """Register a counter metric"""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = Metric(
                    name=name,
                    help_text=help_text,
                    metric_type="counter"
                )
    
    def register_gauge(self, name: str, help_text: str):
        """Register a gauge metric"""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = Metric(
                    name=name,
                    help_text=help_text,
                    metric_type="gauge"
                )
    
    def register_histogram(self, name: str, help_text: str):
        """Register a histogram metric"""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = Metric(
                    name=name,
                    help_text=help_text,
                    metric_type="histogram"
                )
    
    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self.lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if metric.metric_type == "counter":
                    # Find existing label set or create new
                    existing = next(
                        (mv for mv in metric.values if mv.labels == (labels or {})),
                        None
                    )
                    if existing:
                        existing.value += value
                        existing.timestamp = time.time()
                    else:
                        metric.values.append(
                            MetricValue(value=value, labels=labels or {})
                        )
    
    def set(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        with self.lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if metric.metric_type == "gauge":
                    # Find existing label set or create new
                    existing = next(
                        (mv for mv in metric.values if mv.labels == (labels or {})),
                        None
                    )
                    if existing:
                        existing.value = value
                        existing.timestamp = time.time()
                    else:
                        metric.values.append(
                            MetricValue(value=value, labels=labels or {})
                        )
    
    def observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram observation"""
        with self.lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if metric.metric_type == "histogram":
                    metric.values.append(
                        MetricValue(value=value, labels=labels or {})
                    )
                    # Keep only last 1000 observations per label set
                    if len(metric.values) > 1000:
                        metric.values = metric.values[-1000:]
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            process = psutil.Process(os.getpid())
            
            # Memory
            memory_info = process.memory_info()
            self.set("mcp_memory_usage_bytes", memory_info.rss)
            
            # CPU
            cpu_percent = process.cpu_percent(interval=0.1)
            self.set("mcp_cpu_usage_percent", cpu_percent)
            
            # Uptime
            uptime = time.time() - self.start_time
            self.set("mcp_uptime_seconds", uptime)
            
        except Exception as e:
            print(f"Error updating system metrics: {e}")
    
    def generate_prometheus_text(self) -> str:
        """
        Generate Prometheus text exposition format
        
        Returns:
            str: Metrics in Prometheus format
        """
        with self.lock:
            lines = []
            
            for metric in self.metrics.values():
                # Add HELP line
                lines.append(f"# HELP {metric.name} {metric.help_text}")
                # Add TYPE line
                lines.append(f"# TYPE {metric.name} {metric.metric_type}")
                
                if metric.metric_type == "histogram":
                    # Group by labels
                    label_groups: Dict[str, List[float]] = {}
                    for mv in metric.values:
                        label_str = self._format_labels(mv.labels)
                        if label_str not in label_groups:
                            label_groups[label_str] = []
                        label_groups[label_str].append(mv.value)
                    
                    # Generate histogram buckets
                    for label_str, values in label_groups.items():
                        if values:
                            sorted_values = sorted(values)
                            count = len(sorted_values)
                            total = sum(sorted_values)
                            
                            # Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, +Inf
                            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
                            
                            for bucket in buckets:
                                bucket_count = sum(1 for v in sorted_values if v <= bucket)
                                bucket_labels = f'{label_str},le="{bucket}"' if label_str else f'le="{bucket}"'
                                lines.append(f'{metric.name}_bucket{{{bucket_labels}}} {bucket_count}')
                            
                            # +Inf bucket
                            inf_labels = f'{label_str},le="+Inf"' if label_str else 'le="+Inf"'
                            lines.append(f'{metric.name}_bucket{{{inf_labels}}} {count}')
                            
                            # Sum and count
                            lines.append(f'{metric.name}_sum{{{label_str}}} {total}')
                            lines.append(f'{metric.name}_count{{{label_str}}} {count}')
                else:
                    # Counter or Gauge
                    for mv in metric.values:
                        label_str = self._format_labels(mv.labels)
                        lines.append(f"{metric.name}{{{label_str}}} {mv.value}")
            
            return "\n".join(lines) + "\n"
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus exposition"""
        if not labels:
            return ""
        
        formatted = []
        for key, value in sorted(labels.items()):
            # Escape quotes and backslashes
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
            formatted.append(f'{key}="{escaped_value}"')
        
        return ",".join(formatted)
    
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current value of a metric"""
        with self.lock:
            if name not in self.metrics:
                return None
            
            metric = self.metrics[name]
            if not metric.values:
                return None
            
            if labels:
                mv = next((mv for mv in metric.values if mv.labels == labels), None)
                return mv.value if mv else None
            else:
                return metric.values[-1].value if metric.values else None

# Global exporter instance
_exporter: Optional[PrometheusExporter] = None

def get_exporter() -> PrometheusExporter:
    """Get global PrometheusExporter instance"""
    global _exporter
    if _exporter is None:
        _exporter = PrometheusExporter()
    return _exporter

def increment(name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
    """Increment a counter metric (convenience function)"""
    get_exporter().increment(name, value, labels)

def set_gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Set a gauge metric (convenience function)"""
    get_exporter().set(name, value, labels)

def observe(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """Record histogram observation (convenience function)"""
    get_exporter().observe(name, value, labels)

def generate_metrics() -> str:
    """Generate Prometheus metrics text (convenience function)"""
    exporter = get_exporter()
    exporter.update_system_metrics()
    return exporter.generate_prometheus_text()
