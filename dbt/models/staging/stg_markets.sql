-- Light cleanup pass over the raw `markets` table loaded by etl/load.py.
select
    ticker,
    event_ticker,
    title,
    status,
    yes_bid,
    yes_ask,
    no_bid,
    no_ask,
    last_price,
    coalesce(volume, 0) as volume,
    coalesce(open_interest, 0) as open_interest,
    loaded_at
from {{ source('kalshi', 'markets') }}
where ticker is not null
