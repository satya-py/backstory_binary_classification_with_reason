import pathway as pw


def load_novels_from_sources(sources: pw.Table) -> pw.Table:
    """
    Convert raw text file sources into normalized novel documents.

    Expected Pathway file schema:
    - data       -> full text content
    - _metadata  -> file metadata (path, size, etc.)
    """

    available_cols = set(sources.schema.keys())

    # ---- Validate ----
    if "data" not in available_cols:
        raise ValueError(
            f"'sources' table must contain a 'data' column. "
            f"Found columns: {available_cols}"
        )

    # ---- Normalize ----
    novels = sources.select(
        text=sources.data,                       # FULL NOVEL TEXT
        source=pw.this._metadata["path"],        # filename
        metadata=sources._metadata               # keep full metadata
    )

    return novels
