"""Storage interfaces. app.py talks only to these -- never to sqlite3,
psycopg2, or chromadb directly -- so the backend can be swapped by writing
a new implementation, not by editing app.py's route/business logic.
"""
from abc import ABC, abstractmethod


class BarRepository(ABC):
    """Everything app.py needs to read and write bar records. Method shapes
    match what the app's existing routes and background jobs actually call
    -- no speculative extras."""

    @abstractmethod
    def list_bars(self, neighborhood=None):
        """All bars, optionally filtered to one neighborhood. Returns a
        list of dict-like rows (supports row["column"] access)."""

    @abstractmethod
    def get_bars_by_ids(self, place_ids):
        """Bars matching the given place_ids, any order."""

    @abstractmethod
    def upsert_bar(self, bar):
        """Insert a bar, or update it in place if place_id already exists.
        `bar` is a dict covering every bars column except created_at/
        updated_at, which the repository fills in itself (created_at is
        preserved across updates, updated_at is set to now)."""

    @abstractmethod
    def update_bar_fields(self, place_id, fields):
        """Partial update -- only the given columns change. updated_at is
        set to now automatically."""

    @abstractmethod
    def bars_missing_content(self, neighborhood=None):
        """(rows, skipped_count) -- rows are bars with a website but no
        cicchetti_content yet; skipped_count is bars with a website that
        already have content."""

    @abstractmethod
    def bars_missing_tags(self):
        """Bars with no tags, or no blurb (covers bars tagged before the
        blurb field existed)."""

    @abstractmethod
    def bars_missing_instagram(self):
        """Bars with a website but no instagram_url yet."""


class IndexStore(ABC):
    """Vector search backing store. Only ids and embeddings are needed --
    documents/metadata were stored in the old ChromaDB setup but never
    actually read back anywhere in the app, so they're not part of this
    contract."""

    @abstractmethod
    def rebuild(self, ids, embeddings):
        """Replace the entire index with this set of (id, embedding)
        pairs. ids and embeddings are parallel lists."""

    @abstractmethod
    def count(self):
        """Number of embeddings currently indexed."""

    @abstractmethod
    def query(self, embedding, n_results, ids=None):
        """Nearest-neighbor place_ids to `embedding`, closest first. If
        `ids` is given, only those ids are considered."""
