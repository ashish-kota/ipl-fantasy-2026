# IPL Fantasy 2026 — Roadmap & Feature Backlog

## ✅ v1 — Shipped
- Email-based login & registration
- Match schedule from CSV
- Dashboard: user stats, match schedule, my predictions, profile
- Predictions page: pick winner for upcoming matches before they start
- Leaderboard: rankings with accuracy chart
- Admin panel: enter match results, view users, view all predictions, upload schedule

---

## 🗂️ Backlog (Future Versions)

| # | Feature | Description | Priority |
|---|---|---|---|
| 1 | **Email domain restriction** | Registration only allowed for `@qti.qualcomm.com` email addresses | High |
| 2 | **Leaderboard — admin only** | Regular users cannot see the leaderboard; only admin can view rankings | Medium |
| 3 | **Admin CSV exports** | Admin can download leaderboard and all user predictions from DB as CSV | Medium |
| 4 | **Email notifications** | Auto or admin-triggered emails to remind users to submit predictions before a match starts | Medium |
| 5 | **AI prediction suggestions** | Suggest match winner based on team form, head-to-head history, venue stats, player availability | Low |
| 6 | **More TBD** | — | — |

---

## 💰 Hosting Cost Estimate (2 months, 150 users)

| Option | Cost | Notes |
|---|---|---|
| Streamlit Community Cloud | **$0** | Free, easiest, app URL is public but login-protected |
| AWS Lightsail $10/mo plan | **~$20** | 1 vCPU, 1GB RAM, fixed price, includes storage + transfer |
| AWS EC2 `t3.small` | **~$42** | More control, ~$21/mo |
| AWS EC2 `t3.micro` (free tier) | **$0** | Free for 12 months on new AWS accounts |

---

## 📝 Notes
- DB: SQLite (file-based, sufficient for 150 users + low concurrency)
- Upgrade to PostgreSQL (AWS RDS) if concurrent users grow significantly
- All match data loaded from `data/matches.csv` — admin can upload new schedule via Admin Panel
