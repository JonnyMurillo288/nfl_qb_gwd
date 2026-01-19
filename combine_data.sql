CREATE TEMP TABLE suc_gwd_by_qb AS
WITH late_slice AS (
    -- only used to define eligible drives + start/end within last 180s
    SELECT
        game_id,
        pos_team,
        drive,
        game_seconds_remaining,
        score_differential_post,
        week
    FROM pbp_data_1999_2025
    WHERE game_seconds_remaining <= 180
      AND week >= 19
), drive_bounds AS (
    -- drive boundaries within last 180s
    SELECT
        game_id,
        pos_team,
        drive,
        MAX(game_seconds_remaining) AS start_t,
        MIN(game_seconds_remaining) AS end_t
    FROM late_slice
    GROUP BY game_id, pos_team, drive
),-- Assign ONE QB per (game_id, drive, pos_team) using the FULL drive (not just last 180s)
drive_qb AS (
    SELECT
        game_id,
        pos_team,
        drive,
        passer_player_name
    FROM (
        SELECT
            game_id,
            pos_team,
            drive,
            passer_player_name,
            COUNT(*) AS n,
            ROW_NUMBER() OVER (
                PARTITION BY game_id, pos_team, drive
                ORDER BY COUNT(*) DESC, passer_player_name
            ) AS rn
        FROM pbp_data_1999_2025
        WHERE week >= 19
          AND passer_player_name IS NOT NULL
        GROUP BY game_id, pos_team, drive, passer_player_name
    ) x
    WHERE rn = 1
), gwd_attempts AS (
    -- build drive-level attempts using last-180s start/end scores,
    -- but QB from full-drive assignment above
    SELECT
        b.game_id,
        b.pos_team,
        b.drive,
        qb.passer_player_name,
        s.score_differential_post AS start_score,
        e.score_differential_post AS end_score,
        b.end_t
    FROM drive_bounds b
    JOIN late_slice s
      ON s.game_id = b.game_id
     AND s.pos_team = b.pos_team
     AND s.drive = b.drive
     AND s.game_seconds_remaining = b.start_t
    JOIN late_slice e
      ON e.game_id = b.game_id
     AND e.pos_team = b.pos_team
     AND e.drive = b.drive
     AND e.game_seconds_remaining = b.end_t
    LEFT JOIN drive_qb qb
      ON qb.game_id = b.game_id
     AND qb.pos_team = b.pos_team
     AND qb.drive = b.drive
    WHERE s.score_differential_post BETWEEN -8 AND 0
      AND qb.passer_player_name IS NOT NULL
),gwd_labeled AS (
    SELECT
        *,
        CASE
            WHEN start_score <= 0 AND end_score > 0 THEN 1
            WHEN start_score < 0 AND end_score = 0 THEN 1
            ELSE 0
        END AS successful_gwd
    FROM gwd_attempts
),-- last GWD attempt per QB-game by time (end_t smallest = latest)
qb_last_gwd AS (
    SELECT
        game_id,
        passer_player_name,
        pos_team,
        successful_gwd,
        ROW_NUMBER() OVER (
            PARTITION BY game_id, passer_player_name
            ORDER BY end_t ASC
        ) AS rn
    FROM gwd_labeled
),qb_last_gwd_only AS (
    SELECT
        game_id,
        passer_player_name,
        pos_team,
        successful_gwd
    FROM qb_last_gwd
    WHERE rn = 1
),-- game results (one row per game) - do NOT rely on joining to a specific "final play" row
game_results AS (
    SELECT
        game_id,
        MAX(home_team) AS home_team,
        MAX(away_team) AS away_team,
        MAX(result) AS result
    FROM pbp_data_1999_2025
    WHERE week >= 19
    GROUP BY game_id
),team_game_outcomes AS (
    SELECT
        game_id,
        home_team AS team,
        CASE WHEN result > 0 THEN 1 ELSE 0 END AS game_won
    FROM game_results
    UNION ALL
    SELECT
        game_id,
        away_team AS team,
        CASE WHEN result < 0 THEN 1 ELSE 0 END AS game_won
    FROM game_results
), -- drive-level QB stats
drive_level AS (
    SELECT
        passer_player_name,
        COUNT(*) AS total_gwd_attempts,
        SUM(successful_gwd) AS successful_gwd_attempts
    FROM gwd_labeled
    GROUP BY passer_player_name
),-- game-level: had at least one attempt
games_with_attempt AS (
    SELECT DISTINCT
        game_id,
        passer_player_name,
        pos_team
    FROM gwd_labeled
), attempt_game_level AS (
    SELECT
        a.passer_player_name,
        COUNT(DISTINCT a.game_id) AS games_with_gwd_attempt,
        COUNT(DISTINCT CASE WHEN tgo.game_won = 1 THEN a.game_id END) AS games_won_with_gwd_attempt
    FROM games_with_attempt a
    LEFT JOIN team_game_outcomes tgo
      ON a.game_id = tgo.game_id
     AND a.pos_team = tgo.team
    GROUP BY a.passer_player_name
),-- game-level: last attempt successful + did they win
success_game_level AS (
    SELECT
        lg.passer_player_name,
        COUNT(DISTINCT CASE WHEN lg.successful_gwd = 1 THEN lg.game_id END) AS games_with_successful_gwd,
        COUNT(DISTINCT CASE WHEN lg.successful_gwd = 1 AND tgo.game_won = 1 THEN lg.game_id END) AS games_won_after_successful_gwd
    FROM qb_last_gwd_only lg
    LEFT JOIN team_game_outcomes tgo
      ON lg.game_id = tgo.game_id
     AND lg.pos_team = tgo.team
    GROUP BY lg.passer_player_name
) SELECT
    d.passer_player_name,

    d.total_gwd_attempts,
    d.successful_gwd_attempts,
    d.successful_gwd_attempts::float / NULLIF(d.total_gwd_attempts, 0) AS pct_successful_gwd,

    a.games_with_gwd_attempt,
    a.games_won_with_gwd_attempt,
    a.games_won_with_gwd_attempt::float / NULLIF(a.games_with_gwd_attempt, 0) AS pct_won_when_gwd_attempt,

    s.games_with_successful_gwd,
    s.games_won_after_successful_gwd,
    s.games_won_after_successful_gwd::float / NULLIF(s.games_with_successful_gwd, 0) AS pct_won_after_successful_gwd

FROM drive_level d
LEFT JOIN attempt_game_level a
  ON d.passer_player_name = a.passer_player_name
LEFT JOIN success_game_level s
  ON d.passer_player_name = s.passer_player_name
ORDER BY pct_successful_gwd DESC;