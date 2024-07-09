
from lib.png_data import PngData
from typing import List

class ImageCache:
    def __init__(self):
        self.__image_index = {}  # Private inverted index

    def set(self, filename: str, data: PngData):
        if filename not in self.__image_index:
            self.__image_index[filename] = data  # Create a new entry for the image
        # Implement merge logic

    def get(self, filename: str) -> PngData:
        return self.__image_index.get(filename, None) 
    
    def get_all(self) -> List[PngData]:
        return list(self.__image_index.values())
