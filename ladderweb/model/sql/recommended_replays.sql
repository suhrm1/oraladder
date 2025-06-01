create or replace view recommended_replays as
with cte_confidence as (
	select 0 as low,  10 as high, 800 as delta
	union
	select 11 as low, 20 as high, 600 as delta
	union
	select 21 as low, 40 as high, 400 as delta
	union
	select 41 as low, 60 as high, 200 as delta
	union
	select 61 as low, 99999 as high, 0 as delta
),
cte_ranking as (
	select r.profile_id, r.`mod`, min(s.`start`) as r_start, MAX(s.end) as r_end, AVG(r.rating) as avg_rating, SUM(r.wins + r.losses) as games
	FROM ranking r
	JOIN season s ON (
		s.id=r.season_id
		AND r.`mod`=s.`mod`
		AND s.start>=(CURRENT_DATE - INTERVAL '18' month))
	WHERE r.eligible =1 and s.algorithm='openskill'
	GROUP BY r.profile_id, r.`mod`
),
cte_player AS (
	select distinct profile_id, profile_name
	from accounts where banned<>1
),
cte_player_skill AS (
	select
		r.`mod`,
		p.profile_name as name,
		r.profile_id,
		r.avg_rating as rating_base,
		c.delta * 2 as confidence_interval,
		r.avg_rating - c.delta as rating_low,
		r.avg_rating + c.delta as rating_high
	from cte_ranking r
	join cte_player p using (profile_id)
	join cte_confidence c
	on (r.games>=c.low and r.games<c.high)
)
, cte_games AS (
	select
		g.mod,
		g.map_title,
		case when profile_id0<profile_id1 then profile_id0 else profile_id1 end as p1_id,
		case when profile_id0>profile_id1 then profile_id0 else profile_id1 end as p2_id,
		date(g.start_time) as game_date,
		TIMESTAMP(g.start_time) as start_time,
		/* TIMESTAMP(g.end_time) as end_time, */
		TIMEDIFF(TIMESTAMP(g.end_time),TIMESTAMP(g.start_time)) as duration,
		g.hash
	FROM game g
),
cte_gbase AS (
	select
		g.*
		, p1.name as p1_name, p1.rating_base as p1_rating, p1.confidence_interval as p1_confidence_interval
		, p2.name as p2_name, p2.rating_base as p2_rating, p2.confidence_interval as p2_confidence_interval
	from cte_games g
	join cte_player_skill p1 on (g.p1_id=p1.profile_id)
	join cte_player_skill p2 on (g.p2_id=p2.profile_id)
),
cte_game_metrics AS (
	select *
	 , ((p1_rating + p2_rating)/2) avg_base_rating
	 , abs(p1_rating-p2_rating) as skill_diff
	 , abs(p1_rating-p2_rating)/((p1_rating + p2_rating)/2) as skill_diff_normalized
	 , abs(p1_confidence_interval + p2_confidence_interval)/((p1_rating + p2_rating)/2) as confidence_normalized
	 , abs(p1_rating-p2_rating)/((p1_rating + p2_rating)/2) + ((abs(p1_confidence_interval + p2_confidence_interval)/((p1_rating + p2_rating)/2))/3) as pairing_score
	from cte_gbase
),
cte_game_masked AS (
	select
		`mod`
		, game_date
		, start_time
		, `hash` as game_hash
		, map_title
		, p1_id
		, p1_name
		, p2_id
		, p2_name
		, CASE WHEN duration>=SEC_TO_TIME(FLOOR(14+(RAND()*12)%12)*60) THEN 'very long' ELSE
			CASE WHEN duration>=SEC_TO_TIME(FLOOR(9+(RAND()*10)%14)*60) THEN 'long' ELSE
			CASE WHEN duration>=SEC_TO_TIME(FLOOR(7+(RAND()*10)%7)*60) THEN 'average' ELSE
			CASE WHEN duration>=SEC_TO_TIME(FLOOR(4+(RAND()*10)%3)*60) THEN 'short' ELSE
			'extremely short'
		END END END END as game_length
		, CASE
			WHEN pairing_score<=0.1 THEN 1
			ELSE CASE WHEN pairing_score<=0.2 THEN 2
			ELSE CASE WHEN pairing_score<=0.3 THEN 3
			ELSE CASE WHEN pairing_score<=0.5 THEN 4
			ELSE CASE WHEN pairing_score<=0.9 THEN 5
			END END END END END
			AS rivalry_grade
		, CASE WHEN avg_base_rating > 3000 THEN 1 ELSE
			CASE WHEN avg_base_rating > 2800 THEN 2 ELSE
			CASE WHEN avg_base_rating > 2300 THEN 3 ELSE
			CASE WHEN avg_base_rating > 1800 THEN 4 ELSE
			CASE WHEN avg_base_rating > 1000 THEN 5 ELSE
			6 END END END END END as skill_level
		, CASE
			WHEN avg_base_rating >= 2900 AND pairing_score<=0.3 THEN 1
			ELSE CASE WHEN avg_base_rating >= 2000 AND pairing_score<=0.3 THEN 2
			ELSE CASE WHEN avg_base_rating >= 1800 AND pairing_score<=0.3 THEN 3
			ELSE CASE WHEN avg_base_rating >=1500 AND pairing_score<=0.3 THEN 4
			ELSE CASE WHEN pairing_score<=0.1 THEN 5
			END END END END END
			AS recommendation_level
	FROM cte_game_metrics
)
select * from cte_game_masked
