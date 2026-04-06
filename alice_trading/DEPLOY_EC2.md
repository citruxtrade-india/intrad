# EC2 DEPLOYMENT GUIDE - ANTI-GRAVITY

Follow these steps to deploy the platform on an AWS EC2 instance (Ubuntu/Linux).

## 1. Instance Setup
* **Instance Type**: t3.medium or higher (recommended for agent processing).
* **Security Group**: Open **TCP Port 8001** (Inbound) for your IP or '0.0.0.0/0' (publicly accessible).

## 2. Server Preparation
Connect via SSH and run:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv -y
```

## 3. Clone and Install
```bash
git clone <your-repo-url>
cd alice_trading
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Environment Variables
Create a `.env` file and add your credentials:
```bash
nano .env
# Add:
# ALICEBLUE_API_KEY=your_key
# ALICEBLUE_USER_ID=your_id
# ALICEBLUE_TOTP_SECRET=your_totp
# OPENAI_API_KEY=your_openai_key
```

## 5. Run with PM2 (Background Persistence)
To keep the server running after you close SSH:
```bash
sudo npm install -g pm2
pm2 start "python3 server.py" --name "antigravity-trade"
pm2 save
pm2 startup
```

## 6. Access
Open your browser and navigate to: `http://<EC2-PUBLIC-IP>:8001`
