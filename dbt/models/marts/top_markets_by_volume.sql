-- Aggregates staged markets into a per-event volume ranking, mirroring
-- db/analytics_queries.sql query (1).
select
    event_ticker,
    ticker,
    title,
    volume,
    rank() over (partition by event_ticker order by volume desc) as rank_in_event
from {{ ref('stg_markets') }}
