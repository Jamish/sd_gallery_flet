from dataclasses import dataclass, field

@dataclass
class TagData:
    name: str = ""
    files: list[str] = None
    def count(self) -> int:
        return len(self.files)