def noteEntity(item) -> dict:
    return {
        "id": str(item["_id"]),
        "title": item["title"],
        "desc": item["desc"],
        "important": item["important"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"]
    }


def notesEntity(items) -> list:
    return [noteEntity(item) for item in items] 