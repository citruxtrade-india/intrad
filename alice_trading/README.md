# Anti-Gravity Institutional Trading Platform

![Auto Deploy to EC2](https://github.com/citruxtrade-india/intrad/actions/workflows/deploy.yml/badge.svg)

This is a production-grade algorithmic trading platform deployed on AWS EC2.

## 🚀 Deployment Status
The badge above shows the real-time status of your EC2 deployment. 
- **Green (Passing)**: Your server is updated and running the latest code.
- **Red (Failed)**: Something went wrong during the last push. Check the "Actions" tab.

## 🛠️ Infrastructure
- **Server**: FastAPI / Uvicorn
- **Host**: AWS EC2 (Ubuntu)
- **Process Manager**: Systemd (`trading-server.service`)
- **CI/CD**: GitHub Actions

## 📖 Quick Links
- **Dashboard**: [http://13.51.242.57:8002](http://13.51.242.57:8002)
- **Monitoring**: `journalctl -u trading-server -f`
