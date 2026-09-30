#!/usr/bin/env python3
import sys
import argparse
from datetime import datetime
from database import init_database, record_deployment, get_metrics_summary, get_connection
from collector import PerformanceCollector
from analyzer import RegressionAnalyzer

def cmd_collect(args):
    """Collect performance metrics from an endpoint."""
    collector = PerformanceCollector(
        endpoint_url=args.url,
        name=args.name or "collector",
        sample_size=args.samples
    )
    
    print(f"\n📊 Collecting metrics from: {args.url}")
    print(f"   Samples: {args.samples}, Interval: {args.interval}s\n")
    
    stats = collector.collect_batch(interval=args.interval, verbose=True)
    
    if stats:
        print(f"\n✓ Metrics recorded successfully")

def cmd_deploy(args):
    """Record a deployment event."""
    record_deployment(
        version=args.version,
        commit_hash=args.commit,
        description=args.desc
    )

def cmd_analyze(args):
    """Analyze metrics and detect regressions."""
    analyzer = RegressionAnalyzer(
        threshold_percent=args.threshold,
        baseline_window_hours=args.baseline
    )
    
    print(f"\n🔍 Analyzing regressions...")
    print(f"   Threshold: {args.threshold}%")
    print(f"   Recent window: {args.hours} hour(s)")
    print(f"   Baseline window: {args.baseline} hour(s)\n")
    
    regressions = analyzer.check_all_endpoints(recent_hours=args.hours, verbose=True)
    
    if not regressions:
        print("\n✓ No regressions detected")
    else:
        print(f"\n⚠️  Found {len(regressions)} regression(s)")

def cmd_status(args):
    """Show overall status."""
    print("\n📈 Performance Detector Status")
    print("=" * 50)
    
    summary = get_metrics_summary()
    
    print(f"\nMetrics Collected:    {summary['total_metrics']}")
    print(f"Average Response:     {summary['avg_response_time_ms']}ms")
    print(f"Deployments Recorded: {summary['total_deployments']}")
    
    print("\n" + "=" * 50)

def cmd_metrics(args):
    """Show recent metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT timestamp, endpoint, response_time_ms FROM metrics ORDER BY timestamp DESC LIMIT ?'
    cursor.execute(query, (args.count,))
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print("\nNo metrics found")
        return
    
    print("\n📊 Recent Metrics")
    print("=" * 70)
    print(f"{'Timestamp':<25} {'Endpoint':<30} {'Response (ms)':<10}")
    print("-" * 70)
    
    for timestamp, endpoint, response_time in results:
        short_endpoint = endpoint[-25:] if len(endpoint) > 25 else endpoint
        print(f"{timestamp:<25} {short_endpoint:<30} {response_time:>10.1f}")
    
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description='Performance Regression Detector')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Collect performance metrics')
    collect_parser.add_argument('url', help='Endpoint URL to monitor')
    collect_parser.add_argument('--name', help='Collector name', default='collector')
    collect_parser.add_argument('--samples', type=int, default=5, help='Number of samples')
    collect_parser.add_argument('--interval', type=float, default=1.0, help='Interval between requests')
    collect_parser.set_defaults(func=cmd_collect)
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Record a deployment')
    deploy_parser.add_argument('version', help='Version identifier')
    deploy_parser.add_argument('--commit', help='Commit hash')
    deploy_parser.add_argument('--desc', help='Deployment description')
    deploy_parser.set_defaults(func=cmd_deploy)
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze and detect regressions')
    analyze_parser.add_argument('--threshold', type=float, default=15, help='Regression threshold (%)')
    analyze_parser.add_argument('--hours', type=float, default=1, help='Recent period to check (hours)')
    analyze_parser.add_argument('--baseline', type=float, default=6, help='Baseline period (hours)')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show overall status')
    status_parser.set_defaults(func=cmd_status)
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show recent metrics')
    metrics_parser.add_argument('--count', type=int, default=10, help='Number of metrics to show')
    metrics_parser.set_defaults(func=cmd_metrics)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database
    init_database()
    
    # Run the command
    args.func(args)

if __name__ == '__main__':
    main()
