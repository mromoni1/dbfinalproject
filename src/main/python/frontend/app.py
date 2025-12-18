from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("D3WomensSoccer.db")

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
        db.close()

    return render_template(
        "queries.html",
        queries=QUERIES,
        selected=selected,
        rows=rows,
        headers=headers
    )

QUERIES = { # same as in queries.sql
    "goals_per_minute_2025": {
        "label": "Which player scored the most goals per minute (2025 season)?",
        "sql": """
SELECT
  player_id,
  first_name,
  last_name,
  total_goals,
  total_minutes,
  1.0 * total_goals / NULLIF(total_minutes, 0) AS goals_per_minute
FROM (
  SELECT
    gs.player_id,
    p.first_name,
    p.last_name,
    SUM(gs.goals)   AS total_goals,
    SUM(gs.minutes) AS total_minutes
  FROM GameStats gs
  JOIN Game g
    ON g.game_id = gs.game_id
  JOIN Player p
    ON gs.player_id = p.player_id
  GROUP BY
    gs.player_id,
    p.first_name,
    p.last_name
)
WHERE total_minutes > 0
ORDER BY goals_per_minute DESC
LIMIT 1;

"""
    },

    "nescac_minutes_300_500": {
        "label": "Players from NESCAC universities with 300–500 total minutes",
        "sql": """
SELECT
  p.player_id,
  p.first_name,
  p.last_name,
  p.position,
  u.name AS university_name,
  SUM(gs.minutes) AS total_minutes
FROM Player p
JOIN University u ON u.university_id = p.university_id
JOIN Conference c ON c.conference_id = u.conference_id
JOIN GameStats gs ON gs.player_id = p.player_id
GROUP BY p.player_id
HAVING c.conference_name = 'NESCAC'
   AND total_minutes BETWEEN 300 AND 500
ORDER BY total_minutes DESC;
"""
    },

    "late_goals_multiple": {
        "label": "Players who scored more than once with <10 minutes remaining",
        "sql": """
SELECT
  p.player_id,
  p.first_name,
  p.last_name,
  COUNT(*) AS late_goals
FROM Play pl
JOIN Player p ON p.player_id = pl.player_id
JOIN Game g ON g.game_id = pl.game_id
WHERE pl.event_type = 'GOAL'
  AND CAST(substr(pl.time_of_play, 1, 2) AS INTEGER) >= 80
GROUP BY p.player_id
HAVING late_goals > 1
ORDER BY late_goals DESC;
"""
    },

    "uaa_vs_nescac_shutouts": {
        "label": "UAA vs NESCAC: total shutouts against non-conference opponents",
        "sql": """
WITH games_with_confs AS (
  SELECT
    g.game_id,
    g.home_team_id,
    g.away_team_id,
    g.home_score,
    g.away_score,
    ch.conference_name AS home_conf,
    ca.conference_name AS away_conf
  FROM Game g
  JOIN University uh ON uh.university_id = g.home_team_id
  JOIN University ua ON ua.university_id = g.away_team_id
  LEFT JOIN Conference ch ON ch.conference_id = uh.conference_id
  LEFT JOIN Conference ca ON ca.conference_id = ua.conference_id
),
shutouts AS (
  SELECT
    home_conf AS conf,
    CASE WHEN away_score = 0 AND home_conf != away_conf THEN 1 ELSE 0 END AS shutout_nonconf
  FROM games_with_confs
  UNION ALL
  SELECT
    away_conf AS conf,
    CASE WHEN home_score = 0 AND home_conf != away_conf THEN 1 ELSE 0 END AS shutout_nonconf
  FROM games_with_confs
)
SELECT conf, SUM(shutout_nonconf) AS total_shutouts_vs_nonconf
FROM shutouts
WHERE conf IN ('UAA', 'NESCAC')
GROUP BY conf
ORDER BY total_shutouts_vs_nonconf DESC;
"""
    },

    "away_more_than_home": {
        "label": "Teams with more away wins than home wins",
        "sql": """
WITH results AS (
  SELECT
    game_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    CASE
      WHEN home_score > away_score THEN home_team_id
      WHEN away_score > home_score THEN away_team_id
      ELSE NULL
    END AS winner_id
  FROM Game
),
home_wins AS (
  SELECT home_team_id AS university_id, COUNT(*) AS home_wins
  FROM results
  WHERE winner_id = home_team_id
  GROUP BY home_team_id
),
away_wins AS (
  SELECT away_team_id AS university_id, COUNT(*) AS away_wins
  FROM results
  WHERE winner_id = away_team_id
  GROUP BY away_team_id
)
SELECT
  u.university_id,
  u.name,
  COALESCE(aw.away_wins, 0) AS away_wins,
  COALESCE(hw.home_wins, 0) AS home_wins
FROM University u
LEFT JOIN home_wins hw ON hw.university_id = u.university_id
LEFT JOIN away_wins aw ON aw.university_id = u.university_id
WHERE COALESCE(aw.away_wins, 0) > COALESCE(hw.home_wins, 0)
ORDER BY away_wins DESC;
"""
    },

    "avg_goals_per_team": {
        "label": "Average goals per game by university",
        "sql": """
WITH team_game_goals AS (
  SELECT home_team_id AS university_id, home_score AS goals FROM Game
  UNION ALL
  SELECT away_team_id AS university_id, away_score AS goals FROM Game
)
SELECT
  u.university_id,
  u.name,
  AVG(goals * 1.0) AS avg_goals_per_game
FROM team_game_goals tgg
JOIN University u ON u.university_id = tgg.university_id
GROUP BY u.university_id
ORDER BY avg_goals_per_game DESC;
"""
    },
    "game_winning_goals": {
        "label": "Games decided by a game-winning goal and who scored it",
        "sql": """
WITH one_goal_games AS (
  SELECT *
  FROM Game
  WHERE ABS(home_score - away_score) = 1
),
goal_events AS (
  SELECT
    pl.game_id,
    pl.player_id,
    pl.time_of_play,
    ROW_NUMBER() OVER (
      PARTITION BY pl.game_id
      ORDER BY pl.time_of_play DESC
    ) AS rn
  FROM Play pl
  WHERE pl.event_type = 'GOAL'
)
SELECT
  g.game_id,
  g.game_date,
  p.player_id,
  p.first_name,
  p.last_name
FROM one_goal_games g
JOIN goal_events ge
  ON g.game_id = ge.game_id AND ge.rn = 1
JOIN Player p ON p.player_id = ge.player_id
ORDER BY g.game_date;
"""
    },

    "most_corners_oct_12": {
        "label": "Team with the most corners on October 12, 2025",
        "sql": """
SELECT
  u.university_id,
  u.name,
  COUNT(*) AS corners
FROM Play pl
JOIN Game g ON g.game_id = pl.game_id
JOIN University u ON u.university_id IN (g.home_team_id, g.away_team_id)
WHERE pl.event_type = 'CORNER'
  AND g.game_date = '2025-10-12'
GROUP BY u.university_id
ORDER BY corners DESC
LIMIT 1;
"""
    },
    "conference_total_goals": {
        "label": "Conference with the most total goals scored",
        "sql": """
WITH team_goals AS (
  SELECT home_team_id AS university_id, home_score AS goals FROM Game
  UNION ALL
  SELECT away_team_id AS university_id, away_score AS goals FROM Game
)
SELECT
  c.conference_name,
  SUM(tg.goals) AS total_goals
FROM team_goals tg
JOIN University u ON u.university_id = tg.university_id
JOIN Conference c ON c.conference_id = u.conference_id
GROUP BY c.conference_name
ORDER BY total_goals DESC;
"""
    },

    "ranked_once": {
        "label": "Teams ranked in the Top 25 at most once",
        "sql": """
WITH ranked_names AS (
  SELECT rank_week, rank_1  AS team_name FROM Rankings WHERE rank_1  IS NOT NULL UNION ALL
  SELECT rank_week, rank_2  FROM Rankings WHERE rank_2  IS NOT NULL UNION ALL
  SELECT rank_week, rank_3  FROM Rankings WHERE rank_3  IS NOT NULL UNION ALL
  SELECT rank_week, rank_4  FROM Rankings WHERE rank_4  IS NOT NULL UNION ALL
  SELECT rank_week, rank_5  FROM Rankings WHERE rank_5  IS NOT NULL UNION ALL
  SELECT rank_week, rank_6  FROM Rankings WHERE rank_6  IS NOT NULL UNION ALL
  SELECT rank_week, rank_7  FROM Rankings WHERE rank_7  IS NOT NULL UNION ALL
  SELECT rank_week, rank_8  FROM Rankings WHERE rank_8  IS NOT NULL UNION ALL
  SELECT rank_week, rank_9  FROM Rankings WHERE rank_9  IS NOT NULL UNION ALL
  SELECT rank_week, rank_10 FROM Rankings WHERE rank_10 IS NOT NULL UNION ALL
  SELECT rank_week, rank_11 FROM Rankings WHERE rank_11 IS NOT NULL UNION ALL
  SELECT rank_week, rank_12 FROM Rankings WHERE rank_12 IS NOT NULL UNION ALL
  SELECT rank_week, rank_13 FROM Rankings WHERE rank_13 IS NOT NULL UNION ALL
  SELECT rank_week, rank_14 FROM Rankings WHERE rank_14 IS NOT NULL UNION ALL
  SELECT rank_week, rank_15 FROM Rankings WHERE rank_15 IS NOT NULL UNION ALL
  SELECT rank_week, rank_16 FROM Rankings WHERE rank_16 IS NOT NULL UNION ALL
  SELECT rank_week, rank_17 FROM Rankings WHERE rank_17 IS NOT NULL UNION ALL
  SELECT rank_week, rank_18 FROM Rankings WHERE rank_18 IS NOT NULL UNION ALL
  SELECT rank_week, rank_19 FROM Rankings WHERE rank_19 IS NOT NULL UNION ALL
  SELECT rank_week, rank_20 FROM Rankings WHERE rank_20 IS NOT NULL UNION ALL
  SELECT rank_week, rank_21 FROM Rankings WHERE rank_21 IS NOT NULL UNION ALL
  SELECT rank_week, rank_22 FROM Rankings WHERE rank_22 IS NOT NULL UNION ALL
  SELECT rank_week, rank_23 FROM Rankings WHERE rank_23 IS NOT NULL UNION ALL
  SELECT rank_week, rank_24 FROM Rankings WHERE rank_24 IS NOT NULL UNION ALL
  SELECT rank_week, rank_25 FROM Rankings WHERE rank_25 IS NOT NULL
),
rank_counts AS (
  SELECT team_name, COUNT(DISTINCT rank_week) AS weeks_ranked
  FROM ranked_names
  GROUP BY team_name
)
SELECT team_name
FROM rank_counts
WHERE weeks_ranked <= 1
ORDER BY team_name;
"""
    },

    "latest_goal_each_game": {
        "label": "Player who scored the latest goal in each game",
        "sql": """
SELECT
  pl.game_id,
  p.player_id,
  p.first_name,
  p.last_name,
  MAX(pl.time_of_play) AS latest_goal_time
FROM Play pl
JOIN Player p ON p.player_id = pl.player_id
WHERE pl.event_type = 'GOAL'
GROUP BY pl.game_id;
"""
    }, 
    "most_minutes_played": {
    "label": "Players with the most total minutes played",
    "sql": """
SELECT
  gs.player_id,
  u.name AS university_name,
  SUM(gs.minutes) AS total_minutes
FROM GameStats gs
JOIN Player p ON gs.player_id = p.player_id
JOIN University u ON u.university_id = p.university_id
GROUP BY gs.player_id
ORDER BY total_minutes DESC
LIMIT 10;
"""
}, 
}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
