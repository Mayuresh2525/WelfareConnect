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
    audience = request.args.get("audience", "All")

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

        if audience != "All" and s["audience"] != audience:
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