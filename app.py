from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# --------------------------------------------------
# FILE PATHS
# --------------------------------------------------

DB = Path(__file__).with_name("welfareconnect.db")
SCHEME_FILE = Path(__file__).with_name("scheme_data.json")


# --------------------------------------------------
# LOAD SCHEMES FROM JSON
# --------------------------------------------------

with open(SCHEME_FILE, "r", encoding="utf-8") as f:
    SCHEMES = json.load(f)


# --------------------------------------------------
# SURVEY QUESTIONS (CONTINUOUS 1-10)
# --------------------------------------------------

SURVEY_QUESTIONS = [
    "How familiar are you with the eligibility criteria required for major government welfare schemes?",
    "How confident are you in identifying the exact official government portal versus unofficial intermediary websites?",
    "How easy is it for you to find an accurate checklist of required documents before beginning a scheme application?",
    "How confident are you in completing a scheme application process without needing paid agents or intermediaries?",
    "How frequently do you feel lack of clear information or complex procedures prevents eligible citizens from availing benefits?",
    "How important is it to have eligibility rules, benefits, and checklists consolidated into a single guidance platform?",
    "How helpful did you find Welfare Connect’s interactive features (search, audience filters, and document checklist)?",
    "How easy and clear was it to navigate the website and find scheme details?",
    "How useful did you find the step-by-step application instructions and direct official portal links?",
    "How likely are you to use Welfare Connect as a starting point to prepare documents and find official portals in the future?"
]


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS survey_responses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                gender TEXT NOT NULL,
                age_group TEXT NOT NULL,
                stage TEXT NOT NULL,
                q1 INTEGER NOT NULL,
                q2 INTEGER NOT NULL,
                q3 INTEGER NOT NULL,
                q4 INTEGER NOT NULL,
                q5 INTEGER NOT NULL,
                q6 INTEGER NOT NULL,
                q7 INTEGER NOT NULL,
                q8 INTEGER NOT NULL,
                q9 INTEGER NOT NULL,
                q10 INTEGER NOT NULL,
                score INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS scheme_views(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS visitor_sessions(
                visitor_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                visit_count INTEGER NOT NULL DEFAULT 0
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS activity_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                scheme_id INTEGER,
                query_text TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template(
        "index.html",
        survey_questions=SURVEY_QUESTIONS
    )


# --------------------------------------------------
# SCHEME API
# --------------------------------------------------

@app.get("/api/schemes")
def get_schemes():
    q = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "All")

    results = []

    for s in SCHEMES:
        # Build a broad search blob that covers all relevant text fields.
        # documents and steps are lists, so join them safely with a
        # fallback to an empty list when the field is missing or None.
        blob = " ".join([
            s.get("name", ""),
            s.get("category", ""),
            s.get("audience", ""),
            s.get("tags", ""),
            s.get("summary", ""),
            s.get("eligibility", ""),
            s.get("benefits", ""),
            " ".join(s.get("documents", []) or []),
            " ".join(s.get("steps", []) or []),
        ]).lower()

        # Apply keyword filter: skip if a keyword was given and it does
        # not appear anywhere in the combined blob.
        if q and q not in blob:
            continue

        # Apply strict category filter: skip if a specific category was
        # selected and this scheme belongs to a different one.
        if category != "All" and s.get("category") != category:
            continue

        results.append(s)

    return jsonify(results)


# --------------------------------------------------
# SINGLE SCHEME API
# --------------------------------------------------

@app.get("/api/scheme/<int:sid>")
def get_scheme(sid):
    s = next(
        (x for x in SCHEMES if x["id"] == sid),
        None
    )

    if not s:
        return jsonify({
            "error": "Scheme not found"
        }), 404

    with sqlite3.connect(DB) as con:
        con.execute(
            """
            INSERT INTO scheme_views(
                scheme_id,
                created_at
            )
            VALUES (?, ?)
            """,
            (
                sid,
                datetime.now().isoformat(timespec="seconds")
            )
        )

    return jsonify(s)


# --------------------------------------------------
# SAVE SURVEY RESPONSE
# --------------------------------------------------

@app.post("/api/survey")
def save_survey():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    status = str(data.get("status", "")).strip()
    gender = str(data.get("gender", "")).strip()
    age_group = str(data.get("age_group", "")).strip()
    stage = "general"
    answers = data.get("answers")

    # ----------------------------------------------
    # VALIDATE PARTICIPANT DETAILS
    # ----------------------------------------------

    if not name:
        return jsonify({
            "ok": False,
            "error": "Name is required."
        }), 400

    if not status:
        return jsonify({
            "ok": False,
            "error": "Current status is required."
        }), 400

    if not gender:
        return jsonify({
            "ok": False,
            "error": "Gender is required."
        }), 400

    if not age_group:
        return jsonify({
            "ok": False,
            "error": "Age group is required."
        }), 400

    # ----------------------------------------------
    # VALIDATE ANSWERS
    # ----------------------------------------------

    if not isinstance(answers, list):
        return jsonify({
            "ok": False,
            "error": "Invalid survey answers."
        }), 400

    if len(answers) != 10:
        return jsonify({
            "ok": False,
            "error": "Please answer all 10 questions."
        }), 400

    try:
        answers = [int(answer) for answer in answers]
    except (TypeError, ValueError):
        return jsonify({
            "ok": False,
            "error": "Invalid survey response."
        }), 400

    # Only values 1-5 are allowed
    if any(answer not in [1, 2, 3, 4, 5] for answer in answers):
        return jsonify({
            "ok": False,
            "error": "Invalid survey response."
        }), 400

    # ----------------------------------------------
    # CALCULATE SCORE
    # ----------------------------------------------

    total = sum(answers)
    score = round((total / 50) * 100)

    # ----------------------------------------------
    # SAVE TO DATABASE
    # ----------------------------------------------

    with sqlite3.connect(DB) as con:
        con.execute(
            """
            INSERT INTO survey_responses(
                name,
                status,
                gender,
                age_group,
                stage,
                q1,
                q2,
                q3,
                q4,
                q5,
                q6,
                q7,
                q8,
                q9,
                q10,
                score,
                created_at
            )
            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?
            )
            """,
            (
                name,
                status,
                gender,
                age_group,
                stage,
                *answers,
                score,
                datetime.now().isoformat(timespec="seconds")
            )
        )

    return jsonify({
        "ok": True,
        "score": score
    })


# --------------------------------------------------
# PUBLIC AGGREGATE STATISTICS
# --------------------------------------------------

@app.get("/api/stats")
def stats():
    with sqlite3.connect(DB) as con:
        total_responses = con.execute(
            "SELECT COUNT(*) FROM survey_responses"
        ).fetchone()[0]

        average_score = con.execute(
            "SELECT COALESCE(AVG(score), 0) FROM survey_responses"
        ).fetchone()[0]

        views = con.execute(
            "SELECT COUNT(*) FROM scheme_views"
        ).fetchone()[0]

        # Average score for each survey question, converted from 1-5 to 0-100.
        question_averages = []
        for q in range(1, 11):
            value = con.execute(
                f"SELECT COALESCE(AVG(q{q}), 0) FROM survey_responses"
            ).fetchone()[0]
            question_averages.append(round(value * 20, 1))

        # Distribution of all submitted 1-5 ratings across the ten questions.
        distribution = []
        for rating in range(1, 6):
            count = con.execute(
                """
                SELECT COUNT(*) FROM survey_responses
                WHERE q1=? OR q2=? OR q3=? OR q4=? OR q5=?
                   OR q6=? OR q7=? OR q8=? OR q9=? OR q10=?
                """,
                (rating,) * 10
            ).fetchone()[0]
            distribution.append({"rating": rating, "count": count})

        # Logical groups matching the current survey structure.
        group_ranges = {
            "awareness": [1, 2],
            "preparation": [3, 4, 5],
            "platform": [6, 7, 8, 9, 10]
        }
        category_averages = {}
        for name, questions in group_ranges.items():
            pieces = [f"AVG(q{q})" for q in questions]
            sql = "SELECT COALESCE((" + " + ".join(pieces) + f") / {len(questions)}, 0) FROM survey_responses"
            value = con.execute(sql).fetchone()[0]
            category_averages[name] = round(value * 20, 1)

        # Daily response counts for the latest seven calendar days.
        daily_rows = con.execute(
            """
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS responses
            FROM survey_responses
            WHERE date(created_at) >= date('now', '-6 days')
            GROUP BY day
            ORDER BY day ASC
            """
        ).fetchall()
        daily_lookup = {day: count for day, count in daily_rows}
        daily_responses = []
        for offset in range(6, -1, -1):
            day = con.execute(
                "SELECT date('now', ? || ' days')", (f"-{offset}",)
            ).fetchone()[0]
            daily_responses.append({"day": day, "responses": daily_lookup.get(day, 0)})

    return jsonify({
        "responses": total_responses,
        "average": round(average_score, 1),
        "views": views,
        "question_averages": question_averages,
        "rating_distribution": distribution,
        "category_averages": category_averages,
        "daily_responses": daily_responses
    })


# --------------------------------------------------
# ANONYMOUS WEBSITE ACTIVITY TRACKING
# --------------------------------------------------

@app.post("/api/track")
def track_activity():
    data = request.get_json(silent=True) or {}
    visitor_id = str(data.get("visitor_id", "")).strip()
    event_type = str(data.get("event_type", "")).strip()
    query_text = str(data.get("query", "")).strip()[:100]
    details = str(data.get("details", "")).strip()[:300]
    scheme_id = data.get("scheme_id")

    allowed = {
        "page_view",
        "scheme_view",
        "search",
        "filter",
        "official_link_click",
        "quiz_completed",
        "survey_submitted"
    }

    if not visitor_id or len(visitor_id) > 100:
        return jsonify({"ok": False, "error": "Invalid visitor ID."}), 400
    if event_type not in allowed:
        return jsonify({"ok": False, "error": "Invalid event type."}), 400

    try:
        scheme_id = int(scheme_id) if scheme_id is not None else None
    except (TypeError, ValueError):
        scheme_id = None

    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB) as con:
        exists = con.execute("SELECT 1 FROM visitor_sessions WHERE visitor_id = ?", (visitor_id,)).fetchone()
        if exists:
            con.execute(
                "UPDATE visitor_sessions SET last_seen=?, visit_count=visit_count+? WHERE visitor_id=?",
                (now, 1 if event_type == "page_view" else 0, visitor_id)
            )
        else:
            con.execute(
                "INSERT INTO visitor_sessions(visitor_id, first_seen, last_seen, visit_count) VALUES(?,?,?,?)",
                (visitor_id, now, now, 1 if event_type == "page_view" else 0)
            )
        con.execute(
            "INSERT INTO activity_events(visitor_id,event_type,scheme_id,query_text,details,created_at) VALUES(?,?,?,?,?,?)",
            (visitor_id, event_type, scheme_id, query_text or None, details or None, now)
        )
    return jsonify({"ok": True})


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "project": "Welfare Connect"})


# --------------------------------------------------
# CHATBOT — KNOWLEDGE-BASE ASSISTANT
# --------------------------------------------------

def _scheme_search(query, max_results=5):
    """
    Return up to max_results schemes ranked by relevance to query.
    Scoring: exact name match > partial name > category > audience >
             eligibility/benefits/summary > documents/steps.
    Returns list of (score, scheme) tuples — the score is kept so
    callers can check dominance.
    """
    import re as _re

    q = query.lower().strip()
    if not q:
        return []

    # Strip punctuation from query for matching
    q_clean = _re.sub(r"[^a-z0-9 ]", " ", q)
    scored = []
    tokens = [t for t in q_clean.split() if len(t) > 2]

    for s in SCHEMES:
        score = 0

        name_l       = s["name"].lower()
        name_clean   = _re.sub(r"[^a-z0-9 ]", " ", name_l)

        # Exact or near-exact name match
        if q_clean.strip() == name_clean.strip():
            score += 100
        elif q_clean.strip() in name_clean:
            score += 60
        else:
            # Partial token matches on name (use cleaned name)
            for t in tokens:
                if t in name_clean:
                    score += 15

        # Category / audience match
        cat_l = _re.sub(r"[^a-z0-9 ]", " ", s["category"].lower())
        aud_l = _re.sub(r"[^a-z0-9 ]", " ", s["audience"].lower())
        tags_l = _re.sub(r"[^a-z0-9 ]", " ", s.get("tags", "").lower())
        for t in tokens:
            if t in cat_l:
                score += 12
            if t in aud_l:
                score += 10
            if t in tags_l:
                score += 8

        # Summary / eligibility / benefits
        rich_blob = _re.sub(r"[^a-z0-9 ]", " ", " ".join([
            s.get("summary", ""),
            s.get("eligibility", ""),
            s.get("benefits", ""),
        ]).lower())
        for t in tokens:
            if t in rich_blob:
                score += 5

        # Documents / steps
        detail_blob = _re.sub(r"[^a-z0-9 ]", " ", " ".join(
            s.get("documents", []) + s.get("steps", [])
        ).lower())
        for t in tokens:
            if t in detail_blob:
                score += 2

        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:max_results]   # returns (score, scheme) tuples


# Intent keywords
_INTENT_DOCUMENT    = {"document", "documents", "doc", "docs", "papers",
                       "paperwork", "certificate", "certificates", "proof",
                       "required", "need", "needed", "bring", "submit"}
_INTENT_ELIGIBILITY = {"eligible", "eligibility", "qualify", "qualification",
                       "criteria", "who", "can", "allowed", "requirement",
                       "requirements", "age", "income", "limit"}
_INTENT_BENEFITS    = {"benefit", "benefits", "get", "receive", "amount",
                       "money", "pension", "loan", "subsidy", "grant",
                       "scholarship", "stipend", "pay", "payment"}
_INTENT_HOW_APPLY   = {"apply", "application", "register", "registration",
                       "process", "step", "steps", "procedure", "how",
                       "enroll", "enrolment", "start"}

_CAT_MAP = {
    "education":            "Education",
    "scholarship":          "Education",
    "study":                "Education",
    "student":              "Education",
    "school":               "Education",
    "college":              "Education",
    "skill":                "Skills & Employment",
    "skills":               "Skills & Employment",
    "employment":           "Skills & Employment",
    "job":                  "Skills & Employment",
    "jobs":                 "Skills & Employment",
    "training":             "Skills & Employment",
    "apprentice":           "Skills & Employment",
    "apprenticeship":       "Skills & Employment",
    "work":                 "Skills & Employment",
    "career":               "Skills & Employment",
    "business":             "Business & Livelihood",
    "livelihood":           "Business & Livelihood",
    "entrepreneur":         "Business & Livelihood",
    "enterprise":           "Business & Livelihood",
    "vendor":               "Business & Livelihood",
    "food":                 "Business & Livelihood",
    "pension":              "Pension & Social Security",
    "insurance":            "Pension & Social Security",
    "security":             "Pension & Social Security",
    "retirement":           "Pension & Social Security",
    "elderly":              "Pension & Social Security",
    "senior":               "Pension & Social Security",
    "old":                  "Pension & Social Security",
    "digital":              "Digital Services",
    "online":               "Digital Services",
    "language":             "Digital Services",
    "mobile":               "Digital Services",
    "sim":                  "Digital Services",
    "translate":            "Digital Services",
    "translation":          "Digital Services",
    "agriculture":          "Agriculture",
    "farmer":               "Agriculture",
    "farming":              "Agriculture",
    "kisan":                "Agriculture",
    "financial":            "Financial Inclusion",
    "bank":                 "Financial Inclusion",
    "banking":              "Financial Inclusion",
    "account":              "Financial Inclusion",
    "unbanked":             "Financial Inclusion",
}


def _detect_intent(tokens):
    t = set(tokens)
    if t & _INTENT_DOCUMENT:
        return "documents"
    if t & _INTENT_ELIGIBILITY:
        return "eligibility"
    if t & _INTENT_BENEFITS:
        return "benefits"
    if t & _INTENT_HOW_APPLY:
        return "apply"
    return "general"


def _detect_category(tokens):
    for t in tokens:
        if t in _CAT_MAP:
            return _CAT_MAP[t]
    return None


def _build_response(message, context=None):
    """
    Returns a dict:
      type: "scheme_detail" | "scheme_list" | "not_found" | "greeting" | "general"
      text: str
      schemes: list of scheme dicts (slim, safe for JSON)
      intent: str
      context: dict with last_scheme_id (for the frontend to preserve and send back)

    context (optional dict):
      last_scheme_id: int — ID of the last scheme the user was discussing
    """
    import re as _re

    raw = message.strip()
    q_lower = raw.lower()
    tokens = [t.strip("?!.,;:'\"()") for t in q_lower.split() if len(t.strip("?!.,;:'\"()")) > 1]
    token_set = set(tokens)

    # Resolve conversation context — last scheme the user discussed
    _ctx_scheme = None
    if context and isinstance(context, dict):
        _last_id = context.get("last_scheme_id")
        if _last_id:
            try:
                _last_id = int(_last_id)
                _ctx_scheme = next((s for s in SCHEMES if s["id"] == _last_id), None)
            except (TypeError, ValueError):
                pass

    # Helper: text-only response with no scheme cards
    def _plain(text, intent="general"):
        out_ctx = {}
        if _ctx_scheme:
            out_ctx["last_scheme_id"] = _ctx_scheme["id"]
        return {"type": "general", "text": text, "schemes": [], "intent": intent, "context": out_ctx}

    def _scheme_response(s, intent, intro_text):
        """Return a single-scheme detail response and persist its ID in context."""
        return {
            "type":    "scheme_detail",
            "text":    intro_text,
            "schemes": [s],
            "intent":  intent,
            "context": {"last_scheme_id": s["id"]}
        }

    def _list_response(schemes_list, intent, text):
        """Return a scheme list response; persist first scheme's ID in context."""
        ctx = {"last_scheme_id": schemes_list[0]["id"]} if schemes_list else {}
        return {"type": "scheme_list", "text": text, "schemes": schemes_list, "intent": intent, "context": ctx}

    # Derive unique categories from the loaded data (used in several handlers)
    _all_categories = sorted({s["category"] for s in SCHEMES})
    _cat_list_str   = "\n".join(f"• {c}" for c in _all_categories)

    # ------------------------------------------------------------------
    # 1. Greeting
    # ------------------------------------------------------------------
    greet_words = {"hi", "hello", "hey", "namaste", "hii", "helo",
                   "morning", "afternoon", "evening", "greetings"}
    if token_set & greet_words and len(tokens) <= 5:
        return {
            "type": "greeting",
            "text": (
                "Hello! I'm the WelfareConnect Assistant.\n\n"
                "I can help you:\n"
                "• Discover government welfare schemes\n"
                "• Understand eligibility, benefits and documents\n"
                "• Navigate the WelfareConnect website\n"
                "• Find the right official portal to apply\n\n"
                "Try asking: \"Show education schemes\", \"What documents do I need for PM-KISAN?\", "
                "or \"I want to start a business — what can I explore?\""
            ),
            "schemes": [],
            "intent": "greeting"
        }

    # ------------------------------------------------------------------
    # 2. Small talk — thank you / bye / okay / good
    # ------------------------------------------------------------------
    thanks_words = {"thank", "thanks", "thankyou", "thank-you", "ty"}
    bye_words    = {"bye", "goodbye", "see", "later", "cya", "farewell"}
    ack_words    = {"okay", "ok", "alright", "got", "noted", "great",
                    "cool", "nice", "good", "perfect", "understood"}

    if token_set & thanks_words and len(tokens) <= 5:
        return _plain(
            "You're welcome! If you have more questions about welfare schemes or the website, "
            "feel free to ask anytime.",
            "greeting"
        )
    if token_set & bye_words and len(tokens) <= 4:
        return _plain(
            "Goodbye! Visit WelfareConnect anytime to explore government welfare schemes. "
            "Good luck with your applications!",
            "greeting"
        )
    if token_set & ack_words and len(tokens) <= 3:
        return _plain(
            "Great! Let me know if you have any more questions about schemes or the website.",
            "greeting"
        )

    # ------------------------------------------------------------------
    # 3. What can you do / help / capabilities
    # ------------------------------------------------------------------
    capability_signals = {
        ("what", "can", "you"), ("what", "do", "you"), ("how", "can", "you"),
        ("your", "features"), ("what", "you", "do"),
    }
    is_capability = (
        "capabilities" in token_set or "capability" in token_set or
        ("help" in token_set and len(tokens) <= 3) or
        any(all(w in token_set for w in ph) for ph in capability_signals)
    )
    if is_capability:
        return _plain(
            "Here's what I can help you with:\n\n"
            "**Scheme discovery** — Ask about any scheme by name "
            "(e.g. \"Tell me about PM-KISAN\", \"What is MGNREGA?\").\n\n"
            "**Category browsing** — Ask for schemes by category "
            "(e.g. \"Show education schemes\", \"Pension schemes\").\n\n"
            "**Eligibility & benefits** — Ask what a scheme offers or who can apply "
            "(e.g. \"Who is eligible for Atal Pension Yojana?\").\n\n"
            "**Documents & application** — Ask what documents you need or how to apply "
            "(e.g. \"What documents do I need?\", \"How do I apply for PM Vishwakarma?\").\n\n"
            "**Navigation help** — Ask how to use any section of the WelfareConnect website.\n\n"
            "**Profile-based guidance** — Tell me about yourself and I'll point you in the right "
            "direction (e.g. \"I'm a student\", \"I want to start a business\").\n\n"
            "I only use information from the WelfareConnect database and website. "
            "For the actual application, I'll always direct you to the official government portal."
        )

    # ------------------------------------------------------------------
    # 4. About WelfareConnect
    # ------------------------------------------------------------------
    about_signals = {
        ("what", "is", "welfareconnect"), ("what", "is", "welfare", "connect"),
        ("about", "this", "website"), ("about", "this", "site"),
        ("what", "does", "this", "do"), ("what", "does", "this", "website"),
        ("what", "this", "website"), ("purpose", "website"),
        ("what", "is", "this", "website"), ("what", "is", "this", "site"),
        ("how", "can", "website", "help"), ("how", "can", "this", "help"),
        ("what", "can", "do", "here"), ("what", "can", "here"),
        ("about", "welfareconnect"),
    }
    about_words   = {"about", "purpose", "explain", "describe", "overview"}
    website_words = {"welfareconnect", "website", "site", "platform", "portal"}
    is_about = (
        any(all(w in token_set for w in ph) for ph in about_signals) or
        (website_words & token_set and about_words & token_set and len(tokens) <= 8)
    )
    if is_about:
        return _plain(
            "**WelfareConnect** is a digital welfare guide — an educational project that helps "
            "Indian citizens discover, understand, and prepare to apply for government welfare schemes.\n\n"
            "**What the website offers:**\n\n"
            "• **Find Schemes** — Search and filter government schemes by category or keyword. "
            "Each card shows a summary, eligibility guide, document checklist, and a link to the "
            "official portal.\n\n"
            "• **How It Works** — A simple four-step journey: Find → Understand → Prepare → Apply.\n\n"
            "• **Awareness Quiz** — Test your knowledge of welfare schemes in five quick questions.\n\n"
            "• **Awareness Survey** — A short assessment on welfare scheme awareness "
            "(responses feed the public dashboard).\n\n"
            "• **Dashboard** — Anonymous aggregate survey results and statistics.\n\n"
            "• **This Assistant** — Answers questions about schemes and how to use the website.\n\n"
            "WelfareConnect is an informational guide only. Actual applications must be completed "
            "through the official government portals linked inside each scheme."
        )

    # ------------------------------------------------------------------
    # 5. Website navigation / how to find / how to use
    # ------------------------------------------------------------------
    nav_signals = {
        ("find", "scheme"), ("find", "schemes"), ("search", "scheme"),
        ("search", "schemes"), ("how", "find"), ("where", "find"),
        ("how", "search"), ("how", "use"), ("navigate", "website"),
        ("view", "scheme"), ("view", "details"), ("full", "scheme"),
        ("how", "works"), ("finder", "work"), ("where", "search"),
        ("how", "navigate"), ("where", "schemes"),
    }
    nav_words  = {"navigate", "navigation", "section", "finder", "filter",
                  "browse", "search", "find", "look"}
    site_ref   = {"website", "site", "page", "section", "here", "welfareconnect", "it"}
    is_nav = (
        any(all(w in token_set for w in ph) for ph in nav_signals) or
        (nav_words & token_set and site_ref & token_set and len(tokens) <= 9
         and not token_set & {"scheme", "schemes"})   # pure nav question, not category search
    )
    if is_nav:
        return _plain(
            "Here's how to use the WelfareConnect website:\n\n"
            "**Finding a scheme**\n"
            "Click **\"Find Schemes\"** in the top navigation. "
            "Filter by **Category** (Education, Business, Pension, etc.) or type a keyword "
            "(e.g. \"student\", \"pension\", \"loan\"). Scheme cards appear instantly.\n\n"
            "**Viewing full scheme details**\n"
            "Click **\"View Full Guide →\"** on any card to see the full description, "
            "eligibility guide, benefits, document checklist, and step-by-step application guide.\n\n"
            "**Document checklist**\n"
            "Inside the full guide, tick off documents as you prepare them — "
            "the progress bar updates automatically.\n\n"
            "**Applying**\n"
            "Click **\"Open Official Portal ↗\"** to go directly to the government website "
            "for that scheme. The actual application is completed there.\n\n"
            "**Scheme Finder Wizard**\n"
            "Click **\"✨ Find My Schemes\"** to filter schemes by your profile "
            "(student, youth, family, vendor, etc.).\n\n"
            "You can also ask me: \"Show education schemes\" or \"Tell me about PM-KISAN\"."
        )

    # ------------------------------------------------------------------
    # 6. What categories are available
    # ------------------------------------------------------------------
    cat_q_signals = {
        ("what", "categories"), ("which", "categories"), ("list", "categories"),
        ("show", "categories"), ("available", "categories"),
        ("what", "types"), ("which", "types"), ("what", "kinds"),
        ("what", "category"), ("which", "category"),
    }
    is_cat_query = (
        any(all(w in token_set for w in ph) for ph in cat_q_signals) or
        ("categories" in token_set and len(tokens) <= 5) or
        ("category" in token_set
         and token_set & {"what", "which", "list", "show", "available"}
         and len(tokens) <= 6)
    )
    if is_cat_query:
        return _plain(
            f"WelfareConnect covers **{len(SCHEMES)} schemes** across "
            f"**{len(_all_categories)} categories**:\n\n"
            f"{_cat_list_str}\n\n"
            "Filter by category in the **Find Schemes** section, or ask me directly — "
            "for example: \"Show business schemes\" or \"Education schemes\"."
        )

    # ------------------------------------------------------------------
    # 7. Scheme-specific questions — documents, apply, benefits,
    #    eligibility for a NAMED scheme.
    #    These run BEFORE the generic doc/apply handlers (8 & 9) so that
    #    "What documents do I need for MUDRA?" goes to MUDRA's checklist,
    #    not the generic list.
    # ------------------------------------------------------------------

    # Build a fast lookup: cleaned name token → scheme
    # Also handle hyphenated abbreviations like "pm-kisan" → "pmkisan" and "kisan"
    def _find_named_scheme(q_str):
        """
        Return the best-matching scheme when the query contains a specific
        scheme name or widely-known abbreviation.  Strips common intent words
        before scoring so "What documents do I need for MUDRA?" scores MUDRA
        on its name, not on the word "documents" matching other schemes.
        Returns None if no clear single match is found above a threshold.
        """
        # Strip intent/question words — search on the remaining name tokens
        _strip_words = {
            "what", "which", "who", "how", "when", "where", "why",
            "does", "do", "did", "can", "could", "should", "would", "is",
            "are", "was", "were", "the", "for", "and", "of", "in", "to",
            "that", "this", "those", "these", "tell", "me", "about", "show",
            "find", "give", "get", "explain", "describe",
            "document", "documents", "docs", "papers", "paperwork",
            "certificate", "certificates", "proof", "needed", "required",
            "need", "bring", "checklist",
            "apply", "application", "register", "enroll", "steps",
            "process", "procedure", "step",
            "benefit", "benefits", "amount", "loan", "subsidy",
            "grant", "scholarship", "stipend", "money", "receive",
            "eligible", "eligibility", "qualify", "criteria",
            "requirement", "requirements", "age", "income", "limit",
        }
        import re as _re2
        _clean = _re2.sub(r"[^a-z0-9 ]", " ", q_str.lower())
        _name_tokens = [t for t in _clean.split() if len(t) > 2 and t not in _strip_words]
        if not _name_tokens:
            return None
        _name_query = " ".join(_name_tokens)

        results = _scheme_search(_name_query, max_results=3)
        results = [(sc, s) for sc, s in results if sc >= 15]
        if not results:
            return None
        top_score, top = results[0]
        second = results[1][0] if len(results) > 1 else 0
        # Require a meaningful score advantage
        if top_score >= 30 or (top_score >= 15 and second == 0) or top_score >= second * 1.8:
            return top
        return None

    # Detect scheme-specific intent words in this query
    _specific_doc_words  = {"document", "documents", "docs", "papers",
                            "paperwork", "certificate", "certificates", "proof",
                            "needed", "required", "need", "bring", "checklist"}
    _specific_apply_words = {"apply", "application", "register", "enroll",
                             "steps", "process", "procedure", "how"}
    _specific_benefit_words = {"benefit", "benefits", "amount", "loan",
                               "subsidy", "grant", "scholarship", "stipend",
                               "money", "receive", "get", "pension"}
    _specific_elig_words = {"eligible", "eligibility", "qualify", "criteria",
                            "who", "can", "requirement", "requirements",
                            "age", "income", "limit"}

    # Check whether a scheme name appears in this query. We use the
    # same cleaned-token approach as the intent gate later.
    _q_clean_early = _re.sub(r"[^a-z0-9 ]", " ",
                             _re.sub(r"-", " ", q_lower))
    _q_tokens_early = set(t for t in _q_clean_early.split() if len(t) > 2)

    # Try context first: if user asks a follow-up about an active scheme
    _follow_up_words = (
        _specific_doc_words | _specific_apply_words |
        _specific_benefit_words | _specific_elig_words
    )
    if _ctx_scheme and (token_set & _follow_up_words) and len(tokens) <= 8:
        # "What documents do I need?" after discussing PM SVANidhi
        s = _ctx_scheme
        if token_set & _specific_doc_words:
            return _scheme_response(s, "documents",
                f"Here are the **documents required** for **{s['name']}** from our database:")
        if token_set & _specific_apply_words:
            return _scheme_response(s, "apply",
                f"Here's **how to apply** for **{s['name']}** from our database:")
        if token_set & _specific_benefit_words:
            return _scheme_response(s, "benefits",
                f"Here are the **benefits** of **{s['name']}** from our database:")
        if token_set & _specific_elig_words:
            return _scheme_response(s, "eligibility",
                f"Here are the **eligibility criteria** for **{s['name']}** from our database:")

    # Try a direct named-scheme lookup combined with specific intent
    _has_specific_intent = bool(
        token_set & (
            _specific_doc_words | _specific_apply_words |
            _specific_benefit_words | _specific_elig_words
        )
    )
    if _has_specific_intent:
        _named = _find_named_scheme(raw)
        if _named:
            s = _named
            if token_set & _specific_doc_words:
                return _scheme_response(s, "documents",
                    f"Here are the **documents required** for **{s['name']}** from our database:")
            if token_set & _specific_apply_words:
                return _scheme_response(s, "apply",
                    f"Here's **how to apply** for **{s['name']}** from our database:")
            if token_set & _specific_benefit_words:
                return _scheme_response(s, "benefits",
                    f"Here are the **benefits** of **{s['name']}** from our database:")
            if token_set & _specific_elig_words:
                return _scheme_response(s, "eligibility",
                    f"Here are the **eligibility criteria** for **{s['name']}** from our database:")

    # ------------------------------------------------------------------
    # 8. General documents question (not scheme-specific)
    # ------------------------------------------------------------------
    doc_general_words = {"documents", "document", "docs", "papers",
                         "paperwork", "certificates", "certificate", "proof"}
    doc_q_words = {"what", "which", "need", "required", "require",
                   "bring", "prepare", "generally", "common", "typically", "might"}
    # Only fire if the query is short and doesn't name a specific scheme
    is_doc_general = (
        doc_general_words & token_set and
        doc_q_words & token_set and
        len(tokens) <= 9 and
        not any(s["name"].lower().split()[0] in q_lower for s in SCHEMES)
    )
    if is_doc_general:
        return _plain(
            "Most government welfare scheme applications require some or all of the following. "
            "The exact list varies by scheme — always check the official portal for current requirements:\n\n"
            "• **Identity proof** — Aadhaar card (most common), Voter ID, or Passport\n"
            "• **Address proof** — Aadhaar, utility bill, or ration card\n"
            "• **Income certificate** — issued by a competent state authority\n"
            "• **Caste / category certificate** — SC, ST, or OBC as applicable\n"
            "• **Bank account details** — account number and IFSC code (for DBT transfers)\n"
            "• **Academic documents** — mark sheets, certificates (for education schemes)\n"
            "• **Age proof** — birth certificate or Class X/XII certificate\n"
            "• **Photograph** — passport-size\n\n"
            "Each scheme on WelfareConnect has its own **Document Checklist** — click "
            "**\"View Full Guide →\"** on any scheme card for the specific list.\n\n"
            "You can also ask: \"What documents do I need for PM-KISAN?\" for a scheme-specific answer."
        )

    # ------------------------------------------------------------------
    # 8. How to apply — general (not naming a specific scheme)
    # ------------------------------------------------------------------
    apply_signals = {
        ("how", "apply"), ("how", "do", "apply"), ("how", "can", "apply"),
        ("how", "to", "apply"), ("application", "process"),
        ("applying", "scheme"), ("how", "register"), ("how", "enroll"),
    }
    is_apply_general = (
        any(all(w in token_set for w in ph) for ph in apply_signals) and
        len(tokens) <= 7 and
        not any(s["name"].lower().split()[0] in q_lower for s in SCHEMES)
    )
    if is_apply_general:
        return _plain(
            "Here's the general application process for government welfare schemes:\n\n"
            "**1. Find the right scheme**\n"
            "Use the **Find Schemes** section on WelfareConnect — search by keyword or category.\n\n"
            "**2. Check official eligibility**\n"
            "WelfareConnect provides a guide only. Visit the scheme's **Official Portal** to "
            "confirm current eligibility rules — criteria can change.\n\n"
            "**3. Prepare your documents**\n"
            "Gather the items listed in the scheme's document checklist — typically Aadhaar, "
            "income certificate, bank details, and any category certificates.\n\n"
            "**4. Apply on the official portal**\n"
            "Click **\"Open Official Portal ↗\"** in the scheme guide. Most central government "
            "schemes accept online applications; some require visiting a bank, local office, "
            "or Common Service Centre (CSC).\n\n"
            "**5. Track your application**\n"
            "Most portals provide tracking via your application or registration number.\n\n"
            "Ask me about a specific scheme for detailed steps — e.g. "
            "\"How do I apply for PM Vishwakarma?\"."
        )

    # ------------------------------------------------------------------
    # 9. Where to start / getting started
    # ------------------------------------------------------------------
    start_signals = {
        ("where", "start"), ("how", "start"), ("where", "begin"),
        ("how", "begin"), ("getting", "started"), ("get", "started"),
        ("first", "step"), ("what", "first"),
    }
    is_start = any(all(w in token_set for w in ph) for ph in start_signals) and len(tokens) <= 8
    if is_start:
        return _plain(
            "Here's a good way to get started:\n\n"
            "**Step 1 — Browse or search**\n"
            "Go to **Find Schemes** (top navigation). Choose a category or type a keyword "
            "like \"student\", \"farmer\", \"pension\", or \"business\".\n\n"
            "**Step 2 — Read the scheme guide**\n"
            "Click **\"View Full Guide →\"** on any card to read the eligibility overview, "
            "benefits, and application steps.\n\n"
            "**Step 3 — Prepare documents**\n"
            "Use the interactive checklist to track which documents you have ready.\n\n"
            "**Step 4 — Apply officially**\n"
            "Click **\"Open Official Portal ↗\"** — the actual application is submitted on "
            "the government website.\n\n"
            "You can also tell me about yourself and I'll suggest where to look — "
            "for example: \"I'm a student\" or \"I want to start a business\"."
        )

    # ------------------------------------------------------------------
    # 10. Off-topic guard (expanded) — runs BEFORE profile handlers and
    #     scheme search so unrelated questions never reach scheme logic.
    # ------------------------------------------------------------------
    _off_topic_words = {
        # Sports & games
        "weather", "cricket", "football", "basketball", "tennis", "sport",
        "sports", "badminton", "volleyball", "hockey", "chess", "golf",
        "swimming", "athlete", "athletics", "olympics", "ipl", "fifa",
        "game", "games", "player", "players", "team", "teams", "match",
        "tournament", "league",
        # Entertainment
        "movie", "movies", "film", "films", "actor", "actress", "celebrity",
        "celebrities", "song", "songs", "music", "album", "series", "netflix",
        "bollywood", "hollywood", "ott", "streaming",
        # Food & lifestyle
        "recipe", "cook", "cooking", "cuisine", "restaurant", "hotel",
        "dating", "relationship", "fashion", "style", "fitness", "gym",
        # Finance & general market
        "stock", "stocks", "crypto", "bitcoin", "cryptocurrency", "forex",
        "share", "market", "trading", "investment", "mutual", "sensex",
        "nifty", "broker",
        # Astrology & entertainment misc
        "astrology", "horoscope", "zodiac", "joke", "jokes",
        # Travel
        "travel", "flight", "airline", "ticket", "visa", "passport",
        "tourism", "trip", "vacation",
        # General science / technology topics unrelated to welfare
        "python", "java", "javascript", "programming", "coding", "code",
        "html", "css", "react", "angular", "node", "database", "sql",
        "algorithm", "software", "hardware", "computer", "laptop",
        "smartphone", "phone", "android", "ios", "iphone", "gadget",
        "robot", "drone", "satellite", "rocket", "spacecraft",
        "artificial", "intelligence", "machine", "learning", "neural",
        "chatgpt", "openai", "blockchain", "nft",
        # Academic subjects (non-welfare)
        "maths", "math", "mathematics", "science", "history", "geography",
        "biology", "physics", "chemistry", "botany", "zoology", "geology",
        "literature", "grammar", "language", "linguistics", "philosophy",
        "psychology", "sociology", "economics", "politics", "political",
        "constitution", "law", "legal", "lawyer", "court", "judge",
        # General knowledge
        "capital", "country", "countries", "continent", "ocean", "river",
        "mountain", "planet", "solar", "system", "galaxy", "universe",
        "population", "election", "president", "prime", "minister",
        "parliament", "war", "army", "navy", "airforce", "military",
        "flag", "currency", "religion", "temple", "church", "mosque",
        "festival", "culture", "tradition", "mythology",
        # Medicine & health (not welfare schemes)
        "doctor", "medicine", "hospital", "disease", "virus", "vaccine",
        "covid", "cancer", "diabetes", "surgery", "therapy", "treatment",
        "symptom", "diagnosis", "pharmacy", "drug", "tablet", "tablet",
        # Misc
        "news", "newspaper", "headline", "gossip",
    }
    # Only fire if none of the tokens are scheme-name words (safety valve
    # so a message like "Tell me about the Pradhan Mantri science scheme"
    # can still proceed to scheme search).
    # Exception: "capital" is a scheme keyword (in CLCSS) but also a very
    # common general-knowledge word — always treat it as off-topic here.
    _force_off_topic = {"capital", "president", "prime", "minister"}
    _scheme_name_words = set()
    for _s in SCHEMES:
        _scheme_name_words.update(
            t for t in _s["name"].lower().replace("-", " ").split()
            if len(t) > 3
        )
    # A token forces off-topic if it's in the off-topic set AND either
    # it's in _force_off_topic OR it's not a scheme name word.
    _blocking_tokens = set()
    for _ot in (token_set & _off_topic_words):
        if _ot in _force_off_topic or _ot not in _scheme_name_words:
            _blocking_tokens.add(_ot)
    if _blocking_tokens:
        return _plain(
            "I'm the WelfareConnect Assistant — I'm focused on government welfare schemes "
            "and how to use the WelfareConnect website.\n\n"
            "I'm not able to help with that topic, but I'm happy to help you:\n"
            "• Discover schemes (e.g. \"Show education schemes\")\n"
            "• Understand a specific scheme (e.g. \"Tell me about PM-KISAN\")\n"
            "• Find documents or application steps\n"
            "• Navigate the WelfareConnect website\n\n"
            "What would you like to know about welfare schemes?",
            "not_found"
        )

    # ------------------------------------------------------------------
    # 11. Welfare-adjacent topics not in the current database
    # ------------------------------------------------------------------
    _not_in_db = {
        "housing", "house", "home", "shelter", "pmay", "awas",
        "health", "healthcare", "medical",
        "water", "sanitation", "toilet", "swachh",
        "road", "infrastructure", "transport", "railway",
        "electricity", "energy", "lpg",
        "ration", "grain", "pds",
    }
    if token_set & _not_in_db:
        _scheme_kw = set()
        for _s in SCHEMES:
            _scheme_kw.update(
                t for t in _s["name"].lower().replace("-", " ").split()
                if len(t) > 3
            )
        if not (token_set & _scheme_kw):
            return _plain(
                "WelfareConnect's current database focuses on schemes covering education, "
                "skills & employment, business & livelihood, pension & social security, "
                "agriculture, financial inclusion, and digital services.\n\n"
                "The topic you asked about may fall outside what the current database covers. "
                "For a wider search across all government schemes, you can visit:\n"
                "• **india.gov.in** — National Government Services Portal\n"
                "• **myscheme.gov.in** — Government scheme finder across all sectors\n\n"
                "Is there anything else I can help you with from the WelfareConnect database?",
                "not_found"
            )

    # ------------------------------------------------------------------
    # 12. Explicit scheme-intent gate
    #
    #     Scheme cards are shown ONLY when the message expresses a clear
    #     intent to find, explore, compare or get recommendations about
    #     schemes.  Informational questions ("what is X?") are routed to
    #     scheme search only when a specific scheme name is detected.
    # ------------------------------------------------------------------

    # Words that signal the user wants to FIND / EXPLORE schemes
    _find_intent_words = {
        "show", "list", "give", "suggest", "recommend", "find", "search",
        "explore", "browse", "available",
        "options", "opportunities", "programs", "programmes",
    }
    # Words that signal the user wants INFO about a SPECIFIC scheme
    _info_intent_words = {
        "what", "explain", "describe", "tell", "about", "details",
        "eligibility", "eligible", "qualify", "documents", "document",
        "apply", "application", "steps", "process", "how", "benefit",
        "amount", "subsidy", "loan", "grant",
    }
    # Audience / profile words that map to scheme categories
    _audience_words = {
        "student", "students", "youth", "farmer", "farmers", "vendor", "vendors",
        "artisan", "artisans", "entrepreneur", "entrepreneurs", "worker", "workers",
        "women", "woman", "senior", "elderly", "disabled", "rural", "poor",
        "unemployed", "graduate", "graduates",
    }
    # Scheme-name keywords — built by stripping punctuation from every
    # scheme name token that is meaningful (length > 3, not a filler word)
    import re as _re
    _scheme_kw_set = set()
    _kw_filler = {
        "pradhan", "mantri", "national", "scheme", "yojana",
        "india", "indian", "under", "from", "with", "that",
        "prime", "minister", "the", "for", "and", "small",
    }
    for _s in SCHEMES:
        # Strip ALL non-alpha-numeric characters before splitting
        _clean_name = _re.sub(r"[^a-z0-9 ]", " ", _s["name"].lower())
        _toks = [
            t for t in _clean_name.split()
            if len(t) > 2 and t not in _kw_filler
        ]
        if _toks:
            # Take first 5 meaningful tokens AND the last token (often the acronym)
            _candidates = _toks[:5]
            if _toks[-1] not in _candidates:
                _candidates.append(_toks[-1])
            _scheme_kw_set.update(_candidates)

    has_find_intent  = bool(token_set & _find_intent_words)
    has_info_intent  = bool(token_set & _info_intent_words)
    has_audience     = bool(token_set & _audience_words)
    # Clean query tokens for scheme-name matching.
    # Also split on hyphens so "pm-kisan" → {"pm","kisan"} and "kisan" matches.
    _clean_query_tokens = set()
    for _t in tokens:
        # Remove all non-alphanumeric (whole token)
        _whole = _re.sub(r"[^a-z0-9]", "", _t)
        if _whole:
            _clean_query_tokens.add(_whole)
        # Also split on hyphens within the original token
        for _part in _t.split("-"):
            _p = _re.sub(r"[^a-z0-9]", "", _part)
            if len(_p) > 2:
                _clean_query_tokens.add(_p)
    _clean_query_tokens -= {""}
    has_scheme_name  = bool(_clean_query_tokens & _scheme_kw_set)

    # Decide whether to proceed to scheme search at all.
    # We proceed if:
    # (a) user clearly wants to find/explore schemes (action verb), OR
    # (b) user mentions a known scheme name (scheme name token in query), OR
    # (c) user wants to find schemes for a particular audience (profile handlers handle this earlier)
    # Pure informational questions with NO scheme name don't proceed —
    # the min-score threshold is the secondary safety net.
    _proceed_to_search = (
        has_find_intent or
        has_scheme_name or
        (has_find_intent and has_audience)
    )

    # Special case: user said "scheme" / "schemes" with an unknown name
    # (e.g. "What is the Ayushman Bharat scheme?") → honest not-found rather
    # than generic out-of-scope message.
    # Only fire this when the query has an info-style phrasing, NOT a plain
    # discovery/browsing phrase like "schemes for farmers" or "which schemes".
    _info_phrasing = {"what", "tell", "about", "explain", "describe", "show", "explain"}
    _mentions_scheme_word = bool(token_set & {"scheme", "schemes", "yojana"})
    _has_info_phrasing = bool(token_set & _info_phrasing)
    if (not _proceed_to_search and _mentions_scheme_word
            and not has_scheme_name and _has_info_phrasing
            and not (token_set & _audience_words)):
        return {
            "type":    "not_found",
            "text":    (
                "I wasn't able to find that specific scheme in the WelfareConnect database.\n\n"
                "WelfareConnect currently covers **" + str(len(SCHEMES)) + " schemes** across "
                "education, skills & employment, business & livelihood, "
                "pension & social security, agriculture, financial inclusion, and digital services.\n\n"
                "You can:\n"
                "• Browse all available schemes using the **Find Schemes** section\n"
                "• Visit **myscheme.gov.in** for a comprehensive government scheme search"
            ),
            "schemes": [],
            "intent":  "not_found",
            "context": {}
        }

    # ------------------------------------------------------------------
    # 13. Profile-based guidance — only fires when intent is to FIND
    #     schemes; "what is X?" style questions bypass these handlers.
    # ------------------------------------------------------------------

    # Require an explicit find/recommend verb, not just any info word
    _profile_find_verbs = {
        "suggest", "recommend", "show", "list", "find", "explore",
        "want", "need", "looking", "available", "schemes", "scheme",
        "help", "options", "opportunities",
    }

    # student
    student_profile = {
        "student", "students", "studying", "scholarship",
        "undergraduate", "postgraduate",
    }
    is_student_profile = (
        student_profile & token_set and
        _profile_find_verbs & token_set
    )
    if is_student_profile:
        edu_schemes = [s for s in SCHEMES if s["category"] == "Education"][:4]
        return _list_response(
            edu_schemes,
            "general",
            "For students, WelfareConnect covers several **Education** category schemes "
            "including scholarships, free online courses, and skill training opportunities. "
            "Here are some to explore — check each scheme's official eligibility criteria "
            "to see which ones apply to your situation:"
        )

    # business / entrepreneur
    biz_profile = {
        "entrepreneur", "enterprise", "startup", "vendor", "artisan",
        "msme", "livelihood", "manufacturing",
    }
    is_biz_profile = (
        biz_profile & token_set and
        _profile_find_verbs & token_set
    )
    if is_biz_profile:
        biz_schemes = [s for s in SCHEMES if s["category"] == "Business & Livelihood"][:4]
        return _list_response(
            biz_schemes,
            "general",
            "For business and livelihood, WelfareConnect covers schemes that support "
            "entrepreneurs, micro-enterprises, street vendors, food processors, and artisans. "
            "Here are some relevant schemes — verify eligibility on the official portals before applying:"
        )

    # employment / skills
    empl_profile = {
        "unemployed", "apprentice", "apprenticeship", "unskilled",
    }
    is_empl_profile = (
        empl_profile & token_set and
        _profile_find_verbs & token_set
    )
    if is_empl_profile:
        empl_schemes = [s for s in SCHEMES
                        if s["category"] in ("Skills & Employment", "Employment & Livelihood")][:4]
        return _list_response(
            empl_schemes,
            "general",
            "For employment and skills, WelfareConnect has schemes covering skill training, "
            "apprenticeships, job portals, and rural employment programmes. "
            "Here are some to explore — check the official eligibility criteria for each:"
        )

    # farmers / agriculture
    farm_profile = {
        "farmer", "farmers", "farming", "agriculture", "agricultural",
        "kisan", "crop", "crops",
    }
    is_farm_profile = (
        farm_profile & token_set and
        _profile_find_verbs & token_set
    )
    if is_farm_profile:
        farm_schemes = [s for s in SCHEMES if s["category"] == "Agriculture"][:4]
        if not farm_schemes:
            farm_schemes = [s for s in SCHEMES if "farmer" in s.get("audience", "").lower()
                            or "kisan" in s["name"].lower()][:4]
        return _list_response(
            farm_schemes,
            "general",
            "For farmers and agriculture, WelfareConnect has schemes covering income support, "
            "market access, and rural livelihoods. "
            "Here are some to explore — verify eligibility on the official portals:"
        )

    # ------------------------------------------------------------------
    # 14. "I am a [profile]" — acknowledge and offer help without
    #     immediately dumping scheme cards
    # ------------------------------------------------------------------
    identity_words = {
        "student", "farmer", "vendor", "artisan", "worker", "unemployed",
        "youth", "woman", "women", "graduate", "entrepreneur", "senior",
        "elderly", "disabled", "rural",
    }
    identity_signals = {"am", "im", "i'm", "myself"}
    is_identity_stmt = (
        identity_words & token_set and
        identity_signals & token_set and
        len(tokens) <= 7
    )
    if is_identity_stmt:
        matched = (identity_words & token_set).pop()
        return _plain(
            f"Thanks for sharing that. As a **{matched}**, there may be relevant government "
            f"welfare schemes on WelfareConnect that could help you.\n\n"
            f"You can:\n"
            f"• Ask me to show schemes for {matched}s — e.g. \"Show schemes for {matched}s\"\n"
            f"• Use the **Find Schemes** section and filter by category\n"
            f"• Use the **✨ Find My Schemes** wizard on the website\n\n"
            "What would you like to know specifically — eligibility, benefits, documents, "
            "or application steps for a particular scheme?"
        )

    # ------------------------------------------------------------------
    # SCHEME SEARCH — only reached when _proceed_to_search is True
    # A minimum score of 15 is required to show any scheme card.
    # This prevents common English words from generating scheme results.
    # ------------------------------------------------------------------
    if not _proceed_to_search:
        # The message has no scheme-find intent and no scheme name — give a
        # polite "out of scope" response rather than searching.
        return _plain(
            "I'm here to help with WelfareConnect and government welfare schemes.\n\n"
            "I can help you:\n"
            "• **Find schemes** — e.g. \"Show education schemes\" or \"Schemes for farmers\"\n"
            "• **Learn about a specific scheme** — e.g. \"What is PM-KISAN?\"\n"
            "• **Check eligibility or documents** — e.g. \"Who is eligible for PMKVY?\"\n"
            "• **Understand application steps** — e.g. \"How do I apply for PM SVANidhi?\"\n\n"
            "What would you like to know?",
            "general"
        )

    _MIN_SCORE = 15  # minimum relevance score to show a scheme card

    scored  = _scheme_search(raw, max_results=5)
    # Filter out low-confidence matches
    scored  = [(sc, s) for sc, s in scored if sc >= _MIN_SCORE]
    matches = [s for _, s in scored]
    intent  = _detect_intent(tokens)
    cat     = _detect_category(tokens)

    # ------------------------------------------------------------------
    # If top result is a strong name match → single scheme detail view
    # ------------------------------------------------------------------
    if matches:
        top_score    = scored[0][0]
        top          = scored[0][1]
        second_score = scored[1][0] if len(scored) > 1 else 0

        top_name_l = top["name"].lower()
        name_words = set(top_name_l.replace("-", " ").split())
        query_words = set(q_lower.replace("-", " ").split())
        overlap = name_words & query_words
        filler = {
            "the", "for", "and", "are", "what", "tell", "about",
            "me", "find", "show", "give", "get", "how", "with",
            "can", "this", "that", "have", "need", "want", "know",
            "info", "information", "details", "scheme", "schemes",
            "yojana", "pradhan", "mantri", "rashtriya", "national",
            "pm", "is", "of", "in", "to", "an", "its", "does",
        }
        name_meaningful  = name_words  - filler
        query_meaningful = query_words - filler
        meaningful_overlap = name_meaningful & query_meaningful

        strong_name_match = (
            q_lower in top_name_l or
            top_name_l in q_lower or
            len(overlap) >= 3 or
            # Meaningful overlap ≥ 60% of scheme name meaningful words
            # (require at least 2 meaningful words in the name to avoid
            #  firing on single-word short names)
            (len(name_meaningful) >= 2 and
             len(meaningful_overlap) / len(name_meaningful) >= 0.6) or
            # Top score dominates runner-up by 2× with a high minimum
            (top_score >= 30 and second_score == 0) or
            (top_score >= 40 and top_score >= second_score * 2)
        )

        if strong_name_match and intent in ("general", "benefits", "eligibility", "documents", "apply"):
            s = top
            intro = {
                "general":     f"Here's what I found about **{s['name']}** in the WelfareConnect database:",
                "benefits":    f"Here are the **benefits** of **{s['name']}** from our database:",
                "eligibility": f"Here are the **eligibility criteria** for **{s['name']}** from our database:",
                "documents":   f"Here are the **documents required** for **{s['name']}** from our database:",
                "apply":       f"Here's **how to apply** for **{s['name']}** from our database:",
            }[intent]
            return _scheme_response(s, intent, intro)

    # ------------------------------------------------------------------
    # Category-based list (when a category keyword was detected but
    # scheme name search returned nothing above the score threshold)
    # ------------------------------------------------------------------
    if cat and not matches:
        cat_schemes = [s for s in SCHEMES if s["category"] == cat][:5]
        if cat_schemes:
            return _list_response(
                cat_schemes,
                "general",
                f"Here are schemes in the **{cat}** category from the WelfareConnect database. "
                "Please verify your eligibility on the official portal before applying."
            )

    # ------------------------------------------------------------------
    # Keyword search returned results above the score threshold
    # ------------------------------------------------------------------
    if matches:
        if len(matches) == 1:
            s = matches[0]
            return _scheme_response(s, intent, f"The closest match in our database is **{s['name']}**:")
        cat_hint = f" in the **{cat}** category" if cat else ""
        return _list_response(
            matches,
            intent,
            f"I found {len(matches)} scheme(s){cat_hint} that match your question. "
            "These are from the WelfareConnect database — please verify eligibility "
            "on the official portal before applying."
        )

    # ------------------------------------------------------------------
    # No results above the score threshold
    # ------------------------------------------------------------------
    # Check if the user named a scheme whose tokens aren't in any match.
    # If so, give an honest "not in our database" response.
    def _honest_not_found():
        return {
            "type":    "not_found",
            "text":    (
                "I wasn't able to find that specific scheme in the WelfareConnect database.\n\n"
                "This scheme may not be in our current database, or it may be listed under "
                "a different name. You can:\n"
                "• Browse all available schemes using the **Find Schemes** section\n"
                "• Try the scheme's full official name\n"
                "• Visit **myscheme.gov.in** for a comprehensive government scheme search"
            ),
            "schemes": [],
            "intent":  "not_found",
            "context": {}
        }

    if has_scheme_name:
        if not matches:
            return _honest_not_found()
        # Check if the returned schemes actually contain the query's scheme
        # name tokens — if none do, the results are spurious substitutions.
        _query_name_tokens = _clean_query_tokens & _scheme_kw_set
        _top_name_clean = _re.sub(r"[^a-z0-9 ]", " ", matches[0]["name"].lower())
        _any_token_in_top = any(t in _top_name_clean for t in _query_name_tokens)
        if not _any_token_in_top:
            return _honest_not_found()

    return {
        "type":    "not_found",
        "text":    (
            "I wasn't able to find a scheme matching your question in the "
            "WelfareConnect database. The database currently covers "
            f"{len(SCHEMES)} central and state government schemes.\n\n"
            "You could try:\n"
            "• Rephrasing with the scheme name (e.g. \"Tell me about PM-KISAN\")\n"
            "• Using the **Find Schemes** section to browse all schemes by category\n"
            "• Visiting **myscheme.gov.in** for a broader government scheme search"
        ),
        "schemes": [],
        "intent":  "not_found",
        "context": {}
    }


@app.post("/api/chat")
def chat():
    data    = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:300]
    context = data.get("context")  # optional dict from frontend, e.g. {"last_scheme_id": 6}

    if not message:
        return jsonify({
            "type":    "not_found",
            "text":    "Please type a question to get started.",
            "schemes": [],
            "intent":  "empty",
            "context": {}
        })

    result = _build_response(message, context=context)

    # Slim down schemes for the response — keep only fields the UI needs
    slim_fields = ("id", "name", "category", "audience", "summary",
                   "eligibility", "benefits", "documents", "steps", "official")
    result["schemes"] = [
        {k: s[k] for k in slim_fields if k in s}
        for s in result["schemes"]
    ]

    # Ensure context is always present in the response
    if "context" not in result:
        result["context"] = {}

    return jsonify(result)


# ==================================================
# PRIVATE ADMIN AREA
# ==================================================

ADMIN_PASSWORD = "welfare123"


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password", "")

        if password != ADMIN_PASSWORD:
            return render_template(
                "admin.html",
                error="Incorrect password.",
                responses=None,
                analysis=None,
                analytics=None
            )

        with sqlite3.connect(DB) as con:
            con.row_factory = sqlite3.Row

            # Survey responses
            responses = con.execute("""
                SELECT
                    id,
                    name,
                    status,
                    gender,
                    age_group,
                    q1, q2, q3, q4, q5,
                    q6, q7, q8, q9, q10,
                    score,
                    created_at
                FROM survey_responses
                ORDER BY id DESC
            """).fetchall()

            # Overall survey statistics
            total_responses = con.execute("""
                SELECT COUNT(*)
                FROM survey_responses
            """).fetchone()[0]

            average_score = con.execute("""
                SELECT COALESCE(AVG(score), 0)
                FROM survey_responses
            """).fetchone()[0]

            analysis = {
                "total_count": total_responses,
                "average_score": round(average_score, 1)
            }

            # Website analytics
            scheme_map = {s["id"]: s["name"] for s in SCHEMES}

            total_visitors = con.execute(
                "SELECT COUNT(*) FROM visitor_sessions"
            ).fetchone()[0]

            total_visits = con.execute(
                "SELECT COALESCE(SUM(visit_count), 0) FROM visitor_sessions"
            ).fetchone()[0]

            total_activities = con.execute(
                "SELECT COUNT(*) FROM activity_events"
            ).fetchone()[0]

            scheme_view_count = con.execute(
                "SELECT COUNT(*) FROM scheme_views"
            ).fetchone()[0]

            top_scheme_rows = con.execute("""
                SELECT scheme_id, COUNT(*)
                FROM activity_events
                WHERE event_type='scheme_view'
                  AND scheme_id IS NOT NULL
                GROUP BY scheme_id
                ORDER BY COUNT(*) DESC
                LIMIT 8
            """).fetchall()

            top_schemes = [
                {
                    "name": scheme_map.get(r[0], f"Scheme {r[0]}"),
                    "views": r[1]
                }
                for r in top_scheme_rows
            ]

            search_rows = con.execute("""
                SELECT query_text, COUNT(*)
                FROM activity_events
                WHERE event_type='search'
                  AND query_text IS NOT NULL
                  AND query_text != ''
                GROUP BY query_text
                ORDER BY COUNT(*) DESC
                LIMIT 8
            """).fetchall()

            top_searches = [
                {
                    "query": r[0],
                    "count": r[1]
                }
                for r in search_rows
            ]

            daily_rows = con.execute("""
                SELECT substr(created_at, 1, 10), COUNT(*)
                FROM activity_events
                WHERE created_at >= datetime('now', '-6 days')
                GROUP BY substr(created_at, 1, 10)
                ORDER BY substr(created_at, 1, 10)
            """).fetchall()

            daily_activity = [
                {
                    "day": r[0],
                    "events": r[1]
                }
                for r in daily_rows
            ]

            recent_rows = con.execute("""
                SELECT
                    visitor_id,
                    event_type,
                    scheme_id,
                    query_text,
                    details,
                    created_at
                FROM activity_events
                ORDER BY id DESC
                LIMIT 25
            """).fetchall()

            recent_activity = [
                {
                    "visitor_id": r[0][-8:],
                    "event_type": r[1],
                    "scheme": scheme_map.get(r[2], "") if r[2] else "",
                    "query": r[3] or "",
                    "details": r[4] or "",
                    "created_at": r[5]
                }
                for r in recent_rows
            ]

            analytics = {
                "total_visitors": total_visitors,
                "total_visits": total_visits,
                "total_activities": total_activities,
                "scheme_views": scheme_view_count,
                "top_schemes": top_schemes,
                "top_searches": top_searches,
                "daily_activity": daily_activity,
                "recent_activity": recent_activity
            }

            return render_template(
                "admin.html",
                error=None,
                responses=responses,
                analysis=analysis,
                analytics=analytics
            )

    return render_template(
        "admin.html",
        error=None,
        responses=None,
        analysis=None,
        analytics=None
    )


# ==================================================
# CSV EXPORT
# ==================================================

@app.get("/admin/export")
def export_csv():
    from io import StringIO
    import csv

    password = request.args.get("password", "")

    if password != ADMIN_PASSWORD:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    with sqlite3.connect(DB) as con:
        con.row_factory = sqlite3.Row

        responses = con.execute("""
            SELECT
                id,
                name,
                status,
                gender,
                age_group,
                q1, q2, q3, q4, q5,
                q6, q7, q8, q9, q10,
                score,
                created_at
            FROM survey_responses
            ORDER BY id ASC
        """).fetchall()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Name",
        "Current Status",
        "Gender",
        "Age Group",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
        "Q8",
        "Q9",
        "Q10",
        "Score (%)",
        "Submitted At"
    ])

    for r in responses:
        writer.writerow([
            r["id"],
            r["name"],
            r["status"],
            r["gender"],
            r["age_group"],
            r["q1"],
            r["q2"],
            r["q3"],
            r["q4"],
            r["q5"],
            r["q6"],
            r["q7"],
            r["q8"],
            r["q9"],
            r["q10"],
            r["score"],
            r["created_at"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=welfareconnect_survey_responses.csv"
        }
    )


init_db()

if __name__ == "__main__":
    app.run(debug=True)