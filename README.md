# Ledger — Sales & Inventory Tracker (Firebase edition)

A shared, passcode-protected sales & inventory tracker. Free tier throughout, no
credit card anywhere, and access is enforced by real authentication rather than
an open URL.

**Stack**

- Database: **Firestore** (Google Firebase's NoSQL database) — data is private by
  default; Firestore security rules reject any request that isn't signed in.
- Auth: **Firebase Authentication** — one shared account for the whole team. The
  passcode people type in the app _is_ that account's password.
- Frontend: a single static `index.html` (+ manifest/icons) hosted on **GitHub
  Pages** — installable to an iPhone home screen as a real app icon.

Total cost: **$0**, forever, at this scale. Firebase's free "Spark" plan never asks
for a credit card, and Firestore's free daily quota (50K reads / 20K writes) is far
more than a few people logging sales will ever use.

---

## Part 1 — Firebase project

1. Go to [console.firebase.google.com](https://console.firebase.google.com) and
   click **Add project**. Name it anything (e.g. "ledger"). You can decline Google
   Analytics — not needed.
2. In the left sidebar: **Build → Authentication → Get started**.
   - Under "Sign-in method", enable **Email/Password**.
   - Go to the **Users** tab → **Add user**.
   - Email: type exactly `team@ledger.local` (this is just a username, not a real
     inbox — nothing gets emailed there).
   - Password: this is your **team's shared passcode**. Pick something real.
   - Save.
3. In the left sidebar: **Build → Firestore Database → Create database**.
   - Choose a location close to your team, start in **production mode**.
4. Go to the **Rules** tab of Firestore and replace the contents with the
   `firestore.rules` file from this package, then click **Publish**.
5. Go to **Project settings** (gear icon, top left) → scroll to "Your apps" →
   click the **</>** (web) icon → register an app (any nickname) → **skip** the
   hosting step. It shows you a `firebaseConfig` object like:
   ```js
   const firebaseConfig = {
     apiKey: "AIza...",
     authDomain: "ledger-xxxxx.firebaseapp.com",
     projectId: "ledger-xxxxx",
     storageBucket: "ledger-xxxxx.appspot.com",
     messagingSenderId: "...",
     appId: "...",
   };
   ```
   Copy that whole `{ ... }` object — you'll paste it into the app once. (This
   config is not a secret — it just tells the app which Firebase project to talk
   to. Access is controlled by the passcode/auth step, not by hiding this.)

## Part 2 — Frontend (GitHub Pages)

1. Create a free GitHub account if you don't have one, and create a new **public**
   repository (e.g. `ledger`).
2. Upload `index.html`, `manifest.json`, `sw.js`, `icon-192.png`, and `icon-512.png`
   to the repo root (drag-and-drop on github.com via "Add file → Upload files", or
   git if you prefer). `firestore.rules` and this README don't need to be uploaded
   here — they're not part of the served app.
3. Repo **Settings → Pages** → Source: **Deploy from a branch**, branch `main`,
   folder `/ (root)`. Save.
4. GitHub gives you a URL like `https://yourname.github.io/ledger/`. Live in a
   minute or two — this is what your team opens going forward.

## Part 3 — First launch

1. Open the GitHub Pages URL.
2. Tap "Connection settings", paste in the `firebaseConfig` object from Part 1
   step 5, enter the passcode (the password you set for `team@ledger.local`), and
   tap **Open Ledger**.
3. Each device only needs to do this once — it's remembered after that.

### Install to iPhone home screen

Open the URL in **Safari** → Share icon → **Add to Home Screen**. Launches
full-screen with its own icon, no browser chrome.

Everyone on the team repeats Part 3 with the same URL + passcode — no individual
accounts to create.

---

## How it works day-to-day

- **Restock**: adding a product whose name already exists (matched case-
  insensitively) adds to its existing stock instead of creating a duplicate, and
  updates its cost-per-unit to whatever you just entered.
- **Sell**: pick a product, enter sale price and quantity. Oversells are blocked —
  checked in the app immediately, and re-checked inside a Firestore transaction at
  write time, so two people can't both sell the same last unit even if they tap
  "Record sale" at the same instant.
- **Dashboard & History** update live for everyone, in real time, without needing
  to refresh — Firestore pushes changes to every connected device.
- **CSV export**: one tap in History, opens in Excel/Numbers/Sheets.

## Why this is more secure than a spreadsheet-backed version

- Nothing is reachable without signing in — Firestore's rules reject unauthenticated
  requests outright, so there's no URL that exposes your data if someone finds it.
- Data lives in Google's managed database (encrypted at rest and in transit), not
  in a document whose sharing settings someone could accidentally loosen.
- Firestore transactions are stronger than a simple lock for concurrent writes —
  they retry automatically and guarantee the stock check and the deduction happen
  atomically.

## Notes & limits worth knowing

- The shared passcode is one identity for the whole team — fine for a small trusted
  group, but there's no per-person audit trail of _who_ recorded which sale. If you
  need that later, each person could get their own Firebase Auth login instead;
  ask and this can be extended.
- To change the passcode, go to Firebase console → Authentication → Users → the
  `team@ledger.local` user → reset password.
- To reset a device's saved connection, tap the ⚙ icon in the app header.
