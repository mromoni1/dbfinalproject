PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Conference;
CREATE TABLE Conference (
    conference_id   INTEGER PRIMARY KEY,
    conference_name VARCHAR(100),
    seo             VARCHAR(100)
);

DROP TABLE IF EXISTS University;
CREATE TABLE University (
    university_id  INTEGER PRIMARY KEY,
    name           VARCHAR(100),
    conference_id  INTEGER,
    FOREIGN KEY (conference_id)
        REFERENCES Conference(conference_id)
        ON DELETE SET NULL
);

DROP TABLE IF EXISTS Rankings;
CREATE TABLE Rankings (
    rank_week  INTEGER PRIMARY KEY,
    rank_1     VARCHAR(100),
    rank_2     VARCHAR(100),
    rank_3     VARCHAR(100),
    rank_4     VARCHAR(100),
    rank_5     VARCHAR(100),
    rank_6     VARCHAR(100),
    rank_7     VARCHAR(100),
    rank_8     VARCHAR(100),
    rank_9     VARCHAR(100),
    rank_10    VARCHAR(100),
    rank_11    VARCHAR(100),
    rank_12    VARCHAR(100),
    rank_13    VARCHAR(100),
    rank_14    VARCHAR(100),
    rank_15    VARCHAR(100),
    rank_16    VARCHAR(100),
    rank_17    VARCHAR(100),
    rank_18    VARCHAR(100),
    rank_19    VARCHAR(100),
    rank_20    VARCHAR(100),
    rank_21    VARCHAR(100),
    rank_22    VARCHAR(100),
    rank_23    VARCHAR(100),
    rank_24    VARCHAR(100),
    rank_25    VARCHAR(100)
);

DROP TABLE IF EXISTS Game;
CREATE TABLE Game (
    game_id       INTEGER PRIMARY KEY,
    home_team_id  INTEGER,
    away_team_id  INTEGER,
    home_score    INTEGER,
    away_score    INTEGER,
    location      VARCHAR(100),
    game_date     DATE,
    game_time     TIME,
    FOREIGN KEY (home_team_id)
        REFERENCES University(university_id)
        ON DELETE CASCADE,
    FOREIGN KEY (away_team_id)
        REFERENCES University(university_id)
        ON DELETE CASCADE
);

DROP TABLE IF EXISTS Player;
CREATE TABLE Player (
    player_id     INTEGER PRIMARY KEY,
    first_name    VARCHAR(50),
    last_name     VARCHAR(50),
    class_grade   VARCHAR(20),
    position      VARCHAR(20),
    university_id INTEGER,
    FOREIGN KEY (university_id)
        REFERENCES University(university_id)
        ON DELETE CASCADE
);

DROP TABLE IF EXISTS GameStats;
CREATE TABLE GameStats (
    game_id         INTEGER NOT NULL,
    player_id       INTEGER NOT NULL,

    played          BOOLEAN,
    started         BOOLEAN,

    shots           INTEGER,
    shots_on_target INTEGER,
    goals           INTEGER,
    assists         INTEGER,
    minutes         INTEGER,
    pk_attempt      INTEGER,
    pk_made         INTEGER,
    gw              BOOLEAN,
    yc              INTEGER,
    rc              INTEGER,

    PRIMARY KEY (game_id, player_id),

    FOREIGN KEY (game_id)
        REFERENCES Game(game_id)
        ON DELETE CASCADE

);


DROP VIEW IF EXISTS PlayerDerivedStats;
CREATE VIEW PlayerDerivedStats AS
SELECT 
    gs.*,
    (goals * 2 + assists) AS points,
    CASE WHEN shots > 0 THEN shots_on_target * 1.0 / shots END AS shot_pct,
    CASE WHEN shots_on_target > 0 THEN goals * 1.0 / shots_on_target END AS sog_pct
FROM GameStats gs;

DROP VIEW IF EXISTS PlayerSeasonStats;
CREATE VIEW PlayerSeasonStats AS
SELECT
    gs.player_id,
    gs.first_name,
    gs.last_name,
    gs.position,
    gs.university_id,

    COUNT(DISTINCT gs.game_id)            AS games_played,
    SUM(gs.started)                       AS games_started,
    SUM(gs.minutes)                       AS total_minutes,

    SUM(gs.goals)                         AS total_goals,
    SUM(gs.assists)                       AS total_assists,
    SUM(gs.goals * 2 + gs.assists)        AS total_points,

    SUM(gs.shots)                         AS total_shots,
    SUM(gs.shots_on_target)               AS total_sog,

    CASE
        WHEN SUM(gs.shots) > 0
        THEN 1.0 * SUM(gs.shots_on_target) / SUM(gs.shots)
    END                                   AS season_shot_pct,

    CASE
        WHEN SUM(gs.shots_on_target) > 0
        THEN 1.0 * SUM(gs.goals) / SUM(gs.shots_on_target)
    END                                   AS season_sog_pct

FROM GameStats gs
GROUP BY gs.player_id;


DROP TABLE IF EXISTS Play;
CREATE TABLE Play (
    play_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id      INTEGER NOT NULL,
    player_id    INTEGER NULL,
    event_type VARCHAR(30),
    time_of_play TIME NULL,
    description  TEXT NOT NULL,

    FOREIGN KEY (game_id)
        REFERENCES Game(game_id)
        ON DELETE CASCADE,

    FOREIGN KEY (player_id)
        REFERENCES Player(player_id)
        ON DELETE SET NULL
);


