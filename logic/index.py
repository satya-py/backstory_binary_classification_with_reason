import pathway as pw
from pathway.xpacks.llm.document_store import DocumentStore


class SimpleDoc:
    def __init__(self, text: str):
        self.text = text


class SynchronousDocumentStore:
    """
    Stable Pathway-compatible synchronous wrapper
    """

    def __init__(self, store: DocumentStore):
        self.store = store

    def retrieve(self, query: str, k: int = 5):
        try:
            # Query the document store
            result_table = self.store.query(query, k=k)

            # Wait for results and convert to list
            rows = list(pw.iterate(result_table))

            docs = []
            for row in rows:
                # Extract text from the row
                text = ""
                if hasattr(row, 'text'):
                    text = row.text
                elif hasattr(row, 'chunk'):
                    text = row.chunk
                elif isinstance(row, dict):
                    text = row.get('text') or row.get('chunk') or ""
                
                if text:
                    docs.append(SimpleDoc(text))

            return docs

        except Exception as e:
            print(f"⚠ Retrieval failed: {e}")
            return []