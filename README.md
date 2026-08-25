# BacaroHop 🍤

**Find the Venice bacaro you're actually looking for.**

Natural wine near Rialto? Cheap cicchetti in Cannaregio? Somewhere local, lively, and good for standing at the counter?

Just ask.

🔗 **[Try BacaroHop](https://bacarohop.onrender.com)**

## Why I built it

I live an hour from Venice, yet my book club friends almost never go.

Their reason was surprisingly simple: Venice feels overwhelming. There are thousands of places, tourist traps everywhere, and finding somewhere that actually fits what you want can take more time than getting there.

So I built something for us.

BacaroHop lets you describe the kind of place you're looking for in normal words and searches a purpose-built catalogue of bacari across Venice.

And because we are millennials and apparently need to check Instagram before committing to a place, I added direct Instagram links wherever I could find them. See the food, the crowd, the atmosphere, then decide.

## How it works

**Collect → Enrich → Tag → Index → Search → Answer**

BacaroHop collects bacari through Google Places, enriches them with information from their websites and reviews, and tags useful characteristics such as:

> Budget-friendly · Local favorite · Canal-side · Standing bacaro · Natural wine · Lively · Vegan/Veg/GF

Search combines semantic vector search with BM25 keyword search. The model then answers over the retrieved data rather than inventing recommendations.

Every result is marked as either **confirmed by the data** or a **possible match**.

**Stack:** Python · Flask · React · Supabase · pgvector · OpenAI · Google Places

## Fork it and go somewhere else

The bacaro part is Venice. The discovery engine doesn't have to be.

- Planning tapas & vermouth in Barcelona?
- Looking for izakayas in Tokyo?

Build the local version for wherever you're going next.

Or change the problem entirely:

- ☕ specialty coffee
- 📚 independent bookshops
- 🎵 record stores
- 🍜 niche food & dietary discovery
- 👗 vintage shops

Swap the data, tags, and prompts. Keep the basic idea:

`collect → enrich → understand intent → retrieve → answer`

Fork it and build your own.

## Limitations

BacaroHop is an experiment and a starting point for a *giro*, not a definitive guide to Venice.

Opening hours, prices, menus, and places change. Coverage depends on the available sources, and grounding reduces model hallucinations but doesn't eliminate them.

## Run locally

See the repository setup instructions to run the backend and frontend with your own API keys and database.

## About

Built by **Nvard Stepanyan**, growth & marketing leader building and experimenting with AI products.

[LinkedIn](https://www.linkedin.com/in/YOUR-HANDLE)

MIT licensed — see [LICENSE](LICENSE).
