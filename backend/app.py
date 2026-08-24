import os
import json
import time
import re
import math
import pickle
import csv
import io
import threading
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi
from flask import Flask, request, jsonify, g, Response
from flask_cors import CORS

from storage.config import get_repository, get_index_store

APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_DIR, ".env"))

# All secrets come from the environment (see .env.example) -- never stored
# in the database or committed to source control.
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
PARALLEL_API_KEY = os.environ.get("PARALLEL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

BM25_PATH = os.path.join(APP_DIR, "bm25_index.pkl")

# DATA_BACKEND=sqlite (default) or postgres -- see storage/config.py.
repository = get_repository(APP_DIR)
index_store = get_index_store(APP_DIR)

app = Flask(__name__)

# This backend is now an API only -- the public site and admin panel are
# separate frontends on their own domains, so the browser calls this API
# cross-origin. CORS_ORIGINS lists the domains allowed to call it (comma-
# separated); "*" is fine here because auth uses a Bearer token, not cookies.
CORS_ORIGINS = [o.strip() for o in (os.environ.get("CORS_ORIGINS") or "*").split(",") if o.strip()]
CORS(app, resources={r"/*": {"origins": CORS_ORIGINS}})

# ---------- Admin access control (Supabase Auth) ----------
# The admin panel is gated by Supabase Auth: the browser signs in against
# Supabase and receives an access token; every admin API request carries that
# token as "Authorization: Bearer <token>", and the backend asks Supabase to
# validate it (GET /auth/v1/user). Only tokens whose verified email is in
# ADMIN_EMAILS are allowed through. SUPABASE_ANON_KEY is the public key
# (safe to expose to the browser) -- no JWT signing secret is handled here.
SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
ADMIN_EMAILS = {
    e.strip().lower()
    for e in (os.environ.get("ADMIN_EMAILS") or "").split(",")
    if e.strip()
}
_ADMIN_AUTH_CONFIGURED = bool(SUPABASE_URL and SUPABASE_ANON_KEY and ADMIN_EMAILS)

# Endpoints reachable without signing in: the health root, the two the public
# site calls, and the config the admin login form reads. Every other route
# requires a valid admin token.
PUBLIC_PATHS = {"/", "/api/tags", "/api/browse", "/api/auth-config"}


def _verify_admin_token(token):
    """Ask Supabase whether this access token is valid; return the user's
    lowercased email if so, else None. Using Supabase's own /auth/v1/user
    endpoint means we never hold or verify the JWT signing secret ourselves."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return (resp.json().get("email") or "").lower()


@app.before_request
def require_admin_auth():
    # CORS preflight requests carry no auth header and must pass through.
    if request.method == "OPTIONS":
        return None
    path = request.path
    if path in PUBLIC_PATHS or path.startswith("/static/"):
        return None
    # Fail closed: if admin auth isn't fully configured, lock the panel.
    if not _ADMIN_AUTH_CONFIGURED:
        return jsonify({"error": "Admin auth is not configured on the server."}), 503
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return jsonify({"error": "Not authenticated"}), 401
    email = _verify_admin_token(header[len("Bearer "):])
    if not email:
        return jsonify({"error": "Invalid or expired session"}), 401
    if email not in ADMIN_EMAILS:
        return jsonify({"error": "This account is not an admin"}), 403
    g.admin_email = email
    return None


# --- Sestiere viewport boxes (approximate -- Venice is a small, irregular
# archipelago, so rectangular boxes overlap more than they did for Verona's
# neighborhoods; adjust if results look like they're missing known bacari or
# pulling in bars from the wrong sestiere -- draw a rectangle on Google Maps
# and read the corner lat/lng values to fine-tune) ---
NEIGHBORHOODS = {
    "Cannaregio": {
        "low": {"latitude": 45.4400, "longitude": 12.3180},
        "high": {"latitude": 45.4520, "longitude": 12.3450},
    },
    "Castello": {
        "low": {"latitude": 45.4300, "longitude": 12.3400},
        "high": {"latitude": 45.4450, "longitude": 12.3650},
    },
    "San Marco": {
        "low": {"latitude": 45.4320, "longitude": 12.3300},
        "high": {"latitude": 45.4380, "longitude": 12.3420},
    },
    "Dorsoduro": {
        "low": {"latitude": 45.4250, "longitude": 12.3150},
        "high": {"latitude": 45.4360, "longitude": 12.3350},
    },
    "San Polo": {
        "low": {"latitude": 45.4360, "longitude": 12.3200},
        "high": {"latitude": 45.4430, "longitude": 12.3350},
    },
    "Santa Croce": {
        "low": {"latitude": 45.4370, "longitude": 12.3080},
        "high": {"latitude": 45.4460, "longitude": 12.3230},
    },
}

# Real Google Places (New) types that correspond to bacaro/cicchetti-style
# venues. There's no "bacaro" or "cicchetti" type in Google's taxonomy, and
# many genuine bacari get classified as "restaurant" rather than "bar" --
# broadened beyond just bar-types (a lesson from the Verona project, where
# a stricter type list left the dataset too sparse to be useful) so a place
# is kept if it carries any of these AND was surfaced by a cicchetti-focused
# query below.
BAR_TYPES = {
    "bar", "wine_bar", "pub", "bar_and_grill", "restaurant", "italian_restaurant",
}

# Italian-language queries tuned to surface bacari/cicchetti spots the way
# Venetians actually search for them. languageCode=it + regionCode=IT below
# bias Google's relevance ranking toward how locals search, and bias the
# up-to-5 returned reviews toward Italian-language ones.
QUERY_TEMPLATES = [
    "cicchetti a {loc}",
    "bacaro a {loc}",
    "bacari a {loc}",
    "osteria cicchetti a {loc}",
    "dove mangiare cicchetti a {loc}",
]

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.rating",
    "places.userRatingCount",
    "places.websiteUri",
    "places.types",
    "places.primaryType",
    "places.location",
    "places.reviews",
    "places.priceLevel",
    "places.priceRange",
    "nextPageToken",
])

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

# ---------- Parallel Extract API ----------

PARALLEL_EXTRACT_URL = "https://api.parallel.ai/v1/extract"

# What we're actually screening bar websites for: cicchetti / bacaro-style
# content, not general "about us" content.
CICCHETTI_EXTRACTION_OBJECTIVE = (
    "Find all information about cicchetti, Venetian bar snacks, bacaro-style "
    "small plates, ombra (small glass of wine), counter service, cicchetti "
    "menu items, prices, opening hours, and any other cicchetti-related "
    "content."
)

# ---------- Tag classification (OpenAI) ----------

# Kept deliberately small (8) with short labels -- mobile filter-chip UIs
# read poorly past ~6-8 primary facets, and every label here was trimmed to
# 1-3 words. Picked around what tourists and Venetians actually decide on:
# price, authenticity, hours, experience style, wine culture, atmosphere,
# scenery, dietary needs. Overlapping/low-signal tags from the original
# 13-tag set (hidden_gem, sit_down, craft_beer, and the 3-way vegan/veg/GF
# split) were merged or dropped rather than kept as separate chips.
TAG_TAXONOMY = {
    "budget_friendly": "Budget-friendly",
    "local_favorite": "Local favorite",
    "canal_side": "Canal-side",
    "open_late": "Open late",
    "standing_bacaro": "Standing bacaro",
    "natural_wine": "Natural wine",
    "lively": "Lively",
    "dietary_friendly": "Vegan/Veg/GF",
}

TAG_CLASSIFICATION_PROMPT = (
    "You are labeling a Venice bacaro/cicchetti bar based only on the data "
    "given (scraped website content and reviews). Respond with a JSON "
    "object of the form {\"tags\": [list of tag slugs], \"blurb\": string}.\n"
    "\"tags\": pick zero or more from this exact set of slugs: "
    + ", ".join(TAG_TAXONOMY.keys()) + ". Only include a tag if the data "
    "actually supports it -- do not guess or include a tag just because it "
    "seems plausible for a Venetian bar in general.\n"
    "\"blurb\": one short, specific sentence (max ~25 words) describing "
    "what's actually distinctive about this bar based on the data -- a "
    "notable dish, the atmosphere, what reviewers specifically praise. Not "
    "a generic \"great place for cicchetti\" -- if the data has nothing "
    "specific to say, keep it brief and honest rather than inventing "
    "detail. No markdown."
)

# Best-effort only: Google's API has no social-media field at all, so the
# only way to surface an Instagram link is scanning text we already
# fetched for one. Low recall by design (the scrape wasn't aimed at
# footers/social links) -- this catches it when it's mentioned, nothing
# more. Excludes non-profile paths like /p/, /reel/, /explore/.
_INSTAGRAM_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)", re.IGNORECASE
)
_INSTAGRAM_EXCLUDED_PATHS = {
    "p", "reel", "reels", "explore", "accounts", "stories", "tv", "direct",
    "rsrc.php", "static", "embed.js", "graphql", "api",
}
# Real Instagram usernames never end in a file extension -- this catches
# static-resource paths (e.g. Meta's rsrc.php-style asset URLs pulled in by
# embedded widgets) that the excluded-paths set above doesn't enumerate.
_FILE_EXTENSION_RE = re.compile(r"\.(php|js|css|png|jpe?g|gif|svg|json|ico)$", re.IGNORECASE)


def extract_instagram(text):
    if not text:
        return None
    for match in _INSTAGRAM_RE.finditer(text):
        handle = match.group(1).strip("/.")
        if not handle or handle.lower() in _INSTAGRAM_EXCLUDED_PATHS:
            continue
        if _FILE_EXTENSION_RE.search(handle):
            continue
        return f"https://instagram.com/{handle}"
    return None


def scrape_website_for_instagram(website_url):
    """Free first pass: fetch the bar's own website directly (not Google
    Maps, so no ToS concern) and regex-scan the raw HTML, including inside
    href attributes -- much more likely to catch a footer/nav social icon
    than the cicchetti-scoped Parallel excerpt, which was never asked to
    look at those. Returns None on any fetch failure; that's expected for
    some sites (bot protection, timeouts) and handled by the Parallel
    fallback, not treated as an error here."""
    try:
        resp = requests.get(
            website_url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; VeniceCicchettiBot/1.0)"},
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    return extract_instagram(resp.text)


INSTAGRAM_PARALLEL_OBJECTIVE = (
    "Find the Instagram profile link or handle for this business, if it is "
    "linked anywhere on the site (header, footer, contact page, social "
    "icons)."
)


def scrape_instagram_via_parallel(website_url, parallel_api_key):
    """Fallback for sites the direct fetch couldn't read: ask Parallel for
    the full page content (not just cicchetti-focused excerpts) so a
    footer/nav Instagram link has a chance to actually be in the text we
    scan, then run the same regex over it."""
    headers = {"Content-Type": "application/json", "x-api-key": parallel_api_key}
    body = {
        "urls": [website_url],
        "objective": INSTAGRAM_PARALLEL_OBJECTIVE,
        "advanced_settings": {"full_content": True},
    }
    resp = requests.post(PARALLEL_EXTRACT_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None
    full_content = results[0].get("full_content") or ""
    excerpt_text = "\n".join(results[0].get("excerpts") or [])
    return extract_instagram(full_content) or extract_instagram(excerpt_text)


# Safety net for tags with strong, unambiguous lexical signals -- the LLM
# classification call is occasionally internally inconsistent (e.g. writes
# a blurb that says "natural wines" but omits the natural_wine tag from
# the same response), so keyword presence in the bar's own data is used to
# catch what the model missed. Deliberately limited to tags where a keyword
# hit is a reliable, low-false-positive signal; left out entirely for tags
# like canal_side or local_favorite where a matching word (e.g. an address
# containing "Fondamenta") doesn't actually confirm the concept.
KEYWORD_TAG_TRIGGERS = {
    "natural_wine": [
        "natural wine", "natural wines", "vino naturale", "vini naturali",
        "orange wine", "biodynamic", "vino bio", "vini bio", "organic wine",
    ],
    "dietary_friendly": [
        "vegan", "vegano", "vegani", "vegetarian", "vegetariano",
        "gluten free", "gluten-free", "senza glutine",
    ],
    "canal_side": [
        "canal view", "canal views", "vista sul canale", "overlooking the canal",
    ],
}
# The generic address word "Fondamenta" appears on nearly every Venice
# street regardless of whether a bar actually has water-side seating, so
# it's deliberately excluded -- canal_side only trusts phrases that
# describe an actual view/vantage, not just an address containing the word.

_HOURS_RANGE_RE = re.compile(
    r"(\d{1,2}):(\d{2})\s*(AM|PM)?\s*[-–—]\s*(\d{1,2}):(\d{2})\s*(AM|PM)?",
    re.IGNORECASE,
)


def mentions_late_hours(text):
    """True if a closing time in the text is at/after 11pm or in the early
    morning (past midnight) -- parsed from actual posted hours rather than
    guessed from vague phrases like "late night", which are too easy to
    mismatch (e.g. a review title, not the bar's own hours)."""
    if not text:
        return False
    for m in _HOURS_RANGE_RE.finditer(text):
        close_h, ampm = int(m.group(4)), m.group(6)
        if ampm:
            hour24 = (close_h % 12) + (12 if ampm.upper() == "PM" else 0)
        else:
            hour24 = close_h
        if hour24 >= 23 or hour24 <= 5:
            return True
    return False


def keyword_backup_tags(document):
    text = (document or "").lower()
    tags = {tag for tag, phrases in KEYWORD_TAG_TRIGGERS.items() if any(p in text for p in phrases)}
    if mentions_late_hours(document or ""):
        tags.add("open_late")
    return tags


def classify_bar(document, openai_client):
    if not document:
        return [], ""
    resp = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": TAG_CLASSIFICATION_PROMPT},
            {"role": "user", "content": document[:6000]},
        ],
    )
    try:
        parsed = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    tags = {t for t in (parsed.get("tags") or []) if t in TAG_TAXONOMY}
    tags |= keyword_backup_tags(document)
    blurb = parsed.get("blurb") or ""
    return sorted(tags), blurb


# ---------- RAG search (OpenAI + ChromaDB + BM25) ----------

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
# Reciprocal-rank-fusion constant used to merge the vector and BM25 rankings
# -- avoids having to normalize two incomparable score scales (cosine
# distance vs. BM25 score) against each other.
RRF_K = 60

RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant for finding bacari and cicchetti spots in "
    "Venice -- any cicchetti-related question, not narrowly restricted to "
    "one style. You will be given the user's question and data for several "
    "candidate bars, numbered in order. Using only the provided data (no "
    "outside knowledge), respond with a single JSON object of the form "
    "{\"summary\": string, \"bars\": [{\"name\": string, \"relevant\": "
    "boolean, \"explanation\": string}]}.\n"
    "\"bars\" must have exactly one entry per candidate bar, in the same "
    "order they were given. Set \"relevant\": true ONLY if the data "
    "explicitly confirms that bar answers the user's specific question -- "
    "otherwise set it false. Be precise, not just plausible-sounding: a bar "
    "mentioning something related but different is NOT evidence for what "
    "was actually asked (e.g. a general food menu does not confirm "
    "cicchetti unless cicchetti/bacaro-style snacks are explicitly "
    "mentioned). When relevant is true, write a rich, specific "
    "\"explanation\" (2-4 sentences) that actually uses the concrete "
    "details available in the data instead of a generic paraphrase: name "
    "specific cicchetti/dishes mentioned, prices or price range if given, "
    "opening hours or busy times if mentioned, atmosphere/seating details "
    "(standing bacaro vs. sit-down, counter service), and pull short "
    "direct quotes from reviews when they add real color -- but only "
    "state what the data actually says, never pad with invented detail "
    "just to sound fuller. When relevant is false, \"explanation\" can be "
    "a short reason or empty.\n"
    "\"summary\" is one sentence directly answering the question, based "
    "only on the bars marked relevant -- if none are relevant, say so "
    "plainly instead of guessing.\n"
    "Do not use markdown formatting (no asterisks, no bold, no headers) "
    "anywhere."
)

_bm25_lock = threading.Lock()
_bm25_state = {"index": None, "place_ids": []}

_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9]+")


def tokenize(text):
    return _TOKEN_RE.findall(text.lower())


def load_bm25_index():
    global _bm25_state
    if os.path.exists(BM25_PATH):
        with open(BM25_PATH, "rb") as f:
            _bm25_state = pickle.load(f)


def save_bm25_index():
    with open(BM25_PATH, "wb") as f:
        pickle.dump(_bm25_state, f)


# Load any previously built BM25 index so search works right after a
# restart, without forcing a re-index every time the server is launched.
load_bm25_index()


def rank_reviews(reviews):
    """Google gives us at most 5 reviews per place, already pre-selected by
    its own black-box relevance ranking -- there's no API lever to ask for
    a different or larger pool. The only thing we control is the order we
    feed those 5 into the RAG document, so prioritize the ones most likely
    to be informative: Italian-language first (this project biases toward
    local-language content throughout), then longer reviews (more likely
    to contain actual detail rather than a one-line rating)."""
    def sort_key(r):
        is_italian = (r.get("language_code") or "").lower().startswith("it")
        length = len(r.get("text") or "")
        return (0 if is_italian else 1, -length)
    return sorted(reviews, key=sort_key)


def build_bar_document(row):
    """Combine cicchetti_content + review text into one RAG document."""
    parts = []
    if row["cicchetti_content"]:
        parts.append(row["cicchetti_content"])
    reviews = json.loads(row["reviews"]) if row["reviews"] else []
    ranked_reviews = rank_reviews(reviews)
    review_texts = [r["text"] for r in ranked_reviews if r.get("text")]
    if review_texts:
        parts.append("\n".join(review_texts))
    # Keep comfortably under the embedding model's per-input token limit.
    return "\n\n".join(parts).strip()[:12000]


def build_indexes(openai_client):
    rows = repository.list_bars()

    docs, ids = [], []
    for row in rows:
        doc = build_bar_document(row)
        if not doc:
            continue
        docs.append(doc)
        ids.append(row["place_id"])

    # Full rebuild: replace the whole index so removed/changed bars don't
    # leave stale entries behind.
    embeddings = []
    if docs:
        batch_size = 100
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            resp = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            embeddings.extend([item.embedding for item in resp.data])
    index_store.rebuild(ids, embeddings)

    global _bm25_state
    bm25 = BM25Okapi([tokenize(d) for d in docs]) if docs else None
    with _bm25_lock:
        _bm25_state = {"index": bm25, "place_ids": ids}
        save_bm25_index()

    return len(docs)


def rebuild_bm25_from_db():
    """Rebuild just the BM25 half of the index from the database. Cheap --
    no OpenAI calls -- so it can run at startup and make AI search work
    immediately after every deploy/restart, without a manual "Index bars".
    The vector half lives in pgvector and persists on its own."""
    global _bm25_state
    rows = repository.list_bars()
    docs, ids = [], []
    for row in rows:
        doc = build_bar_document(row)
        if not doc:
            continue
        docs.append(doc)
        ids.append(row["place_id"])
    bm25 = BM25Okapi([tokenize(d) for d in docs]) if docs else None
    with _bm25_lock:
        _bm25_state = {"index": bm25, "place_ids": ids}
        try:
            save_bm25_index()
        except Exception:
            pass
    return len(ids)


# On startup, make sure BM25 is ready. Prefer a cached pickle from this
# instance; if there isn't one (e.g. a fresh deploy wiped the disk), rebuild
# from the database so search works right away instead of needing a manual
# re-index. Best-effort: if the DB is briefly unreachable, the app still
# starts and a later "Index bars" (or restart) will populate it.
if not _bm25_state["place_ids"]:
    try:
        rebuild_bm25_from_db()
    except Exception:
        pass


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GEO_RADIUS_KM = 1.0

LOCATION_DETECTION_PROMPT = (
    "Extract a specific location reference (street name, campo, landmark, "
    "or sestiere) mentioned in this search query about bars in Venice, "
    "Italy, if one is genuinely named. Respond with a JSON object "
    "{\"location\": string or null}. Only extract it if a specific place is "
    "actually mentioned in the query -- do not invent or infer one that "
    "isn't there."
)


def detect_location_reference(query, openai_client):
    resp = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": LOCATION_DETECTION_PROMPT},
            {"role": "user", "content": query},
        ],
    )
    try:
        parsed = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return None
    location = parsed.get("location")
    return location.strip() if isinstance(location, str) and location.strip() else None


def geocode_location(location_text, google_api_key):
    resp = requests.get(
        GEOCODING_URL,
        params={"address": f"{location_text}, Venice, Italy", "key": google_api_key},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def resolve_eligible_ids(neighborhood, geo_center, tags=None):
    """None means "no restriction, search everything indexed". A list
    (possibly empty) means restrict to exactly those place_ids -- computed
    by combining the neighborhood dropdown, a detected/selected geo
    location, and required tags, all with AND semantics."""
    scoped_neighborhood = neighborhood if neighborhood and neighborhood != "All Venice" else None
    if not scoped_neighborhood and not geo_center and not tags:
        return None

    rows = repository.list_bars(neighborhood=scoped_neighborhood)

    if geo_center:
        lat0, lng0 = geo_center
        rows = [
            r for r in rows
            if r["latitude"] is not None and r["longitude"] is not None
            and haversine_km(lat0, lng0, r["latitude"], r["longitude"]) <= GEO_RADIUS_KM
        ]

    if tags:
        # ALL selected tags must match -- narrows results as more tags are
        # picked, for precise filtering rather than broad matching.
        wanted = set(tags)
        def has_all_tags(row):
            row_tags = set(json.loads(row["tags"])) if row["tags"] else set()
            return wanted.issubset(row_tags)
        rows = [r for r in rows if has_all_tags(r)]

    return [r["place_id"] for r in rows]


def hybrid_search(query, top_n, openai_client, eligible_ids=None):
    corpus_size = index_store.count()
    if corpus_size == 0:
        return [], 0

    with _bm25_lock:
        bm25 = _bm25_state["index"]
        place_ids = _bm25_state["place_ids"]

    scoped = eligible_ids is not None
    if scoped:
        # eligible_ids comes from a SQL query against the bars table, which
        # can include bars that were never actually indexed (e.g. no
        # reviews/cicchetti_content yet, so build_bar_document() came back
        # empty and build_indexes() skipped them). Chroma's query(ids=...)
        # throws an internal error on an id it doesn't know about, so this
        # must be intersected with what's actually indexed first.
        eligible_ids = [pid for pid in eligible_ids if pid in set(place_ids)]
        if not eligible_ids:
            return [], 0

    # Rank across the FULL eligible pool on each signal before fusing, not
    # just the top_n of each individually -- a bar can rank just outside
    # top_n on both vector and BM25 alone while still being the best
    # overall match once the two signals are combined. Truncating before
    # fusion silently drops exactly those bars.
    q_embedding = openai_client.embeddings.create(
        model=EMBEDDING_MODEL, input=[query]
    ).data[0].embedding
    vector_ids = index_store.query(
        q_embedding, n_results=corpus_size, ids=eligible_ids if scoped else None,
    )
    analyzed_count = len(vector_ids) if scoped else corpus_size

    bm25_ids = []
    if bm25 is not None and place_ids:
        scores = bm25.get_scores(tokenize(query))
        candidate_indices = range(len(scores))
        if scoped:
            eligible_set = set(eligible_ids)
            candidate_indices = [i for i in candidate_indices if place_ids[i] in eligible_set]
        ranked = sorted(candidate_indices, key=lambda i: scores[i], reverse=True)
        bm25_ids = [place_ids[i] for i in ranked if scores[i] > 0]

    combined = {}
    for rank, place_id in enumerate(vector_ids, start=1):
        combined[place_id] = combined.get(place_id, 0.0) + 1 / (RRF_K + rank)
    for rank, place_id in enumerate(bm25_ids, start=1):
        combined[place_id] = combined.get(place_id, 0.0) + 1 / (RRF_K + rank)

    ranked_ids = sorted(combined, key=combined.get, reverse=True)[:top_n]
    return ranked_ids, analyzed_count


def answer_query(query, top_n, api_key, neighborhood=None, google_api_key=None, tags=None):
    client = OpenAI(api_key=api_key)

    location_text = detect_location_reference(query, client)
    geo_center = None
    if location_text and google_api_key:
        try:
            geo_center = geocode_location(location_text, google_api_key)
        except requests.RequestException:
            geo_center = None

    eligible_ids = resolve_eligible_ids(neighborhood, geo_center, tags)
    ranked_ids, analyzed_count = hybrid_search(query, top_n, client, eligible_ids)

    geo_info = {
        "location_detected": location_text,
        "geo_filter_applied": geo_center is not None,
    }

    if not ranked_ids:
        scope_bits = []
        if neighborhood and neighborhood != "All Venice":
            scope_bits.append(neighborhood)
        if geo_center:
            scope_bits.append(f"within {GEO_RADIUS_KM:g} km of {location_text}")
        scope = f" ({', '.join(scope_bits)})" if scope_bits else ""
        return (
            f"No indexed bars matched this query{scope}. Try rephrasing, "
            "picking a different neighborhood, or click "
            "\"Index bars\" if you haven't yet.",
            [],
            analyzed_count,
            geo_info,
        )

    rows = repository.get_bars_by_ids(ranked_ids)
    rows_by_id = {row["place_id"]: row for row in rows}
    ordered_rows = [rows_by_id[pid] for pid in ranked_ids if pid in rows_by_id]

    context_blocks = []
    sources = []
    for i, row in enumerate(ordered_rows, start=1):
        price_label = format_price(row)
        context_blocks.append(
            f"{i}. Name: {row['name']}\nAddress: {row['address']}\n"
            f"Neighborhood: {row['neighborhood']}\nRating: {row['rating']}\n"
            f"Price: {price_label or 'unknown'}\n"
            f"Website: {row['website']}\nContent: {build_bar_document(row)}"
        )
        sources.append({
            "name": row["name"], "address": row["address"],
            "neighborhood": row["neighborhood"], "rating": row["rating"],
            "user_rating_count": row["user_rating_count"],
            "website": row["website"], "place_id": row["place_id"],
            "instagram_url": row["instagram_url"],
            "price": price_label, "blurb": row["blurb"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "explanation": "", "confirmed": False,
        })

    context = "\n\n---\n\n".join(context_blocks)
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {query}\n\nBar data:\n{context}"},
        ],
    )

    try:
        parsed = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    summary = parsed.get("summary") or resp.choices[0].message.content
    bar_explanations = parsed.get("bars") or []

    for source, explained in zip(sources, bar_explanations):
        source["confirmed"] = bool(explained.get("relevant"))
        source["explanation"] = explained.get("explanation", "")

    # Always return up to top_n bars (the user asked for N results), but
    # put data-confirmed matches first and clearly flag the rest as
    # unconfirmed rather than silently passing a guess off as a fact.
    confirmed = [s for s in sources if s["confirmed"]]
    unconfirmed = [s for s in sources if not s["confirmed"]]
    ordered_sources = (confirmed + unconfirmed)[:top_n]

    return summary, ordered_sources, analyzed_count, geo_info


# ---------- DB helpers ----------

def mask_key(key):
    if not key:
        return None
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "…" + key[-4:]


# ---------- Google Places (New) ----------

def search_text(query, bbox, api_key, page_token=None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "languageCode": "it",
        "regionCode": "IT",
        "locationRestriction": {"rectangle": bbox},
    }
    if page_token:
        body["pageToken"] = page_token
    resp = requests.post(PLACES_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_money(money):
    """Google's Money type: {currencyCode, units, nanos}. Returns a float."""
    if not money:
        return None
    units = float(money.get("units", 0) or 0)
    nanos = float(money.get("nanos", 0) or 0) / 1e9
    return units + nanos


def format_price(row):
    """Human-readable price for RAG context/display -- prefers the actual
    priceRange (closest thing to an "average check") over the coarser
    priceLevel enum, since not every place has both populated."""
    lo, hi, currency = row["price_range_min"], row["price_range_max"], row["price_range_currency"] or ""
    if lo is not None and hi is not None:
        return f"{currency} {lo:.0f}-{hi:.0f}".strip()
    if lo is not None:
        return f"{currency} {lo:.0f}+".strip()
    if hi is not None:
        return f"up to {currency} {hi:.0f}".strip()
    if row["price_level"]:
        return row["price_level"].replace("PRICE_LEVEL_", "").replace("_", " ").title()
    return None


def upsert_bar(place, neighborhood, query):
    place_id = place.get("id")
    if not place_id:
        return False
    types = place.get("types", []) or []
    if not any(t in BAR_TYPES for t in types):
        return False

    name = (place.get("displayName") or {}).get("text", "")
    address = place.get("formattedAddress", "")
    rating = place.get("rating")
    user_rating_count = place.get("userRatingCount")
    website = place.get("websiteUri")
    primary_type = place.get("primaryType")
    location = place.get("location") or {}
    lat = location.get("latitude")
    lng = location.get("longitude")

    price_level = place.get("priceLevel")
    price_range = place.get("priceRange") or {}
    price_range_min = parse_money(price_range.get("startPrice"))
    price_range_max = parse_money(price_range.get("endPrice"))
    price_range_currency = (
        (price_range.get("startPrice") or price_range.get("endPrice") or {}).get("currencyCode")
    )

    reviews = []
    for r in place.get("reviews", []) or []:
        reviews.append({
            "author": (r.get("authorAttribution") or {}).get("displayName"),
            "rating": r.get("rating"),
            "text": (r.get("text") or {}).get("text"),
            "language_code": (r.get("text") or {}).get("languageCode"),
            "relative_time": r.get("relativePublishTimeDescription"),
            "publish_time": r.get("publishTime"),
        })

    # Deliberately omits cicchetti_content/tags/blurb/instagram_url -- those
    # are filled in by later admin steps and must survive a re-collect.
    repository.upsert_bar({
        "place_id": place_id, "name": name, "address": address, "rating": rating,
        "user_rating_count": user_rating_count, "website": website,
        "place_types": json.dumps(types, ensure_ascii=False), "primary_type": primary_type,
        "latitude": lat, "longitude": lng, "neighborhood": neighborhood,
        "reviews": json.dumps(reviews, ensure_ascii=False), "found_via_query": query,
        "price_level": price_level, "price_range_min": price_range_min,
        "price_range_max": price_range_max, "price_range_currency": price_range_currency,
    })
    return True


def collect_one(neighborhood, api_key, max_pages=3):
    bbox = NEIGHBORHOODS[neighborhood]
    stats = {"queries": 0, "candidates": 0, "saved": 0, "skipped_non_bar_type": 0}
    for template in QUERY_TEMPLATES:
        query = template.format(loc=f"{neighborhood}, Venice")
        stats["queries"] += 1
        page_token = None
        for _page in range(max_pages):
            data = search_text(query, bbox, api_key, page_token)
            places = data.get("places", [])
            for place in places:
                stats["candidates"] += 1
                if upsert_bar(place, neighborhood, query):
                    stats["saved"] += 1
                else:
                    stats["skipped_non_bar_type"] += 1
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(2)  # Google requires next_page_token to "warm up" briefly
    return stats


def extract_cicchetti_content(url, api_key):
    headers = {"Content-Type": "application/json", "x-api-key": api_key}
    body = {"urls": [url], "objective": CICCHETTI_EXTRACTION_OBJECTIVE}
    resp = requests.post(PARALLEL_EXTRACT_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        errors = data.get("errors") or []
        message = errors[0].get("message") if errors else "No results returned"
        raise RuntimeError(message)
    excerpts = results[0].get("excerpts") or []
    return "\n\n".join(excerpts)


# ---------- Cicchetti-content extraction job (Parallel) ----------

_extract_lock = threading.Lock()
_extract_progress = {
    "running": False,
    "neighborhood": None,
    "total": 0,
    "done": 0,
    "skipped": 0,
    "errors": 0,
    "last_error": None,
}


def _bars_needing_content(neighborhood):
    scoped = neighborhood if neighborhood and neighborhood != "All Venice" else None
    return repository.bars_missing_content(neighborhood=scoped)


def _run_extraction_job(api_key, rows):
    for row in rows:
        try:
            content = extract_cicchetti_content(row["website"], api_key)
            repository.update_bar_fields(row["place_id"], {"cicchetti_content": content})
        except Exception as e:
            with _extract_lock:
                _extract_progress["errors"] += 1
                _extract_progress["last_error"] = str(e)
        finally:
            with _extract_lock:
                _extract_progress["done"] += 1
    with _extract_lock:
        _extract_progress["running"] = False


# ---------- Tag classification job ----------

_tag_lock = threading.Lock()
_tag_progress = {"running": False, "total": 0, "done": 0, "errors": 0}


def _bars_needing_tags():
    # blurb IS NULL also catches bars tagged before the blurb/Instagram
    # fields existed, so re-running this after that change backfills them
    # instead of skipping bars that already have tags.
    return repository.bars_missing_tags()


def _run_tagging_job(api_key, rows):
    client = OpenAI(api_key=api_key)
    for row in rows:
        try:
            doc = build_bar_document(row)
            tags, blurb = classify_bar(doc, client)
            instagram_url = extract_instagram(doc)
            repository.update_bar_fields(row["place_id"], {
                "tags": json.dumps(tags), "blurb": blurb, "instagram_url": instagram_url,
            })
        except Exception:
            with _tag_lock:
                _tag_progress["errors"] += 1
        finally:
            with _tag_lock:
                _tag_progress["done"] += 1
    with _tag_lock:
        _tag_progress["running"] = False


# ---------- Instagram discovery job (direct scrape, then Parallel fallback) ----------

_social_lock = threading.Lock()
_social_progress = {
    "running": False, "total": 0, "done": 0,
    "found_direct": 0, "found_parallel": 0, "errors": 0,
}


def _bars_needing_instagram():
    return repository.bars_missing_instagram()


def _run_instagram_job(parallel_api_key, rows):
    for row in rows:
        try:
            found = scrape_website_for_instagram(row["website"])
            source = "direct"
            if not found and parallel_api_key:
                found = scrape_instagram_via_parallel(row["website"], parallel_api_key)
                source = "parallel"
            if found:
                repository.update_bar_fields(row["place_id"], {"instagram_url": found})
                with _social_lock:
                    _social_progress["found_direct" if source == "direct" else "found_parallel"] += 1
        except Exception:
            with _social_lock:
                _social_progress["errors"] += 1
        finally:
            with _social_lock:
                _social_progress["done"] += 1
    with _social_lock:
        _social_progress["running"] = False


def browse_bars(neighborhood, tags):
    """Plain filter + sort, no LLM -- for checkbox-only browsing with no
    free-text question."""
    scoped = neighborhood if neighborhood and neighborhood != "All Venice" else None
    rows = repository.list_bars(neighborhood=scoped)

    if tags:
        # ALL selected tags must match -- see resolve_eligible_ids.
        wanted = set(tags)
        rows = [
            r for r in rows
            if wanted.issubset(set(json.loads(r["tags"])) if r["tags"] else set())
        ]

    rows = sorted(rows, key=lambda r: r["rating"] or 0, reverse=True)
    total = len(rows)
    bars = [{
        "place_id": r["place_id"], "name": r["name"], "address": r["address"],
        "neighborhood": r["neighborhood"], "rating": r["rating"],
        "user_rating_count": r["user_rating_count"],
        "website": r["website"], "instagram_url": r["instagram_url"],
        "price": format_price(r), "blurb": r["blurb"],
        "tags": json.loads(r["tags"]) if r["tags"] else [],
    } for r in rows[:60]]
    return bars, total


# ---------- Query helpers ----------

def bars_query(neighborhood):
    scoped = neighborhood if neighborhood and neighborhood != "All Venice" else None
    rows = repository.list_bars(neighborhood=scoped)
    return sorted(rows, key=lambda r: (r["neighborhood"] or "", r["name"] or ""))


# ---------- Routes ----------
# API only -- the public site and admin panel are separate frontend apps
# now. The root is just a health check so hitting the backend directly
# shows it's alive.

@app.route("/")
def health():
    return jsonify({"service": "bacaro-hop-api", "ok": True})


@app.route("/api/auth-config")
def auth_config():
    # Public, non-secret values the admin login form needs to talk to
    # Supabase Auth directly from the browser.
    return jsonify({
        "supabase_url": SUPABASE_URL,
        "anon_key": SUPABASE_ANON_KEY,
        "configured": _ADMIN_AUTH_CONFIGURED,
    })


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify({"has_key": bool(GOOGLE_PLACES_API_KEY), "masked_key": mask_key(GOOGLE_PLACES_API_KEY)})


@app.route("/api/settings/parallel", methods=["GET"])
def get_parallel_settings():
    return jsonify({"has_key": bool(PARALLEL_API_KEY), "masked_key": mask_key(PARALLEL_API_KEY)})


@app.route("/api/settings/openai", methods=["GET"])
def get_openai_settings():
    return jsonify({"has_key": bool(OPENAI_API_KEY), "masked_key": mask_key(OPENAI_API_KEY)})


@app.route("/api/rag-index", methods=["POST"])
def rag_index():
    api_key = OPENAI_API_KEY
    if not api_key:
        return jsonify({"error": "Save an OpenAI API key first."}), 400
    try:
        indexed = build_indexes(OpenAI(api_key=api_key))
        return jsonify({"ok": True, "indexed": indexed})
    except Exception as e:
        return jsonify({"error": f"Indexing failed: {e}"}), 502


@app.route("/api/rag-search", methods=["POST"])
def rag_search():
    api_key = OPENAI_API_KEY
    if not api_key:
        return jsonify({"error": "Save an OpenAI API key first."}), 400

    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    neighborhood = data.get("neighborhood") or "All Venice"
    try:
        top_n = int(data.get("top_n", 5))
    except (TypeError, ValueError):
        top_n = 5
    top_n = max(1, min(20, top_n))

    with _bm25_lock:
        has_index = bool(_bm25_state["place_ids"])
    if not has_index:
        return jsonify({"error": 'No index found. Click "Index bars" first.'}), 400

    try:
        answer, sources, analyzed, geo_info = answer_query(
            query, top_n, api_key, neighborhood, GOOGLE_PLACES_API_KEY
        )
        return jsonify({
            "ok": True, "answer": answer, "sources": sources,
            "analyzed": analyzed, "neighborhood": neighborhood,
            **geo_info,
        })
    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 502


@app.route("/api/collect", methods=["POST"])
def collect():
    api_key = GOOGLE_PLACES_API_KEY
    if not api_key:
        return jsonify({"error": "Save a Google Places API key first."}), 400
    data = request.get_json(force=True)
    neighborhood = data.get("neighborhood", "All Venice")

    try:
        if neighborhood == "All Venice":
            results = {}
            for name in NEIGHBORHOODS:
                results[name] = collect_one(name, api_key)
            return jsonify({"ok": True, "results": results})
        elif neighborhood in NEIGHBORHOODS:
            stats = collect_one(neighborhood, api_key)
            return jsonify({"ok": True, "results": {neighborhood: stats}})
        else:
            return jsonify({"error": f"Unknown neighborhood: {neighborhood}"}), 400
    except requests.HTTPError as e:
        return jsonify({
            "error": f"Google API error: {e.response.status_code} {e.response.text}"
        }), 502


@app.route("/api/fetch-cicchetti-content", methods=["POST"])
def fetch_cicchetti_content():
    api_key = PARALLEL_API_KEY
    if not api_key:
        return jsonify({"error": "Save a Parallel API key first."}), 400

    with _extract_lock:
        if _extract_progress["running"]:
            return jsonify({"error": "Extraction already running."}), 409

    data = request.get_json(force=True)
    neighborhood = data.get("neighborhood", "All Venice")
    rows, skipped = _bars_needing_content(neighborhood)

    with _extract_lock:
        _extract_progress.update({
            "running": len(rows) > 0,
            "neighborhood": neighborhood,
            "total": len(rows),
            "done": 0,
            "skipped": skipped,
            "errors": 0,
            "last_error": None,
        })

    if rows:
        thread = threading.Thread(
            target=_run_extraction_job, args=(api_key, rows), daemon=True
        )
        thread.start()

    return jsonify({"ok": True, "total": len(rows), "skipped": skipped})


@app.route("/api/fetch-cicchetti-content/progress")
def fetch_cicchetti_progress():
    with _extract_lock:
        return jsonify(dict(_extract_progress))


@app.route("/api/tags")
def get_tags():
    return jsonify({"tags": [{"slug": k, "label": v} for k, v in TAG_TAXONOMY.items()]})


@app.route("/api/tag-bars", methods=["POST"])
def tag_bars():
    api_key = OPENAI_API_KEY
    if not api_key:
        return jsonify({"error": "Save an OpenAI API key first."}), 400

    with _tag_lock:
        if _tag_progress["running"]:
            return jsonify({"error": "Tagging already running."}), 409

    rows = _bars_needing_tags()
    with _tag_lock:
        _tag_progress.update({"running": len(rows) > 0, "total": len(rows), "done": 0, "errors": 0})

    if rows:
        thread = threading.Thread(target=_run_tagging_job, args=(api_key, rows), daemon=True)
        thread.start()

    return jsonify({"ok": True, "total": len(rows)})


@app.route("/api/tag-bars/progress")
def tag_bars_progress():
    with _tag_lock:
        return jsonify(dict(_tag_progress))


@app.route("/api/find-instagram", methods=["POST"])
def find_instagram():
    with _social_lock:
        if _social_progress["running"]:
            return jsonify({"error": "Already running."}), 409

    rows = _bars_needing_instagram()
    with _social_lock:
        _social_progress.update({
            "running": len(rows) > 0, "total": len(rows), "done": 0,
            "found_direct": 0, "found_parallel": 0, "errors": 0,
        })

    if rows:
        parallel_api_key = PARALLEL_API_KEY
        thread = threading.Thread(
            target=_run_instagram_job, args=(parallel_api_key, rows), daemon=True
        )
        thread.start()

    return jsonify({"ok": True, "total": len(rows)})


@app.route("/api/find-instagram/progress")
def find_instagram_progress():
    with _social_lock:
        return jsonify(dict(_social_progress))


def _log_search(query, neighborhood, tags, answer, sources, analyzed, geo_info):
    """Record a search and its full result set. Best-effort: any failure here
    is swallowed so logging never affects the user's search."""
    try:
        repository.log_search({
            "query": query,
            "neighborhood": neighborhood,
            "tags": json.dumps(tags, ensure_ascii=False),
            "mode": "search",
            "analyzed": analyzed,
            "answer": answer,
            "results": json.dumps([
                {"place_id": s.get("place_id"), "name": s.get("name"), "confirmed": s.get("confirmed")}
                for s in sources
            ], ensure_ascii=False),
            "location_detected": geo_info.get("location_detected"),
            "geo_filter_applied": geo_info.get("geo_filter_applied"),
        })
    except Exception:
        pass


@app.route("/api/browse", methods=["POST"])
def browse():
    data = request.get_json(force=True)
    neighborhood = data.get("neighborhood") or "All Venice"
    tags = [t for t in (data.get("tags") or []) if t in TAG_TAXONOMY]
    query = (data.get("query") or "").strip()

    if not query:
        bars, total = browse_bars(neighborhood, tags)
        return jsonify({
            "ok": True, "mode": "browse", "bars": bars, "total": total,
            "neighborhood": neighborhood,
        })

    api_key = OPENAI_API_KEY
    if not api_key:
        return jsonify({"error": "The search index isn't set up yet. Try again later."}), 400
    with _bm25_lock:
        has_index = bool(_bm25_state["place_ids"])
    if not has_index:
        return jsonify({"error": "The search index isn't set up yet. Try again later."}), 400

    try:
        top_n = int(data.get("top_n", 8))
    except (TypeError, ValueError):
        top_n = 8
    top_n = max(1, min(20, top_n))

    try:
        answer, sources, analyzed, geo_info = answer_query(
            query, top_n, api_key, neighborhood, GOOGLE_PLACES_API_KEY, tags
        )
        _log_search(query, neighborhood, tags, answer, sources, analyzed, geo_info)
        return jsonify({
            "ok": True, "mode": "search", "answer": answer, "sources": sources,
            "analyzed": analyzed, "neighborhood": neighborhood, **geo_info,
        })
    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 502


@app.route("/api/summary")
def summary():
    neighborhood = request.args.get("neighborhood", "All Venice")
    rows = bars_query(neighborhood)
    total = len(rows)
    ratings = [r["rating"] for r in rows if r["rating"] is not None]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    with_website = sum(1 for r in rows if r["website"])
    with_reviews = sum(1 for r in rows if r["reviews"] and json.loads(r["reviews"]))
    with_coords = sum(1 for r in rows if r["latitude"] is not None and r["longitude"] is not None)
    return jsonify({
        "neighborhood": neighborhood,
        "total": total,
        "avg_rating": avg_rating,
        "with_website": with_website,
        "with_reviews": with_reviews,
        "with_coordinates": with_coords,
    })


@app.route("/api/export")
def export_csv():
    neighborhood = request.args.get("neighborhood", "All Venice")
    rows = bars_query(neighborhood)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "name", "address", "neighborhood", "rating", "user_rating_count",
        "website", "instagram_url", "place_id", "place_types", "primary_type",
        "latitude", "longitude", "price_level", "price_range_min",
        "price_range_max", "price_range_currency", "tags", "blurb",
        "review_count", "reviews_json", "cicchetti_content",
    ])
    for r in rows:
        reviews = json.loads(r["reviews"]) if r["reviews"] else []
        writer.writerow([
            r["name"], r["address"], r["neighborhood"], r["rating"], r["user_rating_count"],
            r["website"], r["instagram_url"], r["place_id"], r["place_types"], r["primary_type"],
            r["latitude"], r["longitude"], r["price_level"], r["price_range_min"],
            r["price_range_max"], r["price_range_currency"], r["tags"], r["blurb"],
            len(reviews), json.dumps(reviews, ensure_ascii=False), r["cicchetti_content"],
        ])

    filename = f"venice_cicchetti_{neighborhood.replace(' ', '_')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5051, threaded=True)
