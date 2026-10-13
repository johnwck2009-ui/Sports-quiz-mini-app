# Sports Quiz Arena — Telegram Mini App

A mobile-first sports quiz with Football, Basketball, Tennis and Formula 1. Correct answers earn 10 coins.

## Run locally
1. Install Python 3.10+.
2. Run `pip install -r requirements.txt`.
3. Run `python app.py`.
4. Open `http://127.0.0.1:10000`.

The app can be previewed in browser demo mode. To enable Telegram user verification, set the `BOT_TOKEN` environment variable to your BotFather bot token.

## Deploy to Render
1. Push this repository to GitHub.
2. In Render, create a new Blueprint and select this repository; Render reads `render.yaml`.
3. In the Render service's Environment settings, add `BOT_TOKEN` with the token from BotFather.
4. Deploy and copy the public HTTPS service URL.

## Connect to Telegram
1. Open @BotFather in Telegram and select/create your bot.
2. Use `/setmenubutton` (or the Mini App settings available in BotFather) to configure the app URL, or use `/newapp` to create a Telegram Mini App if offered for your bot.
3. Set the Web App URL to the Render HTTPS URL.
4. Open the bot and launch the app from its menu button.

## Important prototype notes
- This first version keeps coin balances and quiz sessions in server memory. They reset when the service restarts or redeploys and are not shared across multiple server instances.
- Before public launch, use a persistent database such as Supabase/Postgres for balances, user records, and quiz history, and add rate limits and anti-abuse protections.
- Keep the BotFather token private. Only store it as a Render environment variable; never paste it into frontend code or commit it to GitHub.
- With `BOT_TOKEN` configured, the backend validates Telegram Web App init data and rejects invalid/expired data. Without it, the app uses browser demo mode.
