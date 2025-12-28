# Render Deployment Guide: The Secure "Hybrid" Model

## 1. Safety Verification: "No Keys on Frontend"
**Confirmed**: Your system is already architected correctly for maximum security.
*   **Frontend**: `web_dashboard` has **ZERO** API keys. It is just a "Display Screen". It sends a request like "Run Scan" to the backend.
*   **Backend**: `executor_service` holds all the keys (Alpaca, Discord). It lives on the secure Render server.

This means even if someone inspects your website code, they see nothing but a URL pointing to the server.

---

## 2. Step 1: Deploy the Brain (Backend)
This is where the Scheduler and Trading Logic live.

1.  **Create Account**: Go to [render.com](https://render.com) and Sign Up.
2.  **New Web Service**: Click **New +** -> **Web Service**.
3.  **Source**: Connect your GitHub. Select this repository (`harmonic-eagle`).
4.  **Settings**:
    *   **Name**: `a-plus-trader-bot`
    *   **Runtime**: `Docker` (Render will find the `Dockerfile` we made).
    *   **Instance Type**: **Starter** ($7/mo). (Free tier puts bot to sleep, which kills the Scheduler. You need Starter for 24/7 autonomous uptime).
5.  **Environment Variables** (The Vault):
    *   Scroll down to "Environment Variables".
    *   Add the following (Copy from your local secrets):
        *   `APCA_API_KEY_ID`: `PK***************`
        *   `APCA_API_SECRET_KEY`: `****************`
        *   `APCA_API_BASE_URL`: `https://paper-api.alpaca.markets`
        *   `DISCORD_WEBHOOK_URL`: `https://discord.com/api/webhooks/...`
        *   `WEBHOOK_TOKEN`: `MakeUpASecurePasswordHere123`
        *   `TRADING_MODE`: `PAPER`
6.  **Deploy**: Click "Create Web Service".
    *   *Result*: Render gives you a URL: `https://a-plus-trader-bot.onrender.com`.

---

## 3. Step 2: Deploy the Face (Frontend)
This is your Command Center.

1.  **Dashboard**: Go to [vercel.com](https://vercel.com) (Easier than Render for React) or stick with Render "Static Site".
2.  **New Project**: Import `harmonic-eagle`.
3.  **Root Directory**: Click "Edit" and select `web_dashboard`.
4.  **Build Command**: `npm run build` (Default).
5.  **Output Directory**: `dist` (Default).
6.  **Environment Variables**:
    *   Add this **ONE** variable so the frontend knows where the Brain is:
    *   `VITE_API_BASE_URL`: `https://a-plus-trader-bot.onrender.com` (The URL from Step 1).
7.  **Deploy**.

---

## 4. How to Update
*   **Code Change**: When you push code to GitHub (`git push`), Render and Vercel automatically see it, rebuild, and redeploy. You don't do anything.
*   **Config Change**: If you want to change Risk %, you just edit the "Environment Variables" on Render's website and it restarts instantly.

**You are now operating a professional-grade, cloud-hosted Quantitative Trading System.**
