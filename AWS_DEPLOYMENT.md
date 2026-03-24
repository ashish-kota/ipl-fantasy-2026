# IPL Fantasy 2026 — AWS Lightsail Deployment Guide

## Overview

- **Hosting:** AWS Lightsail ($10/mo plan)
- **OS:** Ubuntu 22.04 LTS
- **DB:** SQLite (file on server — persists across restarts)
- **Web server:** nginx (reverse proxy, port 80)
- **Process manager:** systemd (auto-restart on crash/reboot)
- **Estimated cost:** ~$20 for 2 months

---

## Step 1 — Create a Lightsail Instance

1. Go to [https://lightsail.aws.amazon.com](https://lightsail.aws.amazon.com)
2. Click **Create instance**
3. Select:
   - **Region:** Asia Pacific (Mumbai) `ap-south-1` — closest to India
   - **Platform:** Linux/Unix
   - **Blueprint:** Ubuntu 22.04 LTS
   - **Instance plan:** $10/month (1 vCPU, 1 GB RAM, 40 GB SSD, 2 TB transfer)
4. Give it a name: `ipl-fantasy-2026`
5. Click **Create instance**
6. Wait ~2 minutes for it to start

---

## Step 2 — Attach a Static IP

1. In Lightsail console → **Networking** tab → **Create static IP**
2. Attach it to your `ipl-fantasy-2026` instance
3. Note the static IP address (e.g. `13.235.xx.xx`) — this is your app URL

> Without a static IP, the IP changes every time the instance restarts.

---

## Step 3 — Open Firewall Ports

In Lightsail console → your instance → **Networking** tab → **Firewall**:

Add these rules if not already present:
| Protocol | Port | Purpose |
|---|---|---|
| TCP | 22 | SSH |
| TCP | 80 | HTTP (nginx) |
| TCP | 443 | HTTPS (optional, for SSL later) |

> Port 8501 does NOT need to be open — nginx handles routing internally.

---

## Step 4 — SSH into the Instance

**Option A — Browser SSH** (easiest):
- In Lightsail console → click the **SSH** button on your instance

**Option B — Terminal SSH**:
1. Download the SSH key from Lightsail console → Account → SSH keys
2. Run:
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_STATIC_IP
```

---

## Step 5 — Run the Deploy Script

Once SSH'd in, run:

```bash
curl -o deploy.sh https://raw.githubusercontent.com/ashish-kota/ipl-fantasy-2026/main/deploy.sh
bash deploy.sh
```

This script will automatically:
- Update system packages
- Install Python 3, pip, git, nginx
- Clone the GitHub repo
- Set up a Python virtual environment
- Install all dependencies
- Create a `systemd` service (auto-start, auto-restart)
- Configure nginx as a reverse proxy on port 80

**Expected time:** ~5–10 minutes

---

## Step 6 — Verify the App is Running

```bash
# Check service status
sudo systemctl status ipl-fantasy

# View live logs
sudo journalctl -u ipl-fantasy -f

# Check nginx
sudo systemctl status nginx
```

Open your browser: `http://YOUR_STATIC_IP`

You should see the IPL Fantasy 2026 login page.

**Admin login:**
- Email: `admin@iplf.com`
- Password: `admin123`
- ⚠️ **Change this password immediately after first login!**

---

## Step 7 — (Optional) Set Up a Custom Domain

If you have a domain (e.g. `iplf.yourcompany.com`):

1. Add a DNS A record pointing to your Lightsail static IP
2. Update nginx config:
```bash
sudo nano /etc/nginx/sites-available/ipl-fantasy
# Change: server_name _;
# To:     server_name iplf.yourcompany.com;
sudo systemctl restart nginx
```

---

## Updating the App (After Code Changes)

SSH into the server and run:

```bash
cd /home/ubuntu/ipl-fantasy-2026
git pull origin main
sudo systemctl restart ipl-fantasy
```

Or re-run the deploy script — it handles updates too:
```bash
bash deploy.sh
```

---

## Useful Commands

```bash
# Start / stop / restart the app
sudo systemctl start ipl-fantasy
sudo systemctl stop ipl-fantasy
sudo systemctl restart ipl-fantasy

# View live app logs
sudo journalctl -u ipl-fantasy -f

# View last 100 log lines
sudo journalctl -u ipl-fantasy -n 100

# Check nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Backup the SQLite database
cp /home/ubuntu/ipl-fantasy-2026/data/ipl_fantasy.db ~/ipl_fantasy_backup_$(date +%Y%m%d).db
```

---

## Backup Strategy

The SQLite DB is at `/home/ubuntu/ipl-fantasy-2026/data/ipl_fantasy.db`.

**Manual backup** (run periodically):
```bash
cp /home/ubuntu/ipl-fantasy-2026/data/ipl_fantasy.db ~/ipl_fantasy_backup_$(date +%Y%m%d).db
```

**Automated daily backup** (add to crontab):
```bash
crontab -e
# Add this line:
0 2 * * * cp /home/ubuntu/ipl-fantasy-2026/data/ipl_fantasy.db ~/backups/ipl_fantasy_$(date +\%Y\%m\%d).db
```

---

## Cost Summary

| Item | Monthly | 2 Months |
|---|---|---|
| Lightsail $10/mo plan | $10 | $20 |
| Static IP (free when attached) | $0 | $0 |
| **Total** | **$10** | **$20** |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| App not loading on port 80 | `sudo systemctl status nginx` — check for errors |
| App crashed | `sudo journalctl -u ipl-fantasy -n 50` — check logs |
| DB missing after restart | DB persists on EBS — check `/home/ubuntu/ipl-fantasy-2026/data/` |
| Can't SSH | Check Lightsail firewall has port 22 open |
| Slow first load | Normal — Python startup takes ~5s |
