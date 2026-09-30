import requests
import time
import statistics
from datetime import datetime
from database import record_metric, get_connection

class PerformanceCollector:
    """Collects performance metrics from a target endpoint."""
    
    def __init__(self, endpoint_url, name="collector", sample_size=5):
        self.endpoint_url = endpoint_url
        self.name = name
        self.sample_size = sample_size
        self.responses = []
    
    def collect_sample(self, verbose=False):
        """Collect one performance measurement."""
        try:
            start = time.time()
            response = requests.get(self.endpoint_url, timeout=10)
            elapsed_ms = (time.time() - start) * 1000
            
            status = response.status_code
            self.responses.append(elapsed_ms)
            
            if verbose:
                print(f"  {datetime.now().strftime('%H:%M:%S')} - {elapsed_ms:.1f}ms (HTTP {status})")
            
            return elapsed_ms
        except requests.exceptions.Timeout:
            if verbose:
                print(f"  {datetime.now().strftime('%H:%M:%S')} - Timeout")
            return None
        except requests.exceptions.ConnectionError:
            if verbose:
                print(f"  {datetime.now().strftime('%H:%M:%S')} - Connection error")
            return None
    
    def collect_batch(self, interval=1.0, verbose=False):
        """Collect a batch of samples and store aggregate."""
        self.responses = []
        
        if verbose:
            print(f"\n[{self.name}] Collecting {self.sample_size} samples...")
        
        for i in range(self.sample_size):
            self.collect_sample(verbose=verbose)
            if i < self.sample_size - 1:
                time.sleep(interval)
        
        if self.responses:
            avg_ms = statistics.mean(self.responses)
            median_ms = statistics.median(self.responses)
            min_ms = min(self.responses)
            max_ms = max(self.responses)
            
            record_metric(avg_ms, endpoint=self.endpoint_url)
            
            if verbose:
                print(f"\n  Summary:")
                print(f"    Average: {avg_ms:.1f}ms")
                print(f"    Median:  {median_ms:.1f}ms")
                print(f"    Min/Max: {min_ms:.1f}ms / {max_ms:.1f}ms")
            
            return {
                'avg': avg_ms,
                'median': median_ms,
                'min': min_ms,
                'max': max_ms,
                'count': len(self.responses)
            }
        
        return None
    
    def get_last_n_metrics(self, n=10):
        """Retrieve the last N metrics from database."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT timestamp, response_time_ms 
        FROM metrics 
        WHERE endpoint = ?
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (self.endpoint_url, n))
        
        results = cursor.fetchall()
        conn.close()
        
        return list(reversed(results))
