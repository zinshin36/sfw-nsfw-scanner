import re
import unicodedata

def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text

def merge_unique_list(existing, new):
    combined = list(set(existing + new))
    return sorted(combined)
