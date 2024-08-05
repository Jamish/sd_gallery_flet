from dataclasses import dataclass, field

@dataclass
class PngData:
    image_path: str
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