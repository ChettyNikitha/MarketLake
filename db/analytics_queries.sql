-- Example analytical queries over the curated events/markets tables.

-- (1) Rank markets by volume within each event using a window function.
-- This is the query app/routers/analytics.py executes a parameterized
-- version of (limited to the top N rows overall).
WITH ranked_markets AS (
    SELECT
        m.ticker,
        m.event_ticker,
        m.title,
        m.volume,
        RANK() OVER (PARTITION BY m.event_ticker ORDER BY m.volume DESC) AS rank_in_event
    FROM markets m
)
SELECT ticker, event_ticker, title, volume, rank_in_event
FROM ranked_markets
ORDER BY volume DESC NULLS LAST;

-- (2) Count of open markets per category.
SELECT
    e.category,
    COUNT(*) AS open_market_count
FROM markets m
JOIN events e ON e.event_ticker = m.event_ticker
WHERE m.status = 'open'
GROUP BY e.category
ORDER BY open_market_count DESC;

-- (3) Top-N markets by volume overall (simple version, no per-event ranking).
SELECT ticker, event_ticker, title, volume
FROM markets
ORDER BY volume DESC NULLS LAST
LIMIT 10;
