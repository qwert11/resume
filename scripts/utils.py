from pathlib import Path
import yaml

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def has_any_tag(item_tags, target_tags):
    item_tags = set(item_tags or [])
    target_tags = set(target_tags or [])
    return bool(item_tags.intersection(target_tags))

def filter_items(items, target_tags):
    if "full" in target_tags:
        return items
    return [item for item in items if has_any_tag(item.get("tags", []), target_tags)]

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
