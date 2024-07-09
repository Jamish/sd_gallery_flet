from typing import List
class TagCache:
    def __init__(self):
        self.__tag_index = {}  # Private inverted index

    def add(self, tag: str, filename: str):
        tag = tag.strip().lower()  # Normalize the tag (lowercase, trim whitespace)
        if tag not in self.__tag_index:
            self.__tag_index[tag] = []  # Create a new entry for the tag
        self.__tag_index[tag].append(filename)

    def get(self, tag: str) -> str:
        tag = tag.strip().lower()  # Normalize the tag
        return self.__tag_index.get(tag, [])  # Return an empty list if tag not found
    
        
    def get_all(self) -> List[str]:
        return list(self.__tag_index.keys())
