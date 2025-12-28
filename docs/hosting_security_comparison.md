# Hosting & Security Analysis: Safe & Automomous

## 1. Security: How to Protect API Keys
**Golden Rule**: **NEVER** commit your `.env` file or keys to GitHub.

### How it works on Cloud Hosting (Render/Vercel)
All reliable platforms use **"Environment Variables"** (Secrets Management).
1.  **Local**: Keys live in `.env` (ignored by Git).
2.  **Cloud Dashboard**: You paste the keys into a secure "Settings" panel on the host's website.
3.  **Deployment**: The host injects the keys into the bot's memory *only while it runs*. They are never visible in the code repository.
*   **Result**: Even if someone hacks your GitHub, they see `os.getenv("ALPACA_KEY")`, not the actual key.

---

## 2. Platform Showdown: Where should the Bot live?

The critical factor is **Persistence**. Your bot uses a **Scheduler** (APScheduler) that needs to "stay awake" 24/7 to wait for 9:30 AM.

| Feature | **Render** (Recommended) | **Vercel** | **Cloudflare** |
| :--- | :--- | :--- | :--- |
| **Architecture** | **Containers** (Persistent Server) | **Serverless** (Ephemeral) | **Edge Workers** (Ephemeral) |
| **Scheduler** | ✅ **Works Perfectly**. Runs 24/7. | ❌ **Fails**. Kills app after 10 seconds. | ❌ **Fails**. Event-driven only. |
| **Frontend (React)** | ✅ Good. | 🏆 **Excellent**. Fast & Free. | ✅ Good. |
| **Cost** | ~$7/mo (Backend) | Free (Frontend) | Free (Frontend) |
| **Complexity** | Low. (Upload Dockerfile -> Go). | High for Python backends. | High for Python. |

### Why not Vercel/Cloudflare for the Bot?
Vercel and Cloudflare are **"Serverless"**. They wake up when someone visits a website, do a task, and **go back to sleep immediately**.
*   If you put your Scheduler on Vercel, it will sleep after 10 seconds and **miss the 9:45 AM scan**.
*   Render allocates a tiny computer (Container) that stays ON.

---

## 3. The "Hybrid" Strategy (Best of Both Worlds)
To optimize cost and performance, we split the stack:

| Component | Host | Cost | Why? |
| :--- | :--- | :--- | :--- |
| **The Brain (Python Bot)** | **Render** | **$7/mo** | Needs to run 24/7 for specific time schedules. |
| **The Face (React Dashboard)** | **Vercel** | **$0** | Best-in-class UI hosting, free SSL, blazingly fast. |
| **Security** | **Env Vars** | **Included** | Keys securely managed on both platforms. |

## 4. Summary Recommendation
**Deployment Plan:**
1.  **Backend to Render**: Host the `executor_service` + `scheduler`. (Cost: $7/mo).
2.  **Frontend to Vercel**: Host the `web_dashboard`. (Cost: Free).
3.  **Security**: Manually paste Alpaca Keys into Render Dashboard's "Environment" tab.

This gives you a professional, secure, and fully autonomous setup for the price of a coffee.
