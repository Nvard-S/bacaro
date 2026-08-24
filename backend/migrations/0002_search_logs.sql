-- One row per real search a user submits: the query, the filters, and the
-- full set of results (bars returned, plus the generated answer). Used to
-- understand what people actually search for.
CREATE TABLE IF NOT EXISTS search_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),
    query TEXT,
    neighborhood TEXT,
    tags TEXT,                 -- JSON array of tag slugs
    mode TEXT,                 -- 'search'
    analyzed INTEGER,          -- how many bars were considered
    answer TEXT,               -- the generated summary
    results TEXT,              -- JSON: [{place_id, name, confirmed}]
    location_detected TEXT,
    geo_filter_applied BOOLEAN
);

CREATE INDEX IF NOT EXISTS search_logs_created_at_idx ON search_logs (created_at DESC);
