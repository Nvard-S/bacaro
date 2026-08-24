import chromadb

from .interfaces import IndexStore

COLLECTION_NAME = "bars"


class ChromaIndexStore(IndexStore):
    def __init__(self, chroma_path):
        self.client = chromadb.PersistentClient(path=chroma_path)

    def _collection(self):
        return self.client.get_or_create_collection(COLLECTION_NAME)

    def rebuild(self, ids, embeddings):
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        collection = self.client.get_or_create_collection(COLLECTION_NAME)
        if ids:
            collection.add(ids=ids, embeddings=embeddings)

    def count(self):
        return self._collection().count()

    def query(self, embedding, n_results, ids=None):
        results = self._collection().query(
            query_embeddings=[embedding], n_results=n_results, ids=ids,
        )
        return results.get("ids", [[]])[0]
