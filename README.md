# Ledger — Family Sales Tracker

A mobile-first PWA for tracking product sales, inventory, and profit. Free to host and run.

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5000 — default passcode is `family2026` (change it, see below).

## Deploy to Render (free)

1. Push this folder to a GitHub repo.
2. On [render.com](https://render.com), create a new **Web Service** from that repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables (Render dashboard → Environment):
   - `SECRET_KEY` — any random long string
   - `FAMILY_PASSCODE` — the passcode you want your family to use
6. **Important — data persistence:** Render's free web services use an ephemeral filesystem, so the SQLite database (`tracker.db`) will reset on every restart/deploy. To keep data:
   - Add a free **Render Disk** (1 GB is plenty) mounted at e.g. `/var/data`, and set `DB_PATH=/var/data/tracker.db` as an env var — Render's paid disk tier isn't required for 1 GB on some plans, check current pricing since this changes.
   - Or swap SQLite for Render's **free managed Postgres** instance if you outgrow the disk approach (would need a small code change from `sqlite3` to `psycopg2`).

## Add to iPhone home screen

1. Open the deployed URL in **Safari** (not Chrome — Add to Home Screen is Safari-only on iOS).
2. Tap the **Share** icon → **Add to Home Screen**.
3. It'll launch full-screen with its own icon, no address bar.

Share the URL + passcode with your family members and have them do the same.

## Notes

- All family members share the same passcode and see the same data — there's no per-user login, by design, since it's meant to be simple.
- "Add a product" adds to existing stock if the name already exists, rather than creating a duplicate.
- CSV export is available from the bottom tab bar, or at `/export.csv`.
