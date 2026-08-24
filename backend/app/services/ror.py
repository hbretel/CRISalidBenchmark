_ROR_PREFIX = "https://ror.org/"


def normalize_ror(ror_id: str | None) -> str | None:
    """Strip the https://ror.org/ prefix if present. Convention: stored bare.

    leiden_snapshot.ror_id is always stored bare (see leiden_sync.import_leiden_xlsx).
    instance_config.ror_id is stored exactly as OpenAlex returns it — a full
    "https://ror.org/..." URI (see api/config.py, institution.get("ror")).
    Any comparison between the two must normalize both sides through this
    function first, or it will silently never match.
    """
    if not ror_id:
        return None
    ror_id = ror_id.strip()
    if ror_id.startswith(_ROR_PREFIX):
        return ror_id[len(_ROR_PREFIX):]
    return ror_id
