from dataclasses import dataclass, field

@dataclass
class PngData:
    filename: str
    tags: list[str] = None
    positive_prompt: str = ""
    negative_prompt: str = ""
    checkpoint: str = ""
    loras: list[str] = None
    thumbnail_base64: str = ""
    favorite: bool = False