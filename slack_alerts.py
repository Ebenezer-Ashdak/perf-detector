import requests
import json
from datetime import datetime

class SlackAlerter:
    """Send performance regression alerts to Slack."""
    
    def __init__(self, webhook_url):
        """Initialize with a Slack webhook URL."""
        self.webhook_url = webhook_url
    
    def test_connection(self):
        """Test that the webhook is working."""
        try:
            response = requests.post(
                self.webhook_url,
                json={"text": "✓ Performance Regression Detector is connected!"}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def alert_regression(self, regression):
        """Send a regression alert to Slack."""
        try:
            # Determine alert level based on degradation
            if regression['degradation_percent'] > 50:
                color = "danger"
                emoji = "🚨"
                severity = "CRITICAL"
            elif regression['degradation_percent'] > 30:
                color = "warning"
                emoji = "⚠️"
                severity = "HIGH"
            else:
                color = "good"
                emoji = "⚡"
                severity = "MEDIUM"
            
            # Extract endpoint name
            endpoint = regression['endpoint']
            endpoint_short = endpoint.split('//')[-1] if '//' in endpoint else endpoint
            
            # Build the message
            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"{emoji} {severity}: Performance Regression Detected",
                        "fields": [
                            {
                                "title": "Endpoint",
                                "value": f"`{endpoint_short}`",
                                "short": False
                            },
                            {
                                "title": "Baseline Response Time",
                                "value": f"{regression['baseline_ms']:.1f}ms",
                                "short": True
                            },
                            {
                                "title": "Current Response Time",
                                "value": f"{regression['current_ms']:.1f}ms",
                                "short": True
                            },
                            {
                                "title": "Degradation",
                                "value": f"+{regression['degradation_percent']:.1f}% slower",
                                "short": True
                            },
                            {
                                "title": "Samples",
                                "value": f"{regression['recent_samples']} recent, {regression['baseline_samples']} baseline",
                                "short": True
                            },
                        ],
                        "footer": "Performance Regression Detector",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Add deployment info if available
            if regression.get('likely_deployment'):
                dep = regression['likely_deployment']
                message['attachments'][0]['fields'].append({
                    "title": "Likely Culprit",
                    "value": f"v{dep['version']} ({dep['commit_hash'][:8]}...)",
                    "short": False
                })
            
            # Send to Slack
            response = requests.post(self.webhook_url, json=message)
            
            if response.status_code == 200:
                print(f"✓ Alert sent to Slack for {endpoint_short}")
                return True
            else:
                print(f"❌ Slack response {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending alert: {e}")
            return False
    
    def alert_multiple_regressions(self, regressions):
        """Send alerts for multiple regressions."""
        if not regressions:
            return
        
        print(f"\n📤 Sending {len(regressions)} regression alert(s) to Slack...")
        
        for regression in regressions:
            self.alert_regression(regression)

def load_webhook_url():
    """Load saved webhook URL from config file."""
    try:
        with open(".slack_config", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
