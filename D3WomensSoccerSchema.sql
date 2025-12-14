DROP TABLE IF EXISTS Player;
CREATE TABLE Player (
    player_id      INT PRIMARY KEY,
    first_name     VARCHAR(50),
    last_name      VARCHAR(50),
    class_grade    VARCHAR(20), -- may change based on what API returns
    position       VARCHAR(20),
    university_id  INT,
    FOREIGN KEY (university_id) REFERENCES University(university_id)
);

DROP TABLE IF EXISTS University;
CREATE TABLE University (
    university_id  INT PRIMARY KEY,
    name           VARCHAR(100),
    city           VARCHAR(100),
    state          VARCHAR(2),
    conference_id  INT,
    FOREIGN KEY (conference_id) REFERENCES Conference(conference_id)
);

DROP TABLE IF EXISTS Conference;
CREATE TABLE Conference (
    conference_id  INT PRIMARY KEY,
    region         VARCHAR(50),
    school         VARCHAR(100)
);

DROP TABLE IF EXISTS Game;
CREATE TABLE Game (
    game_id       INT PRIMARY KEY,
    home_team_id  INT,
    away_team_id  INT,
    home_score    INT,
    away_score    INT,
    location      VARCHAR(100),
    game_date     DATE,
    game_time     TIME,
    FOREIGN KEY (home_team_id) REFERENCES University(university_id),
    FOREIGN KEY (away_team_id) REFERENCES University(university_id)
);

DROP TABLE IF EXISTS GameStats;
CREATE TABLE GameStats (
    game_id          INT,
    player_id        INT,
    played           BOOLEAN,
    started          BOOLEAN,
    shots            INT,
    shots_on_target  INT,
    goals            INT,
    assists          INT,
    minutes          INT,
    pk_attempt       INT,
    pk_made          INT,
    gw               BOOLEAN,
    yc               INT,
    rc               INT,
    PRIMARY KEY (game_id, player_id),
    FOREIGN KEY (game_id) REFERENCES Game(game_id),
    FOREIGN KEY (player_id) REFERENCES Player(player_id)
);

CREATE VIEW PlayerDerivedStats AS
SELECT 
    gs.*,
    (goals*2 + assists) AS points,
    CASE WHEN shots > 0 THEN shots_on_target * 1.0 / shots ELSE NULL END AS shot_pct,
    CASE WHEN shots_on_target > 0 THEN goals * 1.0 / shots_on_target ELSE NULL END AS sog_pct
FROM GameStats gs;

DROP TABLE IF EXISTS Champion_History;
CREATE TABLE Champion_History (
    season_id      INT,
    university_id  INT,
    PRIMARY KEY (season_id, university_id),
    FOREIGN KEY (university_id) REFERENCES University(university_id)
);

DROP TABLE IF EXISTS Rankings;
CREATE TABLE Rankings (
    rank_week  INT PRIMARY KEY,
    rank_1     VARCHAR(100),
    rank_2     VARCHAR(100),
    rank_3     VARCHAR(100),
    rank_4     VARCHAR(100),
    rank_5     VARCHAR(100)
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
    rank_25    VARCHAR(100),
);

DROP TABLE IF EXISTS Play;
CREATE TABLE Play (
    play_id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    game_id          INT,
    player_id        INT,
    time_of_play     TIME,          
    description VARCHAR(255),
    FOREIGN KEY (player_id) REFERENCES Player(player_id),
    FOREIGN KEY (game_id) REFERENCES Game(game_id)
);