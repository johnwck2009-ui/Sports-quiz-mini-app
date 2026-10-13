import os
import hmac
import hashlib
import json
import time
import random
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
used_questions = {}

EASY_QUESTIONS = {
    "football": [
        {"q": "How many players from one team are on the pitch at kick-off in football?", "options": ["9", "10", "11", "12"], "answer": 2},
        {"q": "What is it called when a player scores three goals in one match?", "options": ["Hat-trick", "Triple play", "Treble kick", "Three-pointer"], "answer": 0},
        {"q": "How long is a standard football match, excluding added time?", "options": ["60 minutes", "80 minutes", "90 minutes", "100 minutes"], "answer": 2},
        {"q": "Which card means a player is sent off?", "options": ["Blue", "Yellow", "Red", "Green"], "answer": 2},
        {"q": "What is the main international tournament run by FIFA for men's national teams?", "options": ["The Euros", "The World Cup", "Copa del Rey", "The Champions League"], "answer": 1}
    ,
        {"q": "What is the name of the area where the goalkeeper may handle the ball?", "options": ["Penalty area","Centre circle","Technical area","Corner arc"], "answer": 0},
        {"q": "Which body is responsible for maintaining the Laws of the Game?", "options": ["FIFA only","IFAB","UEFA","IOC"], "answer": 1},
        {"q": "What is awarded when the whole ball crosses the goal line last touched by a defender, without a goal being scored?", "options": ["Throw-in","Goal kick","Corner kick","Indirect free kick"], "answer": 2},
        {"q": "How long is extra time in a standard knockout football match?", "options": ["15 minutes total","20 minutes total","30 minutes total","45 minutes total"], "answer": 2},
        {"q": "Which part of the body may not normally be used deliberately to play the ball by an outfield player?", "options": ["Head","Chest","Hand or arm","Foot"], "answer": 2}
    ],
    "basketball": [
        {"q": "How many players from one team are on the court in standard basketball?", "options": ["4", "5", "6", "7"], "answer": 1},
        {"q": "How many points is a shot made from beyond the three-point line worth?", "options": ["1", "2", "3", "4"], "answer": 2},
        {"q": "Which league is widely known as the top professional basketball league in the United States?", "options": ["NFL", "MLB", "NBA", "NHL"], "answer": 2},
        {"q": "What is it called when a player bounces the ball while moving?", "options": ["Serving", "Dribbling", "Passing", "Blocking"], "answer": 1},
        {"q": "How many points is a successful free throw worth?", "options": ["1", "2", "3", "4"], "answer": 0}
    ,
        {"q": "How high is a regulation basketball hoop above the floor?", "options": ["8 feet","9 feet","10 feet","12 feet"], "answer": 2},
        {"q": "What is a basket plus a foul on the shooter commonly called?", "options": ["Alley-oop","And-one","Fast break","Put-back"], "answer": 1},
        {"q": "How many points is a field goal made inside the three-point line worth?", "options": ["1","2","3","4"], "answer": 1},
        {"q": "What is it called when a player grabs a missed shot?", "options": ["Rebound","Assist","Turnover","Screen"], "answer": 0},
        {"q": "How many periods are played in a standard NBA game?", "options": ["2","3","4","5"], "answer": 2}
    ],
    "tennis": [
        {"q": "What is the score called at 40–40 in tennis?", "options": ["Match point", "Deuce", "Love", "Break"], "answer": 1},
        {"q": "Which surface is traditionally associated with Wimbledon?", "options": ["Clay", "Hard court", "Grass", "Carpet"], "answer": 2},
        {"q": "What is a score of zero called in tennis?", "options": ["Nil", "Love", "Blank", "Duck"], "answer": 1},
        {"q": "What do players hit over the net?", "options": ["Puck", "Ball", "Shuttlecock", "Disc"], "answer": 1},
        {"q": "Which of these is a Grand Slam tennis tournament?", "options": ["Wimbledon", "Six Nations", "The Masters (golf)", "Super Bowl"], "answer": 0}
    ,
        {"q": "What is the name of the shot that starts a point?", "options": ["Serve","Volley","Lob","Smash"], "answer": 0},
        {"q": "Which Grand Slam is played in New York?", "options": ["Australian Open","French Open","Wimbledon","US Open"], "answer": 3},
        {"q": "What is a shot that lands just over the net with little pace called?", "options": ["Drop shot","Ace","Drive serve","Overhead"], "answer": 0},
        {"q": "What score comes immediately before 40 in a standard tennis game?", "options": ["15","20","30","Love"], "answer": 2},
        {"q": "What is the strip between the singles and doubles sidelines called?", "options": ["Service box","Alley","Baseline","Centre mark"], "answer": 1}
    ],
    "formula1": [
        {"q": "What flag signals the end of an F1 race?", "options": ["Red", "Yellow", "Chequered", "Blue"], "answer": 2},
        {"q": "What does a driver enter to change tyres during a race?", "options": ["Pit lane", "Grid box", "Parc fermé", "Paddock exit"], "answer": 0},
        {"q": "How many wheels does a Formula 1 car have?", "options": ["2", "3", "4", "6"], "answer": 2},
        {"q": "What is the starting order area called?", "options": ["The grid", "The crease", "The baseline", "The tee"], "answer": 0},
        {"q": "Which country hosts the famous Monaco Grand Prix?", "options": ["France", "Monaco", "Italy", "Spain"], "answer": 1}
    ,
        {"q": "What does a red flag mean during an F1 session?", "options": ["Session stopped or suspended","Last lap","Pit lane open","Fastest lap recorded"], "answer": 0},
        {"q": "What is the area where F1 teams work on their cars during a race weekend called?", "options": ["Pit garage","Start box","Service circle","Parc lane"], "answer": 0},
        {"q": "What does a yellow flag usually warn drivers about?", "options": ["A hazard on track","The end of the race","A new lap record","A mandatory pit stop"], "answer": 0},
        {"q": "What is the person who drives a Formula 1 car called?", "options": ["Rider","Pilot","Driver","Navigator"], "answer": 2},
        {"q": "What is a pit stop commonly used for during a race?", "options": ["Changing tyres or making repairs","Adding fuel in modern races","Changing the circuit","Restarting the timing system"], "answer": 0}
    ]
}

# Each difficulty has its own questions. Rewards are chosen on the server.
QUESTIONS = {
    "easy": EASY_QUESTIONS,
    "medium": {
        "football": [
            {"q": "Which country won UEFA Euro 2020, played in 2021?", "options": ["England", "Italy", "Spain", "Portugal"], "answer": 1},
            {"q": "What is the term for three consecutive goals by one team without the opponent scoring between them?", "options": ["Clean sweep", "Perfect hat-trick", "Brace", "Shutout"], "answer": 1},
            {"q": "How far is the penalty spot from the goal line?", "options": ["9 yards", "10 yards", "12 yards", "15 yards"], "answer": 2},
            {"q": "Which club plays its home matches at Anfield?", "options": ["Everton", "Liverpool", "Manchester City", "Chelsea"], "answer": 1},
            {"q": "How many teams compete in the group stage of the men's FIFA World Cup from 2026 onward?", "options": ["32", "36", "40", "48"], "answer": 3}
        ,
        {"q": "Which nation won the 2010 FIFA World Cup?", "options": ["Germany","Spain","Netherlands","Brazil"], "answer": 1},
        {"q": "Which club is nicknamed the Gunners?", "options": ["Arsenal","Liverpool","Chelsea","Tottenham Hotspur"], "answer": 0},
        {"q": "What award is presented to the top scorer at a FIFA World Cup?", "options": ["Golden Boot","Golden Glove","Golden Ball","Fair Play Award"], "answer": 0},
        {"q": "How many points does a team usually earn for a league win?", "options": ["1","2","3","4"], "answer": 2},
        {"q": "Which country won the 2014 FIFA World Cup?", "options": ["Argentina","Brazil","Germany","France"], "answer": 2}
    ],
        "basketball": [
            {"q": "How long is an NBA quarter?", "options": ["10 minutes", "12 minutes", "15 minutes", "20 minutes"], "answer": 1},
            {"q": "How many personal fouls disqualify a player in an NBA game?", "options": ["4", "5", "6", "7"], "answer": 2},
            {"q": "What is a triple-double?", "options": ["Three made three-pointers", "Double digits in three statistical categories", "Three consecutive baskets", "A score tied three times"], "answer": 1},
            {"q": "Which position typically brings the ball up the court and directs the offense?", "options": ["Center", "Point guard", "Power forward", "Small forward"], "answer": 1},
            {"q": "How many seconds does an NBA team normally have to attempt a shot?", "options": ["14", "20", "24", "30"], "answer": 2}
        ,
        {"q": "Which NBA team plays its home games at Madison Square Garden?", "options": ["Brooklyn Nets","New York Knicks","Boston Celtics","Chicago Bulls"], "answer": 1},
        {"q": "What is a shot made close to the basket, often off the backboard, called?", "options": ["Layup","Free throw","Hook pass","Jump ball"], "answer": 0},
        {"q": "How many points is a field goal made inside the three-point line worth?", "options": ["1","2","3","5"], "answer": 1},
        {"q": "What violation occurs when a player takes too many steps without dribbling?", "options": ["Traveling","Goaltending","Charging","Backcourt"], "answer": 0},
        {"q": "What is a pass that directly leads to a made basket called?", "options": ["Rebound","Assist","Steal","Block"], "answer": 1}
    ],
        "tennis": [
            {"q": "In a standard tiebreak, what is the usual minimum points needed to win with a two-point lead?", "options": ["5", "6", "7", "10"], "answer": 2},
            {"q": "Which Grand Slam tournament is played on clay?", "options": ["Australian Open", "French Open", "Wimbledon", "US Open"], "answer": 1},
            {"q": "What is a serve called when the receiver cannot touch it?", "options": ["Let", "Ace", "Volley", "Lob"], "answer": 1},
            {"q": "In doubles, how many players are on court in total?", "options": ["2", "3", "4", "6"], "answer": 2},
            {"q": "What does 'break serve' mean?", "options": ["Win a game while receiving", "Take a medical timeout", "Win a tiebreak", "Change ends"], "answer": 0}
        ,
        {"q": "Which player won 23 Grand Slam singles titles in women's tennis?", "options": ["Serena Williams","Steffi Graf","Martina Navratilova","Chris Evert"], "answer": 0},
        {"q": "Which Grand Slam is traditionally played on grass?", "options": ["Australian Open","French Open","Wimbledon","US Open"], "answer": 2},
        {"q": "What is the line at the back of each side of a tennis court called?", "options": ["Baseline","Service line","Sideline","Centre mark"], "answer": 0},
        {"q": "What is a serve that lands outside the correct service box called?", "options": ["Fault","Ace","Let","Volley"], "answer": 0},
        {"q": "What is a shot hit high over an opponent toward the back of the court called?", "options": ["Lob","Volley","Slice serve","Drop shot"], "answer": 0}
    ],
        "formula1": [
            {"q": "What does DRS help a driver do?", "options": ["Save fuel in the pit lane", "Reduce aerodynamic drag to aid overtaking", "Warm the tyres", "Communicate with race control"], "answer": 1},
            {"q": "What colour flag is commonly used to warn a driver of danger ahead?", "options": ["Blue", "Yellow", "Green", "White"], "answer": 1},
            {"q": "What is a formation lap mainly used for before a race start?", "options": ["Awarding points", "Preparing tyres and checking the car", "Changing the grid order freely", "Refuelling every car"], "answer": 1},
            {"q": "Which tyre compound is generally marked with a white sidewall in dry F1 races?", "options": ["Soft", "Medium", "Hard", "Intermediate"], "answer": 2},
            {"q": "What is parc fermé?", "options": ["A restricted area where cars are subject to rules and checks", "The driver parade", "The pit crew garage only", "The post-race podium"], "answer": 0}
        ,
        {"q": "Which circuit hosts the British Grand Prix?", "options": ["Silverstone","Monza","Monaco","Interlagos"], "answer": 0},
        {"q": "What is the halo on an F1 car designed primarily to do?", "options": ["Protect the driver's head","Reduce tyre wear","Improve radio reception","Cool the brakes"], "answer": 0},
        {"q": "Which flag signals the end of an F1 race?", "options": ["Green","Blue","Chequered","Yellow"], "answer": 2},
        {"q": "What does DRS stand for?", "options": ["Drag Reduction System","Driver Recovery Setting","Downforce Regulation Setup","Dynamic Racing Speed"], "answer": 0},
        {"q": "What is the term for a driver's fastest lap in a race?", "options": ["Fastest lap","Pole lap","Formation lap","Out lap"], "answer": 0}
    ]
    },
    "hard": {
        "football": [
            {"q": "Which nation won the first FIFA World Cup in 1930?", "options": ["Brazil", "Italy", "Uruguay", "Argentina"], "answer": 2},
            {"q": "Which club won the first edition of the European Cup in 1956?", "options": ["Real Madrid", "AC Milan", "Benfica", "Barcelona"], "answer": 0},
            {"q": "Under the standard Laws of the Game, what is the minimum number of players a team must have to continue a match?", "options": ["6", "7", "8", "9"], "answer": 1},
            {"q": "Which country hosted the 1998 FIFA World Cup?", "options": ["Germany", "Spain", "France", "Mexico"], "answer": 2},
            {"q": "What is the name of the annual award traditionally presented to the world's best men's football player by France Football?", "options": ["The Golden Boot", "The Ballon d'Or", "The Golden Glove", "The Puskás Award"], "answer": 1}
        ,
        {"q": "Which club won the 2019 UEFA Champions League final?", "options": ["Liverpool","Tottenham Hotspur","Real Madrid","Barcelona"], "answer": 0},
        {"q": "Which country won UEFA Euro 2016?", "options": ["France","Portugal","Germany","Italy"], "answer": 1},
        {"q": "Which country won the 2022 FIFA World Cup?", "options": ["France","Argentina","Croatia","Brazil"], "answer": 1},
        {"q": "Which club plays its home matches at the Santiago Bernabéu?", "options": ["Atlético Madrid","Real Madrid","Sevilla","Valencia"], "answer": 1},
        {"q": "What is the name of the continental competition for national teams in South America?", "options": ["Copa América","Gold Cup","Africa Cup of Nations","Asian Cup"], "answer": 0}
    ],
        "basketball": [
            {"q": "How far is the NBA three-point line at the top of the arc?", "options": ["21 ft 9 in", "22 ft", "23 ft 9 in", "25 ft"], "answer": 2},
            {"q": "Which team drafted Kobe Bryant before trading him to the Los Angeles Lakers in 1996?", "options": ["Charlotte Hornets", "Philadelphia 76ers", "New Jersey Nets", "Boston Celtics"], "answer": 0},
            {"q": "How many seconds does a player have to inbound the ball in the NBA?", "options": ["3", "5", "8", "10"], "answer": 1},
            {"q": "Which statistic records a player's pass directly leading to a made basket?", "options": ["Rebound", "Assist", "Steal", "Block"], "answer": 1},
            {"q": "What violation occurs when an offensive player stays in the key too long under NBA rules?", "options": ["Backcourt violation", "Three-second violation", "Double dribble", "Traveling"], "answer": 1}
        ,
        {"q": "Which team won the first NBA championship in 1947?", "options": ["Boston Celtics","Philadelphia Warriors","Chicago Stags","Minneapolis Lakers"], "answer": 1},
        {"q": "Which player is known as 'The Greek Freak'?", "options": ["Luka Dončić","Giannis Antetokounmpo","Nikola Jokić","Joel Embiid"], "answer": 1},
        {"q": "How many points are awarded for a made free throw?", "options": ["1","2","3","4"], "answer": 0},
        {"q": "Which team drafted Kobe Bryant before trading him to the Lakers?", "options": ["Charlotte Hornets","Philadelphia 76ers","New Jersey Nets","Boston Celtics"], "answer": 0},
        {"q": "What is the violation called when a player dribbles, stops, then dribbles again?", "options": ["Traveling","Double dribble","Goaltending","Backcourt"], "answer": 1}
    ],
        "tennis": [
            {"q": "Which player completed the calendar-year Grand Slam in men's singles in 1969?", "options": ["Rod Laver", "Ken Rosewall", "Roy Emerson", "Björn Borg"], "answer": 0},
            {"q": "In tennis scoring, what does 'ad-in' mean after deuce?", "options": ["Receiver has advantage", "Server has advantage", "The point is replayed", "The game is over"], "answer": 1},
            {"q": "Which Grand Slam moved to a hard court in 1988 after being played on grass?", "options": ["French Open", "Wimbledon", "Australian Open", "US Open"], "answer": 2},
            {"q": "What is the maximum number of sets in a men's singles match at most Grand Slam events today?", "options": ["3", "4", "5", "7"], "answer": 2},
            {"q": "Which shot is hit before the ball bounces on the player's side?", "options": ["Lob", "Volley", "Drop shot", "Passing shot"], "answer": 1}
        ,
        {"q": "Which player completed the calendar-year Grand Slam in men's singles in 1969?", "options": ["Rod Laver","Ken Rosewall","Roy Emerson","Björn Borg"], "answer": 0},
        {"q": "Which Grand Slam moved to a hard court in 1988 after being played on grass?", "options": ["French Open","Wimbledon","Australian Open","US Open"], "answer": 2},
        {"q": "What is the score called when a player has one point to win the match?", "options": ["Match point","Set point","Break point","Game point"], "answer": 0},
        {"q": "Which surface is used at the French Open?", "options": ["Clay","Grass","Hard court","Carpet"], "answer": 0},
        {"q": "What is a shot hit before the ball bounces on the player's side called?", "options": ["Lob","Volley","Drop shot","Passing shot"], "answer": 1}
    ],
        "formula1": [
            {"q": "Who became Formula 1's first World Drivers' Champion in 1950?", "options": ["Juan Manuel Fangio", "Alberto Ascari", "Giuseppe Farina", "Stirling Moss"], "answer": 2},
            {"q": "Which circuit is known for its Eau Rouge–Raidillon sequence?", "options": ["Monza", "Spa-Francorchamps", "Silverstone", "Suzuka"], "answer": 1},
            {"q": "How many points does a driver receive for winning a modern F1 Grand Prix, excluding sprint points?", "options": ["20", "25", "26", "30"], "answer": 1},
            {"q": "What does a blue flag generally instruct a driver to do when being lapped?", "options": ["Stop immediately", "Allow a faster car to pass", "Return to the pits", "Change tyres"], "answer": 1},
            {"q": "Which team did Michael Schumacher win his first two World Drivers' Championships with?", "options": ["Ferrari", "Benetton", "Jordan", "Mercedes"], "answer": 1}
        ,
        {"q": "Who became Formula 1's first World Drivers' Champion in 1950?", "options": ["Juan Manuel Fangio","Alberto Ascari","Giuseppe Farina","Stirling Moss"], "answer": 2},
        {"q": "Which circuit is known for its Eau Rouge–Raidillon sequence?", "options": ["Monza","Spa-Francorchamps","Silverstone","Suzuka"], "answer": 1},
        {"q": "How many points does a driver receive for winning a modern F1 Grand Prix, excluding sprint points?", "options": ["20","25","26","30"], "answer": 1},
        {"q": "What does a blue flag generally instruct a driver to do when being lapped?", "options": ["Stop immediately","Allow a faster car to pass","Return to the pits","Change tyres"], "answer": 1},
        {"q": "Which team did Michael Schumacher win his first two World Drivers' Championships with?", "options": ["Ferrari","Benetton","Jordan","Mercedes"], "answer": 1}
    ]
    }
}

COINS_BY_DIFFICULTY = {"easy": 5, "medium": 15, "hard": 30}

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
        "text": "🏆 Welcome to Sports Quiz!\n\nChoose a sport and difficulty, answer questions, and earn up to 30 coins per correct answer on Hard mode.",
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
    difficulty = data.get("difficulty", "easy")
    if sport not in EASY_QUESTIONS:
        return jsonify({"error": "Choose a supported sport."}), 400
    if difficulty not in QUESTIONS:
        return jsonify({"error": "Choose a supported difficulty."}), 400
    bank = QUESTIONS[difficulty][sport]
    history_key = (user_id, sport, difficulty)
    used = used_questions.get(history_key, set())
    available = [item for item in bank if item["q"] not in used]
    # Reset only when fewer than a full round of unseen questions remain.
    if len(available) < QUESTION_COUNT:
        used = set()
        available = list(bank)
    selected_questions = random.sample(available, QUESTION_COUNT)
    used_questions[history_key] = used | {item["q"] for item in selected_questions}
    sessions[user_id] = {"sport": sport, "difficulty": difficulty, "index": 0, "correct": 0, "answered": [], "questions": selected_questions}
    return jsonify({"question": public_question(selected_questions[0]), "number": 1, "total": QUESTION_COUNT, "difficulty": difficulty, "coinsPerCorrect": COINS_BY_DIFFICULTY[difficulty]})

def public_question(item):
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
    item = session["questions"][session["index"]]
    correct = choice == item["answer"]
    earned = COINS_BY_DIFFICULTY[session["difficulty"]] if correct else 0
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
        result["question"] = public_question(session["questions"][session["index"]])
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
