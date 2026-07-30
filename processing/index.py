import db


def index_document(document_id, title, content):
    db.index_fts(document_id, title, content or "")


def related_documents(document_id, limit=10):
    return db.related_by_entities(document_id, limit=limit)
