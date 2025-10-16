"""
Template Performance Testing and Optimization
Provides tools for testing template performance and optimization
"""

import time
import os
from functools import wraps
from flask import current_app, render_template_string
import threading
from collections import defaultdict

# Try to import psutil, fallback if not available
try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Create a dummy psutil class for type hints
    class psutil:  # type: ignore
        class Process:
            def memory_info(self):
                return type('MemoryInfo', (), {'rss': 0, 'vms': 0})()
            def cpu_percent(self):
                return 0.0

# Performance metrics storage
_performance_metrics = defaultdict(list)
_template_times = defaultdict(list)
_memory_usage = []

class PerformanceMonitor:
    """Monitor template rendering performance"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_end = None
        self.template_name = None
    
    def start(self, template_name):
        """Start monitoring"""
        self.template_name = template_name
        self.start_time = time.time()
        
        if PSUTIL_AVAILABLE:
            self.memory_start = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        else:
            self.memory_start = 0
            
        return self
    
    def stop(self):
        """Stop monitoring and record metrics"""
        self.end_time = time.time()
        
        if PSUTIL_AVAILABLE:
            self.memory_end = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        else:
            self.memory_end = 0
        
        render_time = self.end_time - self.start_time
        memory_used = self.memory_end - self.memory_start
        
        # Record metrics
        _template_times[self.template_name].append(render_time)
        _memory_usage.append({
            'template': self.template_name,
            'memory_mb': memory_used,
            'timestamp': self.end_time
        })
        
        # Log if current_app is available
        try:
            current_app.logger.info(
                f"Template {self.template_name}: {render_time:.3f}s, "
                f"Memory: {memory_used:.2f}MB"
            )
        except RuntimeError:
            # current_app not available
            pass
        
        return {
            'template': self.template_name,
            'render_time': render_time,
            'memory_used': memory_used
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

def monitor_template_performance(template_name):
    """Decorator to monitor template rendering performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with PerformanceMonitor().start(template_name) as monitor:
                result = func(*args, **kwargs)
                monitor.stop()
                return result
        return wrapper
    return decorator

def get_template_performance_stats():
    """Get template performance statistics"""
    stats = {}
    
    for template_name, times in _template_times.items():
        if times:
            stats[template_name] = {
                'count': len(times),
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'total_time': sum(times)
            }
    
    return stats

def get_memory_stats():
    """Get memory usage statistics"""
    if not _memory_usage:
        return {}
    
    total_memory = sum(entry['memory_mb'] for entry in _memory_usage)
    avg_memory = total_memory / len(_memory_usage)
    
    return {
        'total_memory_mb': total_memory,
        'avg_memory_mb': avg_memory,
        'max_memory_mb': max(entry['memory_mb'] for entry in _memory_usage),
        'min_memory_mb': min(entry['memory_mb'] for entry in _memory_usage),
        'samples': len(_memory_usage)
    }

def benchmark_template(template_content, context=None, iterations=100):
    """Benchmark template rendering performance"""
    if context is None:
        context = {}
    
    times = []
    memory_usage = []
    
    for i in range(iterations):
        # Measure time
        start_time = time.time()
        
        if PSUTIL_AVAILABLE:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            start_memory = 0
        
        # Render template
        render_template_string(template_content, **context)
        
        end_time = time.time()
        
        if PSUTIL_AVAILABLE:
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            end_memory = 0
        
        times.append(end_time - start_time)
        memory_usage.append(end_memory - start_memory)
    
    return {
        'iterations': iterations,
        'avg_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'avg_memory': sum(memory_usage) / len(memory_usage),
        'times': times,
        'memory_usage': memory_usage
    }

def optimize_template_rendering():
    """Provide optimization recommendations based on performance data"""
    recommendations = []
    
    # Analyze template performance
    stats = get_template_performance_stats()
    
    for template_name, template_stats in stats.items():
        avg_time = template_stats['avg_time']
        
        if avg_time > 0.1:  # Templates taking more than 100ms
            recommendations.append({
                'template': template_name,
                'issue': 'Slow rendering',
                'avg_time': avg_time,
                'suggestion': 'Consider caching or optimizing database queries'
            })
        
        if template_stats['max_time'] > avg_time * 3:  # High variance
            recommendations.append({
                'template': template_name,
                'issue': 'High performance variance',
                'variance': template_stats['max_time'] - template_stats['min_time'],
                'suggestion': 'Check for conditional logic or external dependencies'
            })
    
    # Analyze memory usage
    memory_stats = get_memory_stats()
    if memory_stats.get('avg_memory_mb', 0) > 10:  # More than 10MB average
        recommendations.append({
            'template': 'Overall',
            'issue': 'High memory usage',
            'avg_memory': memory_stats['avg_memory_mb'],
            'suggestion': 'Consider lazy loading or reducing data size'
        })
    
    return recommendations

def clear_performance_data():
    """Clear all performance monitoring data"""
    global _performance_metrics, _template_times, _memory_usage
    _performance_metrics.clear()
    _template_times.clear()
    _memory_usage.clear()

# Template optimization utilities
def optimize_includes(template_content):
    """Optimize template includes for better performance"""
    optimizations = []
    
    # Count includes
    include_count = template_content.count('{% include')
    if include_count > 10:
        optimizations.append({
            'type': 'too_many_includes',
            'count': include_count,
            'suggestion': 'Consider combining includes or using macros'
        })
    
    # Check for nested includes
    if '{% include' in template_content and '{% include' in template_content:
        optimizations.append({
            'type': 'nested_includes',
            'suggestion': 'Avoid nested includes for better performance'
        })
    
    return optimizations

def optimize_loops(template_content):
    """Optimize template loops for better performance"""
    optimizations = []
    
    # Count loops
    loop_count = template_content.count('{% for')
    if loop_count > 5:
        optimizations.append({
            'type': 'too_many_loops',
            'count': loop_count,
            'suggestion': 'Consider pagination or limiting loop iterations'
        })
    
    # Check for nested loops
    if template_content.count('{% for') > 1:
        optimizations.append({
            'type': 'nested_loops',
            'suggestion': 'Avoid nested loops, consider restructuring data'
        })
    
    return optimizations

def get_template_optimization_report(template_content):
    """Generate comprehensive optimization report for a template"""
    report = {
        'template_size': len(template_content),
        'line_count': len(template_content.split('\n')),
        'includes': optimize_includes(template_content),
        'loops': optimize_loops(template_content),
        'recommendations': []
    }
    
    # General recommendations
    if report['template_size'] > 10000:  # 10KB
        report['recommendations'].append({
            'type': 'large_template',
            'suggestion': 'Consider breaking into smaller components'
        })
    
    if report['line_count'] > 500:
        report['recommendations'].append({
            'type': 'long_template',
            'suggestion': 'Split template into multiple files'
        })
    
    return report

# Performance testing utilities
def run_performance_tests():
    """Run comprehensive performance tests"""
    results = {
        'template_stats': get_template_performance_stats(),
        'memory_stats': get_memory_stats(),
        'optimization_recommendations': optimize_template_rendering(),
        'timestamp': time.time()
    }
    
    return results

def export_performance_data():
    """Export performance data for analysis"""
    return {
        'template_times': dict(_template_times),
        'memory_usage': _memory_usage,
        'stats': get_template_performance_stats(),
        'memory_stats': get_memory_stats()
    }