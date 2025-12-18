from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("soccer.db")

@app.route("/", methods=["GET", "POST"])
def query_runner():
    selected = request.form.get("query")
    rows = []
    headers = []

    if selected in QUERIES:
        db = get_db()
        cur = db.cursor()
        cur.execute(QUERIES[selected]["sql"])
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]

    return render_template(
        "queries.html",
        queries=QUERIES,
        selected=selected,
        rows=rows,
        headers=headers
    )


QUERIES = { # populate with queries once we have them 
    "recent_games": {
        "label": "Most Recent Games",
        "sql": """
            SELECT g.game_date, ht.name, at.name, g.home_score, g.away_score
            FROM Game g
            JOIN Team ht ON g.home_team_id = ht.team_id
            JOIN Team at ON g.away_team_id = at.team_id
            ORDER BY g.game_date DESC
            LIMIT 25
        """
    },
    "highest_scoring": {
        "label": "Highest Scoring Games",
        "sql": """
            SELECT g.game_date, ht.name, at.name,
                   g.home_score + g.away_score AS total_goals
            FROM Game g
            JOIN Team ht ON g.home_team_id = ht.team_id
            JOIN Team at ON g.away_team_id = at.team_id
            ORDER BY total_goals DESC
            LIMIT 25
        """
    },
    "home_wins": {
        "label": "Home Team Wins",
        "sql": """
            SELECT g.game_date, ht.name, at.name, g.home_score, g.away_score
            FROM Game g
            JOIN Team ht ON g.home_team_id = ht.team_id
            JOIN Team at ON g.away_team_id = at.team_id
            WHERE g.home_score > g.away_score
            LIMIT 25
        """
    }
}
