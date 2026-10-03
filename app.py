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
        blob = " ".join([
            s["name"],
            s["category"],
            s["audience"],
            s["summary"]
        ]).lower()

        if q and q not in blob:
            continue

        if category != "All" and s["category"] != category:
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
    q = query.lower().strip()
    if not q:
        return []

    scored = []
    tokens = [t for t in q.replace(",", " ").split() if len(t) > 2]

    for s in SCHEMES:
        score = 0

        name_l = s["name"].lower()
        # Exact or near-exact name match
        if q == name_l:
            score += 100
        elif q in name_l:
            score += 60
        else:
            # Partial token matches on name
            for t in tokens:
                if t in name_l:
                    score += 15

        # Category / audience match
        cat_l = s["category"].lower()
        aud_l = s["audience"].lower()
        for t in tokens:
            if t in cat_l:
                score += 12
            if t in aud_l:
                score += 10

        # Summary / eligibility / benefits
        rich_blob = " ".join([
            s.get("summary", ""),
            s.get("eligibility", ""),
            s.get("benefits", ""),
        ]).lower()
        for t in tokens:
            if t in rich_blob:
                score += 5

        # Documents / steps
        detail_blob = " ".join(
            s.get("documents", []) + s.get("steps", [])
        ).lower()
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


def _build_response(message):
    """
    Returns a dict:
      type: "scheme_detail" | "scheme_list" | "not_found" | "greeting" | "general"
      text: str
      schemes: list of scheme dicts (slim, safe for JSON)
      intent: str
    """
    raw = message.strip()
    q_lower = raw.lower()
    tokens = [t.strip("?!.,;:'\"()") for t in q_lower.split() if len(t.strip("?!.,;:'\"()")) > 1]
    token_set = set(tokens)

    # Helper: text-only response with no scheme cards
    def _plain(text, intent="general"):
        return {"type": "general", "text": text, "schemes": [], "intent": intent}

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
    # 7. General documents question (not scheme-specific)
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
    # 10. Profile-based guidance: student
    # ------------------------------------------------------------------
    student_profile = {"student", "students", "studying", "study",
                       "college", "university", "school", "scholarship",
                       "degree", "diploma", "undergraduate", "postgraduate"}
    profile_verbs   = {"am", "im", "i'm", "looking", "want", "need",
                       "suggest", "recommend", "what", "explore", "help"}
    is_student_profile = (
        student_profile & token_set and
        (profile_verbs & token_set or len(tokens) <= 4) and
        # Don't fire if they're asking about a specific named scheme
        not any(w in q_lower for w in ["eligib", "benefit", "document", "apply",
                                        "pm-kisan", "mgnrega", "nats", "naps"])
    )
    if is_student_profile:
        edu_schemes = [s for s in SCHEMES if s["category"] == "Education"][:4]
        return {
            "type":    "scheme_list",
            "text": (
                "For students, WelfareConnect covers several **Education** category schemes "
                "including scholarships, free online courses, and skill training opportunities. "
                "Here are some to explore — check each scheme's official eligibility criteria "
                "to see which ones apply to your situation:"
            ),
            "schemes": edu_schemes,
            "intent":  "general"
        }

    # ------------------------------------------------------------------
    # 11. Profile-based guidance: business / entrepreneur
    # ------------------------------------------------------------------
    biz_profile = {"business", "entrepreneur", "enterprise", "startup",
                   "shop", "vendor", "self-employed", "artisan", "msme",
                   "livelihood", "manufacturing", "trade", "food"}
    is_biz_profile = (
        biz_profile & token_set and
        profile_verbs & token_set and
        not any(w in q_lower for w in ["eligib", "benefit", "document", "apply",
                                        "pmegp", "svanidhi", "stand-up", "pmfme"])
    )
    if is_biz_profile:
        biz_schemes = [s for s in SCHEMES if s["category"] == "Business & Livelihood"][:4]
        return {
            "type":    "scheme_list",
            "text": (
                "For business and livelihood, WelfareConnect covers schemes that support "
                "entrepreneurs, micro-enterprises, street vendors, food processors, and artisans. "
                "Here are some relevant schemes — verify eligibility on the official portals before applying:"
            ),
            "schemes": biz_schemes,
            "intent":  "general"
        }

    # ------------------------------------------------------------------
    # 12. Profile-based guidance: employment / skills / job seeker
    # ------------------------------------------------------------------
    empl_profile = {"job", "jobs", "employment", "unemployed", "work", "career",
                    "skill", "skills", "training", "apprentice", "apprenticeship",
                    "rural", "unskilled"}
    is_empl_profile = (
        empl_profile & token_set and
        profile_verbs & token_set and
        not any(w in q_lower for w in ["eligib", "benefit", "document", "apply",
                                        "mgnrega", "ddu", "rseti", "nats", "naps", "ncs"])
    )
    if is_empl_profile:
        empl_schemes = [s for s in SCHEMES
                        if s["category"] in ("Skills & Employment", "Employment & Livelihood")][:4]
        return {
            "type":    "scheme_list",
            "text": (
                "For employment and skills, WelfareConnect has schemes covering skill training, "
                "apprenticeships, job portals, and rural employment programmes. "
                "Here are some to explore — check the official eligibility criteria for each:"
            ),
            "schemes": empl_schemes,
            "intent":  "general"
        }

    # ------------------------------------------------------------------
    # 13. Off-topic guard — runs before scheme search so clearly
    #     unrelated questions never leak into scheme results
    # ------------------------------------------------------------------
    _off_topic_words = {
        "weather", "cricket", "football", "basketball", "tennis", "sport",
        "sports", "movie", "movies", "film", "films", "recipe", "cook",
        "cooking", "news", "stock", "stocks", "crypto", "bitcoin", "share",
        "market", "astrology", "horoscope", "joke", "jokes", "game", "games",
        "travel", "hotel", "flight", "restaurant", "dating", "relationship",
        "celebrity", "song", "music", "maths", "math", "science", "history",
        "geography", "biology", "physics", "chemistry",
    }
    if token_set & _off_topic_words:
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
    # 14. Welfare-adjacent topics not in the current database
    #     (check before scheme search to avoid spurious matches)
    # ------------------------------------------------------------------
    _not_in_db = {
        "housing", "house", "home", "shelter", "pmay", "pradhan", "awas",
        "health", "healthcare", "hospital", "medical", "treatment",
        "water", "sanitation", "toilet", "swachh",
        "road", "infrastructure", "transport", "railway",
        "electricity", "solar", "energy", "lpg",
        "food", "ration", "grain", "pds",
    }
    # Only fire if there's no other strong intent — i.e. no scheme keyword overlap
    if token_set & _not_in_db and len(tokens) <= 8:
        # Check if the query also contains a strong scheme keyword — if so, let search handle it
        _scheme_keywords = set()
        for s in SCHEMES:
            _scheme_keywords.update(s["name"].lower().split())
        overlap_with_schemes = token_set & _scheme_keywords
        if not overlap_with_schemes:
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
    # Run scheme search — all conversational handlers have run above
    # ------------------------------------------------------------------
    scored  = _scheme_search(raw, max_results=5)
    matches = [s for _, s in scored]
    intent  = _detect_intent(tokens)
    cat     = _detect_category(tokens)

    # ------------------------------------------------------------------
    # If top result is a very strong name match, give scheme detail
    # ------------------------------------------------------------------
    if matches:
        top_score       = scored[0][0]
        top             = scored[0][1]
        second_score    = scored[1][0] if len(scored) > 1 else 0

        top_name_l = top["name"].lower()
        name_words = set(top_name_l.replace("-", " ").split())
        query_words = set(q_lower.replace("-", " ").split())
        overlap = name_words & query_words
        filler = {"the", "for", "and", "are", "what", "tell", "about",
                  "me", "find", "show", "give", "get", "how", "with",
                  "can", "this", "that", "have", "need", "want", "know",
                  "info", "information", "details", "scheme", "schemes",
                  "yojana", "pradhan", "mantri", "rashtriya", "national"}

        name_meaningful    = name_words  - filler
        query_meaningful   = query_words - filler
        meaningful_overlap = name_meaningful & query_meaningful

        strong_name_match = (
            q_lower in top_name_l or
            top_name_l in q_lower or
            len(overlap) >= 3 or
            (len(meaningful_overlap) >= 1 and len(name_meaningful) <= 3) or
            (len(name_meaningful) > 0 and
             len(meaningful_overlap) / len(name_meaningful) >= 0.6) or
            # Top score dominates runner-up by 2× and has a name component
            (top_score >= 15 and second_score == 0) or
            (top_score >= 20 and top_score >= second_score * 2)
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

            return {
                "type":   "scheme_detail",
                "text":   intro,
                "schemes": [s],
                "intent": intent
            }

    # ------------------------------------------------------------------
    # Category-based list
    # ------------------------------------------------------------------
    if cat and not matches:
        cat_schemes = [s for s in SCHEMES if s["category"] == cat][:5]
        if cat_schemes:
            return {
                "type":   "scheme_list",
                "text":   (
                    f"I found {len(cat_schemes)} scheme(s) in the "
                    f"**{cat}** category that may be relevant. "
                    "Please check each scheme's official eligibility criteria to confirm whether you qualify."
                ),
                "schemes": cat_schemes,
                "intent":  "general"
            }

    # ------------------------------------------------------------------
    # Keyword search returned results
    # ------------------------------------------------------------------
    if matches:
        if len(matches) == 1:
            s = matches[0]
            return {
                "type":   "scheme_detail",
                "text":   f"The closest match in our database is **{s['name']}**:",
                "schemes": [s],
                "intent":  intent
            }

        cat_hint = f" in the **{cat}** category" if cat else ""
        return {
            "type":   "scheme_list",
            "text":   (
                f"I found {len(matches)} scheme(s){cat_hint} that may be relevant to your question. "
                "These are based on the information available in the WelfareConnect database. "
                "Please verify your eligibility on the official portal before applying."
            ),
            "schemes": matches,
            "intent":  intent
        }

    # ------------------------------------------------------------------
    # No results
    # ------------------------------------------------------------------
    return {
        "type":   "not_found",
        "text":   (
            "I wasn't able to find information matching your question in the "
            "WelfareConnect database. The database currently covers "
            f"{len(SCHEMES)} central and state government schemes.\n\n"
            "You could try:\n"
            "• Rephrasing with different keywords (e.g. \"student scholarship\", \"pension\", \"loan\")\n"
            "• Using the **Find Schemes** section to browse and filter all schemes\n"
            "• Asking about a specific scheme name (e.g. \"Tell me about MGNREGA\")\n"
            "• Visiting the National Government Services Portal at india.gov.in for a broader search"
        ),
        "schemes": [],
        "intent":  "not_found"
    }


@app.post("/api/chat")
def chat():
    data    = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:300]

    if not message:
        return jsonify({
            "type":    "not_found",
            "text":    "Please type a question to get started.",
            "schemes": [],
            "intent":  "empty"
        })

    result = _build_response(message)

    # Slim down schemes for the response — keep only fields the UI needs
    slim_fields = ("id", "name", "category", "audience", "summary",
                   "eligibility", "benefits", "documents", "steps", "official")
    result["schemes"] = [
        {k: s[k] for k in slim_fields if k in s}
        for s in result["schemes"]
    ]

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