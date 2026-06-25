import json
from dataclasses import dataclass, asdict, field
import os
import uuid
from typing import List


@dataclass
class ImageCollection:
    name: str
    directory_path: str
    id: str = ""


class Config:
    def __init__(self, data):
        self.simple_configs = {}
        self.simple_configs["slideshow_delay"] = 3000
        self.simple_configs["images_per_page"] = 128

        for key in self.simple_configs.keys():
            if key in data:
                self.simple_configs[key] = data[key]

    def serialize(self):
        return dict(self.simple_configs)


class Configurations:
    def __init__(self, cache_dir, config_filename, database):
        self.config_filename = config_filename
        self.cache_dir = cache_dir
        self.config_path = os.path.join(self.cache_dir, self.config_filename)
        self.database = database
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

    # --- Collections (backed by DB) ---

    def save_collection(self, collection: ImageCollection) -> ImageCollection:
        if not collection.id:
            collection.id = str(uuid.uuid4())
        self.database.save_collection(collection.id, collection.name, collection.directory_path)
        return collection

    def collection_exists(self, name: str) -> bool:
        return name in (c.name for c in self.get_collections())

    def get_collections(self) -> List[ImageCollection]:
        rows = self.database.get_collections()
        return [ImageCollection(id=r[0], name=r[1], directory_path=r[2]) for r in rows]

    def delete_collection(self, collection: ImageCollection):
        self.database.delete_collection(collection.id)

    # --- Simple key/value settings (backed by config.json) ---

    def get_config(self, key):
        return self.config.simple_configs[key]

    def set_config(self, key, value):
        self.config.simple_configs[key] = value
        self.__save()
