-- Enable pgvector so we can store embeddings as a native column type.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS bars (
    place_id TEXT PRIMARY KEY,
    name TEXT,
    address TEXT,
    rating REAL,
    user_rating_count INTEGER,
    website TEXT,
    place_types TEXT,
    primary_type TEXT,
    latitude REAL,
    longitude REAL,
    neighborhood TEXT,
    reviews TEXT,
    found_via_query TEXT,
    cicchetti_content TEXT,
    price_level TEXT,
    price_range_min REAL,
    price_range_max REAL,
    price_range_currency TEXT,
    tags TEXT,
    blurb TEXT,
    instagram_url TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- One row per bar that has been embedded (mirrors today's behavior where
-- bars with no reviews/content are skipped when building the index).
CREATE TABLE IF NOT EXISTS bar_embeddings (
    place_id TEXT PRIMARY KEY REFERENCES bars(place_id) ON DELETE CASCADE,
    embedding vector(1536)
);

-- Index for fast nearest-neighbor search (cosine distance, matching what
-- Chroma used by default).
CREATE INDEX IF NOT EXISTS bar_embeddings_cosine_idx
    ON bar_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
