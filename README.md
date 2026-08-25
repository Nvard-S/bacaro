# Bacaro Hop

Find Venice's **bacari** and **cicchetti** — the tiny bars where you sip a small glass of wine (*ombra*) and snack on little plates. Browse by neighborhood and tag, or just **ask in plain words** ("natural wine near Rialto", "cheap place for sarde in saor") and get an answer built from real data about the bars.

🔗 **Live site:** https://bacarohop.onrender.com

## What it is

A small service that helps tourists and Venetians find their kind of bacaro. Under the hood is a purpose-built catalogue of bars across Venice's six *sestieri* (Cannaregio, Castello, San Marco, Dorsoduro, San Polo, Santa Croce), enriched with content from the bars' own websites and their reviews, powered by a **hybrid AI search** that answers strictly from the collected data — not from the model's imagination.

The guiding principle is **don't make things up**: every bar in an answer is flagged as either *confirmed by the data* for your question, or merely a *possible match*.

## How it works

The data flows through a pipeline (run from the private admin panel):

1. **Collect** — via the Google Places API, using Italian-language queries ("cicchetti a…", "bacaro a…"), bars are gathered for each sestiere.
2. **Enrich** — each bar's website is scanned (Parallel Extract API) for cicchetti details: small plates, prices, hours, format (standing counter vs. sit-down).
3. **Tag** — a model (OpenAI `gpt-4o-mini`) labels each bar with 8 tags (Budget-friendly, Local favorite, Canal-side, Open late, Standing bacaro, Natural wine, Lively, Vegan/Veg/GF) and writes a short, honest blurb.
4. **Index** — a search index is built from the blurbs and reviews: vector (`text-embedding-3-small` embeddings in **pgvector**) and keyword (**BM25**).
5. **Search** — for a user's question the two indexes are merged with **Reciprocal Rank Fusion**, then the model writes an answer over the top candidates, marking each as "confirmed by the data" or "possible match".

> The data is only as good as Google's reviews and the bars' own websites. Hours and prices change, so the service is a starting point for a *giro*, not a last-word reference.

## Architecture

The service is deliberately split into three independent parts:

| Part | What it is | Stack |
|---|---|---|
| **Backend** | API only (JSON) | Python / Flask, Render |
| **Public site** | what friends see | React + Vite + Tailwind, static on CDN |
| **Admin** | runs the pipeline, behind auth | React + Vite, static on CDN |
| **Database** | catalogue + embeddings + search logs | Supabase Postgres + pgvector |

The database is reachable only from the backend (Supabase's Data API is turned off). The admin is gated by **Supabase Auth** (an allow-list of emails), and the protection covers not just the UI but the backend commands it calls.

## Running locally (quick start)

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own keys
python run_migrations.py
python app.py

# frontend (in a separate terminal)
cd frontend/public
npm install
npm run dev
```

Secrets (API keys, the database connection string) live only in environment variables — **never in the code or the repository**.

## Reusing this approach for other problems

The architecture is a general template: **your own local catalogue + hybrid semantic search + model answers grounded strictly in your data, with an admin pipeline to collect / enrich / tag / index.** Swap the data source, the tag set, and the prompts, and the same skeleton solves very different problems. For example:

1. **Same format, different city or theme** — specialty coffee shops, independent bookshops and record stores, vintage shops, quiet laptop-friendly spots.
2. **Niche food filters** — a vegan / gluten-free navigator for restaurants, where what matters isn't star ratings but concrete dietary facts pulled from reviews and menus.
3. **Places and activities** — hiking trails, climbing crags, museums and exhibitions (swapping Google for a domain-specific data source).
4. **Internal knowledge** — "search-with-an-answer over your own documents": product reviews, support tickets, real-estate listings — anywhere you want to ask a question in plain words and get a grounded answer **with sources**.

What stays constant is the pattern: `collect → enrich → tag → embed → hybrid search → answer backed by the data`.

## Limitations and implications

- **Coverage = whatever the source returns.** The catalogue is limited to what Google Places surfaces for the given queries; rare spots with no online presence may be missed.
- **Facts go stale.** Hours, prices, and whether a bar still exists all change; review-derived facts can be out of date.
- **The model can be wrong.** Answers are built only from the collected data and carry a confirmed/possible flag — this lowers the risk of hallucination but does not remove it.
- **Enrichment is best-effort.** Some sites can't be read (bot protection, timeouts) so not every bar is enriched; the Instagram link is matched heuristically and isn't guaranteed.
- **Language bias.** The service is deliberately skewed toward Italian-language content — a plus for locality, a minus for sources in other languages.
- **Cost scales with searches.** Every smart query is an OpenAI call; this is protected by rate limiting and a spending cap, but scaling up costs money.
- **Search quality isn't formally measured** — there's no labelled query set to evaluate the ranking against.

## What could be improved

- **An evaluation harness** — labelled queries to measure and tune ranking (fusion weights, a cross-encoder re-rank).
- **More and better data** — official menus, live opening hours, more reviews; an "open now" filter, distance sorting, a map view.
- **Caching** — of repeated queries and embeddings; move BM25 to persistent storage.
- **Personalization** — accounts, favorites, shareable lists.
- **Multilingual** — UI and content translation.
- **A feedback loop** — users flag wrong answers, feeding data back into improvements.
- **Reliability at scale** — a transaction pooler / connection pool to the database, and CI (run the frontend tests and backend checks on every PR).

## License

MIT — see [LICENSE](LICENSE).
