"""
Flask Application – Intelligent Athletic Performance Tracker

All database access uses raw parameterised SQL via psycopg2
(no ORM). Routes:

  /                       – Dashboard (4-table JOIN)
  /athletes               – Athlete list
  /add_athlete             – Create athlete  (GET form / POST insert)
  /edit_athlete/<id>       – Edit athlete    (GET form / POST update)
  /delete_athlete/<id>     – Delete athlete  (POST)
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash
)
from psycopg2 import OperationalError

from config import Config
from db import get_db_cursor, check_health

# ─────────────────────────────────────────────
# App Factory
# ─────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY


# ─────────────────────────────────────────────
# Context processor – inject DB health into every template
# ─────────────────────────────────────────────

@app.context_processor
def inject_db_health():
    """Make db_health available in all templates for the status banner."""
    return {"db_health": check_health()}


# ─────────────────────────────────────────────
# READ (Complex) – Dashboard with 4-Table JOIN
# ─────────────────────────────────────────────

DASHBOARD_QUERY = """
SELECT
    ws.set_id,
    a.athlete_id,
    a.name          AS athlete_name,
    ts.session_id,
    ts.date         AS session_date,
    ts.session_type,
    ts.duration     AS session_duration,
    e.exercise_id,
    e.name          AS exercise_name,
    e.muscle_group,
    e.mechanics,
    ws.weight,
    ws.reps,
    ws.rpe,
    ROUND(ws.weight * ws.reps, 2) AS volume_load
FROM WorkoutSets ws
JOIN TrainingSessions ts ON ws.session_id  = ts.session_id
JOIN Athletes a          ON ts.athlete_id  = a.athlete_id
JOIN Exercises e         ON ws.exercise_id = e.exercise_id
ORDER BY ts.date DESC, ws.set_id DESC;
"""

STATS_QUERY = """
SELECT
    COUNT(*)                                   AS total_sets,
    COALESCE(ROUND(SUM(weight * reps), 0), 0)  AS total_volume,
    COALESCE(ROUND(AVG(rpe), 1), 0)            AS avg_rpe
FROM WorkoutSets;
"""

ATHLETE_COUNT_QUERY = "SELECT COUNT(*) FROM Athletes;"

SESSIONS_QUERY = """
SELECT 
    ts.session_id,
    a.athlete_id,
    a.name          AS athlete_name,
    ts.date         AS session_date,
    ts.session_type,
    ts.duration,
    COUNT(ws.set_id) AS total_sets,
    COALESCE(ROUND(SUM(ws.weight * ws.reps), 0), 0) AS total_volume
FROM TrainingSessions ts
JOIN Athletes a ON ts.athlete_id = a.athlete_id
LEFT JOIN WorkoutSets ws ON ts.session_id = ws.session_id
GROUP BY ts.session_id, a.athlete_id, a.name, ts.date, ts.session_type, ts.duration
ORDER BY ts.date DESC, ts.session_id DESC;
"""

RECOVERY_QUERY = """
SELECT 
    r.recovery_id,
    a.athlete_id,
    a.name          AS athlete_name,
    r.date          AS recovery_date,
    r.sleep_hours,
    r.soreness_level
FROM RecoveryLogs r
JOIN Athletes a ON r.athlete_id = a.athlete_id
ORDER BY r.date DESC, r.recovery_id DESC;
"""


@app.route("/")
def dashboard():
    """Render the main performance dashboard with 4-table join and KPI metrics."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(DASHBOARD_QUERY)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]

            cur.execute(STATS_QUERY)
            stats_row = cur.fetchone()
            stats = {
                "total_sets": stats_row[0],
                "total_volume": stats_row[1],
                "avg_rpe": stats_row[2],
            }

            cur.execute(ATHLETE_COUNT_QUERY)
            stats["athlete_count"] = cur.fetchone()[0]

        return render_template("index.html", rows=rows, stats=stats)

    except OperationalError:
        flash("⚠️ Database is currently unavailable. Please check the connection.", "error")
        return render_template(
            "index.html",
            rows=[],
            stats={"total_sets": 0, "total_volume": 0, "avg_rpe": 0, "athlete_count": 0},
        )


@app.route("/workouts")
def workouts():
    """Standalone page displaying all workout sets with 4-table join details."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(DASHBOARD_QUERY)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return render_template("workouts.html", workouts=rows)
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return render_template("workouts.html", workouts=[])


@app.route("/sessions")
def sessions():
    """Standalone page displaying Training Sessions table."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(SESSIONS_QUERY)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return render_template("sessions.html", sessions=rows)
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return render_template("sessions.html", sessions=[])


@app.route("/recovery")
def recovery():
    """Standalone page displaying Recovery Logs table."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(RECOVERY_QUERY)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return render_template("recovery.html", recovery_logs=rows)
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return render_template("recovery.html", recovery_logs=[])


@app.route("/log_recovery", methods=["GET", "POST"])
def log_recovery():
    """Add or update an athlete's recovery log (enforces strictly 1 entry per athlete)."""
    from datetime import date
    today_str = date.today().isoformat()

    if request.method == "POST":
        athlete_id_str = request.form.get("athlete_id", "").strip()
        date_str = request.form.get("date", "").strip() or today_str
        sleep_hours_str = request.form.get("sleep_hours", "").strip()
        soreness_level_str = request.form.get("soreness_level", "").strip()

        if not athlete_id_str or not sleep_hours_str or not soreness_level_str:
            flash("All fields are required to log recovery.", "error")
            return redirect(url_for("log_recovery", athlete_id=athlete_id_str))

        try:
            athlete_id = int(athlete_id_str)
            sleep_hours = float(sleep_hours_str)
            soreness_level = int(soreness_level_str)

            if not (0.0 <= sleep_hours <= 24.0):
                flash("Sleep hours must be between 0.0 and 24.0.", "error")
                return redirect(url_for("log_recovery", athlete_id=athlete_id))

            if not (1 <= soreness_level <= 10):
                flash("Soreness level must be between 1 and 10.", "error")
                return redirect(url_for("log_recovery", athlete_id=athlete_id))

        except ValueError:
            flash("Invalid numeric value for sleep or soreness.", "error")
            return redirect(url_for("log_recovery", athlete_id=athlete_id_str))

        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT name FROM Athletes WHERE athlete_id = %s;", (athlete_id,))
                ath_row = cur.fetchone()
                athlete_name = ath_row[0] if ath_row else f"Athlete #{athlete_id}"

                upsert_query = """
                INSERT INTO RecoveryLogs (athlete_id, date, sleep_hours, soreness_level)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (athlete_id) DO UPDATE
                SET date = EXCLUDED.date,
                    sleep_hours = EXCLUDED.sleep_hours,
                    soreness_level = EXCLUDED.soreness_level
                RETURNING recovery_id, (xmax = 0) AS was_inserted;
                """
                cur.execute(upsert_query, (athlete_id, date_str, sleep_hours, soreness_level))
                res = cur.fetchone()
                rec_id, was_inserted = res[0], res[1]

            if was_inserted:
                flash(f"✅ Recovery log recorded for {athlete_name} (ID #{rec_id}).", "success")
            else:
                flash(f"🔄 Recovery log updated for {athlete_name} (Single profile maintained, ID #{rec_id}).", "success")

            return redirect(url_for("recovery"))

        except OperationalError as exc:
            flash(f"Database error while saving recovery log: {exc}", "error")
            return redirect(url_for("log_recovery", athlete_id=athlete_id))

    # GET request
    selected_athlete_id = request.args.get("athlete_id", "").strip()
    try:
        selected_athlete_id = int(selected_athlete_id) if selected_athlete_id else None
    except ValueError:
        selected_athlete_id = None

    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT athlete_id, name FROM Athletes ORDER BY name ASC;")
            athletes = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

            cur.execute("SELECT recovery_id, athlete_id, date, sleep_hours, soreness_level FROM RecoveryLogs;")
            existing_logs = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]
            existing_map = {}
            for log in existing_logs:
                aid = log["athlete_id"]
                existing_map[aid] = {
                    "recovery_id": log["recovery_id"],
                    "date": str(log["date"]),
                    "sleep_hours": float(log["sleep_hours"]),
                    "soreness_level": int(log["soreness_level"])
                }

            selected_recovery = existing_map.get(selected_athlete_id, {})

        return render_template(
            "recovery_form.html",
            athletes=athletes,
            existing_map=existing_map,
            selected_athlete_id=selected_athlete_id,
            selected_recovery=selected_recovery,
            today=today_str,
        )
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return redirect(url_for("recovery"))


@app.route("/delete_recovery/<int:recovery_id>", methods=["POST"])
def delete_recovery(recovery_id):
    """Delete a recovery record (allows resetting an athlete's recovery status)."""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                DELETE FROM RecoveryLogs 
                WHERE recovery_id = %s 
                RETURNING athlete_id;
            """, (recovery_id,))
            deleted = cur.fetchone()
            if deleted:
                cur.execute("SELECT name FROM Athletes WHERE athlete_id = %s;", (deleted[0],))
                ath_row = cur.fetchone()
                name = ath_row[0] if ath_row else f"Athlete #{deleted[0]}"
                flash(f"🗑️ Recovery log for {name} removed.", "success")
            else:
                flash("Recovery log not found.", "error")
    except OperationalError as exc:
        flash(f"Error deleting recovery log: {exc}", "error")

    return redirect(url_for("recovery"))


# ─────────────────────────────────────────────
# READ (Simple) – All Athletes
# ─────────────────────────────────────────────

@app.route("/athletes")
def athletes():
    """List every athlete with edit/delete actions."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT * FROM Athletes ORDER BY athlete_id ASC;")
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return render_template("athletes.html", athletes=rows)

    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return render_template("athletes.html", athletes=[])


# ─────────────────────────────────────────────
# CREATE – Add Athlete
# ─────────────────────────────────────────────

@app.route("/add_athlete", methods=["GET", "POST"])
def add_athlete():
    """GET → show form; POST → INSERT new athlete."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        height = request.form.get("height", "").strip()
        weight = request.form.get("weight", "").strip()

        if not name or not height or not weight:
            flash("All fields are required.", "error")
            return render_template("athlete_form.html", action="Add", athlete=request.form)

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO Athletes (name, height, weight) "
                    "VALUES (%s, %s, %s) RETURNING athlete_id;",
                    (name, float(height), float(weight)),
                )
                new_id = cur.fetchone()[0]
            flash(f'✅ Athlete "{name}" created (ID #{new_id}).', "success")
            return redirect(url_for("athletes"))

        except (OperationalError, ValueError) as exc:
            flash(f"Error creating athlete: {exc}", "error")
            return render_template("athlete_form.html", action="Add", athlete=request.form)

    return render_template("athlete_form.html", action="Add", athlete={})


# ─────────────────────────────────────────────
# UPDATE – Edit Athlete
# ─────────────────────────────────────────────

@app.route("/edit_athlete/<int:athlete_id>", methods=["GET", "POST"])
def edit_athlete(athlete_id):
    """GET → load current data into form; POST → UPDATE row."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        height = request.form.get("height", "").strip()
        weight = request.form.get("weight", "").strip()

        if not name or not height or not weight:
            flash("All fields are required.", "error")
            return render_template("athlete_form.html", action="Edit", athlete=request.form)

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE Athletes SET name = %s, height = %s, weight = %s "
                    "WHERE athlete_id = %s;",
                    (name, float(height), float(weight), athlete_id),
                )
            flash(f'✅ Athlete "{name}" updated.', "success")
            return redirect(url_for("athletes"))

        except (OperationalError, ValueError) as exc:
            flash(f"Error updating athlete: {exc}", "error")
            return render_template("athlete_form.html", action="Edit", athlete=request.form)

    # GET – fetch current athlete data
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT * FROM Athletes WHERE athlete_id = %s;", (athlete_id,))
            row = cur.fetchone()
            if not row:
                flash("Athlete not found.", "error")
                return redirect(url_for("athletes"))
            columns = [desc[0] for desc in cur.description]
            athlete = dict(zip(columns, row))
        return render_template("athlete_form.html", action="Edit", athlete=athlete)

    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return redirect(url_for("athletes"))


# ─────────────────────────────────────────────
# DELETE – Remove Athlete
# ─────────────────────────────────────────────

@app.route("/delete_athlete/<int:athlete_id>", methods=["POST"])
def delete_athlete(athlete_id):
    """DELETE the athlete and cascade-remove related records."""
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "DELETE FROM Athletes WHERE athlete_id = %s RETURNING name;",
                (athlete_id,),
            )
            deleted = cur.fetchone()
            if deleted:
                flash(f'🗑️ Athlete "{deleted[0]}" deleted.', "success")
            else:
                flash("Athlete not found.", "error")
    except OperationalError as exc:
        flash(f"Error deleting athlete: {exc}", "error")

    return redirect(url_for("athletes"))


# ─────────────────────────────────────────────
# EXERCISES CRUD
# ─────────────────────────────────────────────

@app.route("/exercises")
def exercises():
    """List every exercise with edit/delete actions."""
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT * FROM Exercises ORDER BY exercise_id ASC;")
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        return render_template("exercises.html", exercises=rows)
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return render_template("exercises.html", exercises=[])


@app.route("/add_exercise", methods=["GET", "POST"])
def add_exercise():
    """GET → show form; POST → INSERT new exercise."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        muscle_group = request.form.get("muscle_group", "").strip()
        mechanics = request.form.get("mechanics", "").strip()

        if not name or not muscle_group or not mechanics:
            flash("All fields are required.", "error")
            return render_template("exercise_form.html", action="Add", exercise=request.form)

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO Exercises (name, muscle_group, mechanics) "
                    "VALUES (%s, %s, %s) RETURNING exercise_id;",
                    (name, muscle_group, mechanics),
                )
                new_id = cur.fetchone()[0]
            flash(f'✅ Exercise "{name}" added (ID #{new_id}).', "success")
            return redirect(url_for("exercises"))
        except OperationalError as exc:
            flash(f"Error creating exercise: {exc}", "error")
            return render_template("exercise_form.html", action="Add", exercise=request.form)

    return render_template("exercise_form.html", action="Add", exercise={})


@app.route("/edit_exercise/<int:exercise_id>", methods=["GET", "POST"])
def edit_exercise(exercise_id):
    """GET → load current data into form; POST → UPDATE exercise."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        muscle_group = request.form.get("muscle_group", "").strip()
        mechanics = request.form.get("mechanics", "").strip()

        if not name or not muscle_group or not mechanics:
            flash("All fields are required.", "error")
            return render_template("exercise_form.html", action="Edit", exercise=request.form)

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE Exercises SET name = %s, muscle_group = %s, mechanics = %s "
                    "WHERE exercise_id = %s;",
                    (name, muscle_group, mechanics, exercise_id),
                )
            flash(f'✅ Exercise "{name}" updated.', "success")
            return redirect(url_for("exercises"))
        except OperationalError as exc:
            flash(f"Error updating exercise: {exc}", "error")
            return render_template("exercise_form.html", action="Edit", exercise=request.form)

    # GET – fetch current exercise data
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT * FROM Exercises WHERE exercise_id = %s;", (exercise_id,))
            row = cur.fetchone()
            if not row:
                flash("Exercise not found.", "error")
                return redirect(url_for("exercises"))
            columns = [desc[0] for desc in cur.description]
            exercise = dict(zip(columns, row))
        return render_template("exercise_form.html", action="Edit", exercise=exercise)
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return redirect(url_for("exercises"))


@app.route("/delete_exercise/<int:exercise_id>", methods=["POST"])
def delete_exercise(exercise_id):
    """DELETE the exercise and cascade-remove related sets."""
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "DELETE FROM Exercises WHERE exercise_id = %s RETURNING name;",
                (exercise_id,),
            )
            deleted = cur.fetchone()
            if deleted:
                flash(f'🗑️ Exercise "{deleted[0]}" deleted.', "success")
            else:
                flash("Exercise not found.", "error")
    except OperationalError as exc:
        flash(f"Error deleting exercise: {exc}", "error")

    return redirect(url_for("exercises"))


# ─────────────────────────────────────────────
# WORKOUT LOGGING (TrainingSessions & WorkoutSets)
# ─────────────────────────────────────────────

@app.route("/log_workout", methods=["GET", "POST"])
def log_workout():
    """Log a workout session and set directly from the website."""
    from datetime import date

    if request.method == "POST":
        athlete_id = request.form.get("athlete_id", "").strip()
        session_date = request.form.get("date", "").strip() or str(date.today())
        session_type = request.form.get("session_type", "").strip()
        duration = request.form.get("duration", "60").strip()
        exercise_id = request.form.get("exercise_id", "").strip()
        weight = request.form.get("weight", "0").strip()
        reps = request.form.get("reps", "").strip()
        rpe = request.form.get("rpe", "7").strip()

        if not athlete_id or not exercise_id or not reps:
            flash("Please fill in athlete, exercise, and reps.", "error")
            return redirect(url_for("log_workout"))

        try:
            with get_db_cursor() as cur:
                # 1. Check if athlete already has a TrainingSession on this date & session_type
                cur.execute(
                    "SELECT session_id FROM TrainingSessions "
                    "WHERE athlete_id = %s AND date = %s AND session_type = %s "
                    "ORDER BY session_id DESC LIMIT 1;",
                    (int(athlete_id), session_date, session_type),
                )
                existing = cur.fetchone()

                if existing:
                    session_id = existing[0]
                    is_new_session = False
                else:
                    # Create a new session if one does not exist for this date and type
                    cur.execute(
                        "INSERT INTO TrainingSessions (athlete_id, date, session_type, duration) "
                        "VALUES (%s, %s, %s, %s) RETURNING session_id;",
                        (int(athlete_id), session_date, session_type, int(duration)),
                    )
                    session_id = cur.fetchone()[0]
                    is_new_session = True

                # 2. Insert the WorkoutSet linked to that session_id
                cur.execute(
                    "INSERT INTO WorkoutSets (session_id, exercise_id, weight, reps, rpe) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING set_id;",
                    (session_id, int(exercise_id), float(weight), int(reps), int(rpe)),
                )
                set_id = cur.fetchone()[0]

            if is_new_session:
                flash(f"⚡ New training session #{session_id} created & Set #{set_id} logged!", "success")
            else:
                flash(f"⚡ Set #{set_id} automatically grouped into existing {session_type} session #{session_id}!", "success")

            return redirect(url_for("dashboard"))
        except OperationalError as exc:
            flash(f"Error logging workout: {exc}", "error")
            return redirect(url_for("log_workout"))

    # GET – Fetch athletes and exercises dropdown options
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT athlete_id, name FROM Athletes ORDER BY name ASC;")
            athletes_list = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

            cur.execute("SELECT exercise_id, name, muscle_group, mechanics FROM Exercises ORDER BY name ASC;")
            exercises_list = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

        return render_template(
            "log_workout.html",
            athletes=athletes_list,
            exercises=exercises_list,
            today=str(date.today()),
        )
    except OperationalError:
        flash("⚠️ Database is currently unavailable.", "error")
        return redirect(url_for("dashboard"))


@app.route("/delete_set/<int:set_id>", methods=["POST"])
def delete_set(set_id):
    """Delete a workout set from the dashboard."""
    try:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM WorkoutSets WHERE set_id = %s;", (set_id,))
        flash(f"🗑️ Workout set #{set_id} deleted.", "success")
    except OperationalError as exc:
        flash(f"Error deleting set: {exc}", "error")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
# SQL QUERY STUDIO (Interactive Query Console)
# ─────────────────────────────────────────────

@app.route("/query", methods=["GET", "POST"])
def query_console():
    """Interactive SQL query execution page."""
    import time

    session_id = request.args.get("session_id", "").strip()
    query_sql = request.form.get("query_sql", "").strip() if request.method == "POST" else ""
    should_run = request.method == "POST" and bool(query_sql)

    default_query = """SELECT 
    a.name AS athlete, 
    ts.session_type, 
    e.name AS exercise, 
    ws.weight, 
    ws.reps, 
    ws.rpe, 
    ROUND(ws.weight * ws.reps, 2) AS volume_kg
FROM WorkoutSets ws
JOIN TrainingSessions ts ON ws.session_id = ts.session_id
JOIN Athletes a ON ts.athlete_id = a.athlete_id
JOIN Exercises e ON ws.exercise_id = e.exercise_id
ORDER BY ws.set_id DESC
LIMIT 15;"""

    # If clicked from a Training Session, load the specific session query and auto-run
    if session_id and request.method == "GET":
        try:
            sid = int(session_id)
            query_sql = f"""SELECT 
    ws.set_id,
    a.name AS athlete_name,
    ts.date AS session_date,
    ts.session_type,
    ts.duration AS session_duration_min,
    e.name AS exercise_name,
    e.muscle_group,
    e.mechanics,
    ws.weight AS weight_kg,
    ws.reps,
    ws.rpe,
    ROUND(ws.weight * ws.reps, 2) AS volume_kg
FROM WorkoutSets ws
JOIN TrainingSessions ts ON ws.session_id = ts.session_id
JOIN Athletes a ON ts.athlete_id = a.athlete_id
JOIN Exercises e ON ws.exercise_id = e.exercise_id
WHERE ts.session_id = {sid}
ORDER BY ws.set_id ASC;"""
            should_run = True
        except ValueError:
            query_sql = default_query

    elif not query_sql and request.method == "GET":
        query_sql = default_query

    result = {
        "columns": [],
        "rows": [],
        "row_count": 0,
        "execution_time_ms": 0,
        "is_select": False,
        "message": None,
        "error": None,
        "has_run": False,
        "filtered_session_id": session_id if session_id else None,
    }

    if should_run and query_sql:
        result["has_run"] = True
        start_time = time.time()
        try:
            with get_db_cursor() as cur:
                cur.execute(query_sql)
                duration = round((time.time() - start_time) * 1000, 2)
                result["execution_time_ms"] = duration

                if cur.description:
                    result["is_select"] = True
                    result["columns"] = [desc[0] for desc in cur.description]
                    result["rows"] = cur.fetchall()
                    result["row_count"] = len(result["rows"])
                else:
                    result["is_select"] = False
                    result["row_count"] = cur.rowcount
                    result["message"] = f"Query executed successfully ({cur.rowcount} row(s) affected)."
        except Exception as exc:
            result["error"] = str(exc)

    return render_template("query.html", query_sql=query_sql, result=result)


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5050))
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=port)
