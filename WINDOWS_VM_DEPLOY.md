# IPL Fantasy 2026 — Windows VM Deployment Guide

## Prerequisites
- Windows Server 2019/2022 or Windows 10/11
- Git installed
- Python 3.10+ installed
- Port 8501 open in firewall (or whichever port you choose)
- Access to GitHub repo

---

## Step 1: Install Python (if not already installed)

Download Python 3.11 from https://www.python.org/downloads/  
During install, **check "Add Python to PATH"**

Verify:
```powershell
python --version
```

---

## Step 2: Clone the Repository

```powershell
cd C:\
git clone https://github.com/ashish-kota/ipl-fantasy-2026.git
cd ipl-fantasy-2026
```

---

## Step 3: Create Virtual Environment & Install Dependencies

```powershell
python -m venv ipl
.\ipl\Scripts\activate
pip install -r requirements.txt
```

---

## Step 4: Create Secrets File

Create the file `.streamlit\secrets.toml` (this is gitignored — must be created manually on each VM):

```powershell
mkdir .streamlit
notepad .streamlit\secrets.toml
```

Paste this content and save:
```toml
QGENIE_API_KEY = "5bc2436a-5e59-448e-815d-58ddfac26ca3"
QGENIE_ENDPOINT = "https://qgenie-chat.qualcomm.com"
```

---

## Step 5: Run the App (Manual / Test)

```powershell
cd C:\ipl-fantasy-2026
.\ipl\Scripts\streamlit run app.py --server.port=8501
```

App will be available at:
- Local: http://localhost:8501
- Network: http://<VM-IP>:8501

---

## Step 6: Run as a Background Service (Recommended for Production)

### Option A: Run with NSSM (Non-Sucking Service Manager) — Recommended

1. Download NSSM from https://nssm.cc/download  
   Extract `nssm.exe` to `C:\nssm\`

2. Open PowerShell as Administrator:
```powershell
C:\nssm\nssm.exe install IPLFantasy
```

3. In the NSSM GUI:
   - **Path:** `C:\ipl-fantasy-2026\ipl\Scripts\streamlit.exe`
   - **Startup directory:** `C:\ipl-fantasy-2026`
   - **Arguments:** `run app.py --server.port=8501 --server.headless=true`

4. Click **Install service**, then:
```powershell
C:\nssm\nssm.exe start IPLFantasy
```

5. To stop/restart:
```powershell
C:\nssm\nssm.exe stop IPLFantasy
C:\nssm\nssm.exe restart IPLFantasy
```

---

### Option B: Run via Task Scheduler (Simpler)

1. Open **Task Scheduler** → Create Basic Task
2. Trigger: **At system startup**
3. Action: **Start a program**
   - Program: `C:\ipl-fantasy-2026\ipl\Scripts\streamlit.exe`
   - Arguments: `run app.py --server.port=8501 --server.headless=true`
   - Start in: `C:\ipl-fantasy-2026`

---

## Step 7: Open Firewall Port

```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="IPL Fantasy 8501" dir=in action=allow protocol=TCP localport=8501
```

---

## Step 8: Updating the App

When a new version is pushed to GitHub:

```powershell
cd C:\ipl-fantasy-2026
git pull origin main
# Restart the service
C:\nssm\nssm.exe restart IPLFantasy
```

Or if using Task Scheduler, just restart the task.

---

## Step 9: Database Location

The SQLite database is stored at:
```
C:\ipl-fantasy-2026\data\ipl_fantasy.db
```

**Back this up regularly** — it contains all users, predictions, and match results.

```powershell
# Simple backup command
copy C:\ipl-fantasy-2026\data\ipl_fantasy.db C:\backups\ipl_fantasy_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start app manually | `.\ipl\Scripts\streamlit run app.py --server.port=8501` |
| Start service | `C:\nssm\nssm.exe start IPLFantasy` |
| Stop service | `C:\nssm\nssm.exe stop IPLFantasy` |
| Update from GitHub | `git pull origin main` |
| View logs (NSSM) | Check `C:\ipl-fantasy-2026\nssm_logs\` |

---

## Admin Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@iplf.com | admin123 | Admin |

**Change the admin password after first login via the Profile page.**
