from typing import List

from lib.tag_data import TagData
class TagCache:
    def __init__(self):
        self.__tag_index = {} 

    def add(self, tag: str, filename: str):
        tag = tag.strip().lower()  
        if tag not in self.__tag_index:
            self.__tag_index[tag] = TagData(name=tag, files=[])  
        self.__tag_index[tag].files.append(filename) # TODO Use a dictionary/set

    def get(self, tag: str) -> str:
        tag = tag.strip().lower()  
        return self.__tag_index.get(tag, [])  
    
        
    def get_all(self) -> List[TagData]:
        tags = list(self.__tag_index.values())
        tags.sort(key=lambda x: x.count(), reverse=True)
        return tags
