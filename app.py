import os
import hmac
import hashlib
import json
import time
import threading
import urllib.request
import urllib.error
from urllib.parse import parse_qsl
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PUBLIC_APP_URL = "https://sports-quiz-mini-app-production.up.railway.app"
QUESTION_COUNT = 5
COINS_PER_CORRECT = 10

# Prototype storage only: balances and quiz sessions reset when the server restarts.
balances = {}
sessions = {}

QUESTIONS = {
    "football": [
        {"q": "How many players from one team are on the pitch at kick-off in football?", "options": ["9", "10", "11", "12"], "answer": 2},
        {"q": "What is it called when a player scores three goals in one match?", "options": ["Hat-trick", "Triple play", "Treble kick", "Three-pointer"], "answer": 0},
        {"q": "How long is a standard football match, excluding added time?", "options": ["60 minutes", "80 minutes", "90 minutes", "100 minutes"], "answer": 2},
        {"q": "Which card means a player is sent off?", "options": ["Blue", "Yellow", "Red", "Green"], "answer": 2},
        {"q": "What is the main international tournament run by FIFA for men's national teams?", "options": ["The Euros", "The World Cup", "Copa del Rey", "The Champions League"], "answer": 1}
    ],
    "basketball": [
        {"q": "How many players from one team are on the court in standard basketball?", "options": ["4", "5", "6", "7"], "answer": 1},
        {"q": "How many points is a shot made from beyond the three-point line worth?", "options": ["1", "2", "3", "4"], "answer": 2},
        {"q": "Which league is widely known as the top professional basketball league in the United States?", "options": ["NFL", "MLB", "NBA", "NHL"], "answer": 2},
        {"q": "What is it called when a player bounces the ball while moving?", "options": ["Serving", "Dribbling", "Passing", "Blocking"], "answer": 1},
        {"q": "How many points is a successful free throw worth?", "options": ["1", "2", "3", "4"], "answer": 0}
    ],
    "tennis": [
        {"q": "What is the score called at 40–40 in tennis?", "options": ["Match point", "Deuce", "Love", "Break"], "answer": 1},
        {"q": "Which surface is traditionally associated with Wimbledon?", "options": ["Clay", "Hard court", "Grass", "Carpet"], "answer": 2},
        {"q": "What is a score of zero called in tennis?", "options": ["Nil", "Love", "Blank", "Duck"], "answer": 1},
        {"q": "What do players hit over the net?", "options": ["Puck", "Ball", "Shuttlecock", "Disc"], "answer": 1},
        {"q": "Which of these is a Grand Slam tennis tournament?", "options": ["Wimbledon", "Six Nations", "The Masters (golf)", "Super Bowl"], "answer": 0}
    ],
    "formula1": [
        {"q": "What flag signals the end of an F1 race?", "options": ["Red", "Yellow", "Chequered", "Blue"], "answer": 2},
        {"q": "What does a driver enter to change tyres during a race?", "options": ["Pit lane", "Grid box", "Parc fermé", "Paddock exit"], "answer": 0},
        {"q": "How many wheels does a Formula 1 car have?", "options": ["2", "3", "4", "6"], "answer": 2},
        {"q": "What is the starting order area called?", "options": ["The grid", "The crease", "The baseline", "The tee"], "answer": 0},
        {"q": "Which country hosts the famous Monaco Grand Prix?", "options": ["France", "Monaco", "Italy", "Spain"], "answer": 1}
    ]
}

def telegram_api(method, payload=None):
    """Call Telegram's Bot API without requiring an extra package."""
    if not BOT_TOKEN:
        return None
    body = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))

def send_start_message(chat_id):
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": "🏆 Welcome to Sports Quiz!\n\nChoose a sport, answer questions, and earn 10 coins for every correct answer.",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "⚽ Play Sports Quiz", "web_app": {"url": PUBLIC_APP_URL}}
            ]]
        }
    })

def telegram_polling_loop():
    """Simple single-process polling loop for the Railway prototype."""
    offset = None
    try:
        # Ensure long polling can be used if a webhook was previously configured.
        telegram_api("deleteWebhook", {"drop_pending_updates": False})
    except Exception as exc:
        print(f"Telegram bot setup warning: {exc}", flush=True)
    while True:
        try:
            payload = {"timeout": 25, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            result = telegram_api("getUpdates", payload) or {}
            for update in result.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                chat = message.get("chat", {})
                if chat.get("id") and text.split("@", 1)[0].strip() in ("/start", "/start "):
                    send_start_message(chat["id"])
        except Exception as exc:
            print(f"Telegram polling warning: {exc}", flush=True)
            time.sleep(5)

def start_telegram_bot():
    if BOT_TOKEN:
        thread = threading.Thread(target=telegram_polling_loop, daemon=True, name="telegram-bot-polling")
        thread.start()

def telegram_user_id(init_data):
    """Validate Telegram WebApp initData when BOT_TOKEN is configured."""
    if not BOT_TOKEN:
        # Demo mode for previewing the app before adding a bot token.
        return request.headers.get("X-Demo-User", "demo-user")
    if not init_data:
        return None
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        return None
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        return None
    try:
        auth_date = int(values.get("auth_date", "0"))
        if time.time() - auth_date > 86400:
            return None
        user = json.loads(values.get("user", "{}"))
        return str(user["id"])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None

def get_user():
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return telegram_user_id(init_data)

@app.get("/")
def home():
    return send_from_directory(".", "index.html")

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.get("/api/me")
def me():
    user_id = get_user()
    if user_id is None:
        return jsonify({"error": "Telegram verification failed. Open this app from Telegram."}), 401
    return jsonify({"coins": balances.get(user_id, 0), "verified": bool(BOT_TOKEN)})

@app.post("/api/start")
def start_quiz():
    user_id = get_user()
    if user_id is None:
        return jsonify({"error": "Telegram verification failed. Open this app from Telegram."}), 401
    data = request.get_json(silent=True) or {}
    sport = data.get("sport", "football")
    if sport not in QUESTIONS:
        return jsonify({"error": "Choose a supported sport."}), 400
    sessions[user_id] = {"sport": sport, "index": 0, "correct": 0, "answered": []}
    return jsonify({"question": public_question(sport, 0), "number": 1, "total": QUESTION_COUNT})

def public_question(sport, index):
    item = QUESTIONS[sport][index]
    return {"question": item["q"], "options": item["options"]}

@app.post("/api/answer")
def answer():
    user_id = get_user()
    if user_id is None:
        return jsonify({"error": "Telegram verification failed. Open this app from Telegram."}), 401
    session = sessions.get(user_id)
    if not session:
        return jsonify({"error": "Start a quiz first."}), 400
    if session["index"] >= QUESTION_COUNT:
        return jsonify({"error": "This quiz is already complete."}), 400
    data = request.get_json(silent=True) or {}
    choice = data.get("choice")
    if not isinstance(choice, int) or isinstance(choice, bool) or not 0 <= choice < 4:
        return jsonify({"error": "Select an answer."}), 400
    item = QUESTIONS[session["sport"]][session["index"]]
    correct = choice == item["answer"]
    earned = COINS_PER_CORRECT if correct else 0
    if correct:
        session["correct"] += 1
        balances[user_id] = balances.get(user_id, 0) + earned
    session["index"] += 1
    result = {
        "correct": correct,
        "correctAnswer": item["options"][item["answer"]],
        "earned": earned,
        "coins": balances.get(user_id, 0),
        "finished": session["index"] >= QUESTION_COUNT,
        "number": session["index"] + 1,
        "total": QUESTION_COUNT,
        "score": session["correct"]
    }
    if not result["finished"]:
        result["question"] = public_question(session["sport"], session["index"])
    return jsonify(result)

@app.get("/api/sports")
def sports():
    return jsonify([{"id": key, "name": name} for key, name in [
        ("football", "Football"), ("basketball", "Basketball"),
        ("tennis", "Tennis"), ("formula1", "Formula 1")
    ]])

# Railway's current Start Command uses one Gunicorn worker, which keeps this
# prototype's in-memory quiz data and polling loop in a single process.
start_telegram_bot()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
