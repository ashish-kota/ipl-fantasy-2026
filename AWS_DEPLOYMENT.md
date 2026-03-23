# AWS Deployment Guide — IPL Fantasy 2026

This guide covers deploying the Streamlit app on AWS using an **EC2 instance** (simplest approach for ~150 users).

---

## Option A: EC2 (Recommended for v1)

### 1. Launch an EC2 Instance

1. Go to **AWS Console → EC2 → Launch Instance**
2. Choose **Ubuntu Server 22.04 LTS (Free Tier eligible)**
3. Instance type: **t3.small** (2 vCPU, 2 GB RAM) — handles 150 concurrent users comfortably
4. Storage: **20 GB gp3**
5. Security Group — add these inbound rules:

| Type       | Protocol | Port | Source    |
|------------|----------|------|-----------|
| SSH        | TCP      | 22   | Your IP   |
| Custom TCP | TCP      | 8501 | 0.0.0.0/0 |
| HTTP       | TCP      | 80   | 0.0.0.0/0 |
| HTTPS      | TCP      | 443  | 0.0.0.0/0 |

6. Create or select a **Key Pair** (.pem file) and download it.

---

### 2. Connect to the Instance

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

---

### 3. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx

# Clone your repo (or upload files via scp)
git clone https://github.com/ashish-kota/ipl-fantasy-2026.git
cd ipl-fantasy-2026

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

---

### 4. Upload Your Files (if not using git)

From your **local machine**:
```bash
scp -i your-key.pem -r ./ipl-fantasy-2026 ubuntu@<EC2_PUBLIC_IP>:~/
```

---

### 5. Run the App (Quick Test)

```bash
cd ~/ipl-fantasy-2026
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Visit: `http://<EC2_PUBLIC_IP>:8501`

---

### 6. Run as a Background Service (systemd)

Create a service file so the app restarts automatically:

```bash
sudo nano /etc/systemd/system/ipl-fantasy.service
```

Paste this content:
```ini
[Unit]
Description=IPL Fantasy 2026 Streamlit App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ipl-fantasy-2026
Environment="PATH=/home/ubuntu/ipl-fantasy-2026/venv/bin"
ExecStart=/home/ubuntu/ipl-fantasy-2026/venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ipl-fantasy
sudo systemctl start ipl-fantasy
sudo systemctl status ipl-fantasy
```

---

### 7. Set Up Nginx Reverse Proxy (Port 80)

```bash
sudo nano /etc/nginx/sites-available/ipl-fantasy
```

Paste:
```nginx
server {
    listen 80;
    server_name <EC2_PUBLIC_IP>;  # or your domain name

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

Enable and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/ipl-fantasy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Now visit: `http://<EC2_PUBLIC_IP>` (no port needed)

---

### 8. Add HTTPS with Let's Encrypt (Optional but Recommended)

If you have a domain name pointed to your EC2 IP:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
sudo systemctl reload nginx
```

---

### 9. Persistent Data (SQLite)

The SQLite database is stored at `data/ipl_fantasy.db` on the EC2 instance.

**Backup the database regularly:**
```bash
# Manual backup
cp ~/ipl-fantasy-2026/data/ipl_fantasy.db ~/ipl_fantasy_backup_$(date +%Y%m%d).db

# Automated daily backup via cron
crontab -e
# Add this line:
0 2 * * * cp ~/ipl-fantasy-2026/data/ipl_fantasy.db ~/backups/ipl_fantasy_$(date +\%Y\%m\%d).db
```

---

## Option B: AWS Elastic Beanstalk (More Managed)

For a more managed deployment:

1. Install EB CLI: `pip install awsebcli`
2. Create `Procfile`:
   ```
   web: streamlit run app.py --server.port=8080 --server.address=0.0.0.0
   ```
3. Initialize and deploy:
   ```bash
   eb init -p python-3.11 ipl-fantasy-2026
   eb create ipl-fantasy-env
   eb open
   ```

---

## Option C: Streamlit Community Cloud (Free, Easiest)

For a completely free and zero-ops deployment (good for testing):

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Deploy

> ⚠️ Note: Streamlit Community Cloud resets the filesystem on each restart, so the SQLite DB will be lost. Use this only for demos. For production with 150 users, use EC2.

---

## Cost Estimate (EC2)

| Resource         | Type       | Monthly Cost (approx) |
|------------------|------------|----------------------|
| EC2 t3.small     | Compute    | ~$15–18              |
| EBS 20 GB gp3    | Storage    | ~$1.60               |
| Data Transfer    | Egress     | ~$1–3                |
| **Total**        |            | **~$18–23/month**    |

---

## Updating the App

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
cd ~/ipl-fantasy-2026
git pull origin main
sudo systemctl restart ipl-fantasy
```

---

## Updating the Match Schedule

**Option 1 — Via Admin Panel:**
Log in as admin → Admin Panel → Upload Schedule tab → upload new `matches.csv`

**Option 2 — Via SSH:**
```bash
scp -i your-key.pem data/matches.csv ubuntu@<EC2_PUBLIC_IP>:~/ipl-fantasy-2026/data/matches.csv
```

---

## Default Admin Credentials

| Username | Password  |
|----------|-----------|
| `admin`  | `admin123` |

> ⚠️ **Change the admin password immediately after first login!**
> Go to Dashboard → My Profile → Change Password
