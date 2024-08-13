import json
from dataclasses import dataclass, asdict, field
import os

@dataclass
class ImageCollection:
    name: str
    directory_path: str

class Config:
    def __init__(self, data):
        self.collections = []
        self.slideshow_delay = 3000
        if "collections" in data:
            for collection_data in data['collections']:
                self.collections.append(ImageCollection(**collection_data))
        if "slideshow_delay" in data:
            self.slideshow_delay = data['slideshow_delay']

    def serialize(self):
        return {
            "collections": list(map(lambda x: asdict(x), self.collections)),
            "slideshow_delay": self.slideshow_delay
        }



class Configurations:
    def __init__(self, cache_dir, config_filename):
        self.config_filename = config_filename
        self.cache_dir = cache_dir
        self.config_path = os.path.join(self.cache_dir, self.config_filename)

        self.config = self.__load()

    def __load(self):
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                return Config(data)
        except FileNotFoundError:
            return Config({})
        

    def __save(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config.serialize(), f, indent=4)

    def save_collection(self, image_collection: ImageCollection):
        self.config.collections.append(image_collection)
        self.__save()

    def collection_exists(self, name):
        return name in map(lambda x: x.name, self.get_collections())
    
    def get_collections(self):
        return self.config.collections
    
    def delete_collection(self, image_collection: ImageCollection):
        for i, collection in enumerate(self.config.collections):
                if collection == image_collection:
                    del self.config.collections[i]
        self.__save()

    def get_slideshow_delay(self):
        return self.config.slideshow_delay

    def set_slideshow_delay(self, delay):
        self.config.slideshow_delay = delay
        self.__save()