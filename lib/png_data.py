from dataclasses import dataclass, field

@dataclass
class PngData:
    favorite: bool = False
    checkpoint: str = ""
    loras: list[str] = None
    positive_prompt: str = ""
    negative_prompt: str = ""
    tags: list[str] = None
    thumbnail_base64: str = ""
    timestamp: float = ""
    raw_data: str = ""
    error: str = ""
    image_path: str = ""  # runtime only — derived from collection.directory_path + relative_path, not stored in DB
