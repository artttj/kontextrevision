import os


def write(tmp_path, rel, content=""):
    """Create a file at tmp_path/rel with content. Returns absolute path."""
    full = os.path.join(str(tmp_path), rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full
