#!/usr/bin/env python3
import sys
import argparse
from datetime import datetime
from database import init_database, record_deployment, get_metrics_summary, get_connection
from collector import PerformanceCollector
from analyzer import RegressionAnalyzer
from slack_alerts import SlackAlerter, load_webhook_url

def cmd_collect(args):
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
    record_deployment(version=args.version, commit_hash=args.commit, description=args.desc)

def cmd_analyze(args):
    analyzer = RegressionAnalyzer(threshold_percent=args.threshold, baseline_window_hours=args.baseline)
    print(f"\n🔍 Analyzing regressions...")
    regressions = analyzer.check_all_endpoints(recent_hours=args.hours, verbose=True)
    if not regressions:
        print("\n✓ No regressions detected")

def cmd_analyze_slack(args):
    webhook_url = load_webhook_url()
    if not webhook_url:
        print("\n❌ Slack not configured. Run: python cli.py slack-setup")
        return
    analyzer = RegressionAnalyzer(threshold_percent=args.threshold, baseline_window_hours=args.baseline)
    print(f"\n🔍 Analyzing and sending to Slack...")
    regressions = analyzer.check_all_endpoints(recent_hours=args.hours, verbose=False)
    if regressions:
        print(f"🚨 Found {len(regressions)} regression(s), sending to Slack...\n")
        alerter = SlackAlerter(webhook_url)
        alerter.alert_multiple_regressions(regressions)
        for r in regressions:
            print(f"  • {r['endpoint']}: {r['degradation_percent']:.1f}% slower")
    else:
        print("✓ No regressions detected")

def cmd_slack_setup(args):
    print("\n" + "=" * 60)
    print("Slack Webhook Setup")
    print("=" * 60)
    print("""
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Performance Detector"
4. Select your workspace
5. Go to "Incoming Webhooks" → Enable it
6. "Add New Webhook to Workspace"
7. Pick a channel
8. Copy the Webhook URL
    """)
    webhook_url = input("Paste your Webhook URL: ").strip()
    if not webhook_url.startswith("https://hooks.slack.com"):
        print("❌ Invalid webhook URL")
        return
    alerter = SlackAlerter(webhook_url)
    print("\nTesting connection...")
    if alerter.test_connection():
        print("✓ Connection successful!")
        with open(".slack_config", "w") as f:
            f.write(webhook_url)
        print("✓ Webhook URL saved to .slack_config")
    else:
        print("❌ Connection failed.")

def cmd_slack_test(args):
    webhook_url = load_webhook_url()
    if not webhook_url:
        print("\n❌ Slack not configured. Run: python cli.py slack-setup")
        return
    alerter = SlackAlerter(webhook_url)
    print("\nTesting Slack connection...")
    if alerter.test_connection():
        print("✓ Slack is connected and ready!")
    else:
        print("❌ Connection failed.")

def cmd_status(args):
    print("\n📈 Performance Detector Status")
    print("=" * 50)
    summary = get_metrics_summary()
    print(f"\nMetrics Collected:    {summary['total_metrics']}")
    print(f"Average Response:     {summary['avg_response_time_ms']}ms")
    print(f"Deployments Recorded: {summary['total_deployments']}")
    print("\n" + "=" * 50)

def cmd_metrics(args):
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
    for timestamp, endpoint, response_time in results:
        short_endpoint = endpoint[-25:] if len(endpoint) > 25 else endpoint
        print(f"{timestamp:<25} {short_endpoint:<30} {response_time:>10.1f}")

def main():
    parser = argparse.ArgumentParser(description='Performance Regression Detector')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    collect_parser = subparsers.add_parser('collect', help='Collect metrics')
    collect_parser.add_argument('url', help='Endpoint URL')
    collect_parser.add_argument('--samples', type=int, default=5)
    collect_parser.add_argument('--interval', type=float, default=1.0)
    collect_parser.set_defaults(func=cmd_collect)
    
    deploy_parser = subparsers.add_parser('deploy', help='Record deployment')
    deploy_parser.add_argument('version', help='Version')
    deploy_parser.add_argument('--commit', help='Commit hash')
    deploy_parser.add_argument('--desc', help='Description')
    deploy_parser.set_defaults(func=cmd_deploy)
    
    analyze_parser = subparsers.add_parser('analyze', help='Detect regressions')
    analyze_parser.add_argument('--threshold', type=float, default=15)
    analyze_parser.add_argument('--hours', type=float, default=1)
    analyze_parser.add_argument('--baseline', type=float, default=6)
    analyze_parser.set_defaults(func=cmd_analyze)
    
    analyze_slack_parser = subparsers.add_parser('analyze-slack', help='Analyze & send Slack alerts')
    analyze_slack_parser.add_argument('--threshold', type=float, default=15)
    analyze_slack_parser.add_argument('--hours', type=float, default=1)
    analyze_slack_parser.add_argument('--baseline', type=float, default=6)
    analyze_slack_parser.set_defaults(func=cmd_analyze_slack)
    
    slack_setup_parser = subparsers.add_parser('slack-setup', help='Configure Slack')
    slack_setup_parser.set_defaults(func=cmd_slack_setup)
    
    slack_test_parser = subparsers.add_parser('slack-test', help='Test Slack')
    slack_test_parser.set_defaults(func=cmd_slack_test)
    
    status_parser = subparsers.add_parser('status', help='Show status')
    status_parser.set_defaults(func=cmd_status)
    
    metrics_parser = subparsers.add_parser('metrics', help='Show metrics')
    metrics_parser.add_argument('--count', type=int, default=10)
    metrics_parser.set_defaults(func=cmd_metrics)
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    init_database()
    args.func(args)

if __name__ == '__main__':
    main()
