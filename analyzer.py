import statistics
from datetime import datetime, timedelta
from database import get_connection

class RegressionAnalyzer:
    """Detects performance regressions in metrics data."""
    
    def __init__(self, threshold_percent=15, baseline_window_hours=6):
        """
        Initialize the analyzer.
        
        Args:
            threshold_percent: How much degradation (%) triggers a regression
            baseline_window_hours: How many hours back to use for baseline
        """
        self.threshold_percent = threshold_percent
        self.baseline_window_hours = baseline_window_hours
    
    def get_baseline_metrics(self, endpoint, hours=None):
        """Get the baseline (normal) response times."""
        if hours is None:
            hours = self.baseline_window_hours
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
        SELECT response_time_ms 
        FROM metrics 
        WHERE endpoint = ? AND timestamp < ?
        ORDER BY timestamp
        ''', (endpoint, cutoff_time))
        
        metrics = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return metrics
    
    def get_recent_metrics(self, endpoint, hours=1):
        """Get recent metrics (potentially affected by a deployment)."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
        SELECT response_time_ms, timestamp 
        FROM metrics 
        WHERE endpoint = ? AND timestamp >= ?
        ORDER BY timestamp
        ''', (endpoint, cutoff_time))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def detect_regression(self, endpoint, recent_hours=1):
        """Detect if there's a performance regression."""
        baseline = self.get_baseline_metrics(endpoint)
        recent = self.get_recent_metrics(endpoint, hours=recent_hours)
        
        if not baseline or not recent:
            return None
        
        # Calculate baseline stats
        baseline_avg = statistics.mean(baseline)
        baseline_stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0
        
        # Calculate recent stats
        recent_metrics = [r[0] for r in recent]
        recent_avg = statistics.mean(recent_metrics)
        
        # Calculate degradation percentage
        degradation_percent = ((recent_avg - baseline_avg) / baseline_avg) * 100
        
        # Check if it's a regression
        if degradation_percent > self.threshold_percent:
            return {
                'endpoint': endpoint,
                'detected_at': datetime.now(),
                'baseline_ms': round(baseline_avg, 2),
                'current_ms': round(recent_avg, 2),
                'degradation_percent': round(degradation_percent, 1),
                'recent_samples': len(recent),
                'baseline_samples': len(baseline),
                'first_regression_time': recent[0][1] if recent else None
            }
        
        return None
    
    def find_likely_culprit_deployment(self, endpoint, regression_time):
        """Find which deployment most likely caused the regression."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Find deployments within 30 minutes before the regression
        search_start = regression_time - timedelta(minutes=30)
        
        cursor.execute('''
        SELECT id, version, timestamp, commit_hash
        FROM deployments 
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp DESC
        LIMIT 1
        ''', (search_start, regression_time))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'version': result[1],
                'timestamp': result[2],
                'commit_hash': result[3]
            }
        
        return None
    
    def check_all_endpoints(self, recent_hours=1, verbose=False):
        """Check all monitored endpoints for regressions."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all unique endpoints
        cursor.execute('SELECT DISTINCT endpoint FROM metrics')
        endpoints = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        regressions = []
        
        for endpoint in endpoints:
            regression = self.detect_regression(endpoint, recent_hours=recent_hours)
            
            if regression:
                # Find likely culprit deployment
                culprit = self.find_likely_culprit_deployment(
                    endpoint, 
                    regression['first_regression_time']
                )
                regression['likely_deployment'] = culprit
                
                regressions.append(regression)
                
                if verbose:
                    print(f"\n🚨 REGRESSION DETECTED:")
                    print(f"   Endpoint: {endpoint}")
                    print(f"   Baseline: {regression['baseline_ms']}ms")
                    print(f"   Current:  {regression['current_ms']}ms")
                    print(f"   Increase: {regression['degradation_percent']}%")
                    if culprit:
                        print(f"   Likely caused by: v{culprit['version']} ({culprit['commit_hash']})")
        
        return regressions
