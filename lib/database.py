from dataclasses import asdict, dataclass
import json
import sqlite3
import os
from contextlib import closing

from lib.png_data import PngData
from PIL import Image

@dataclass
class CacheEntry:
    filename: str
    png_data: PngData
    thumbnail: Image


class Database:
    def __init__(self, cache_dir, database_filename):
        self.database_filename = database_filename
        self.cache_dir = cache_dir
        self.database_path = os.path.join(self.cache_dir, self.database_filename)

        self.try_create_database()

    def try_create_database(self):
        if (os.path.exists(self.database_path)):
            return
        
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("CREATE TABLE images (filename TEXT, thumbnail BLOB, metadata TEXT)")

                # for image_path, thumbnail_path in zip(image_paths, thumbnail_paths):
                #     with open(thumbnail_path, "rb") as f:
                #         thumbnail_data = f.read()
                #     with open(change_extension_to_json(image_path), "r") as f:
                #         metadata = f.read()
                #     cursor.execute("INSERT INTO images VALUES (?, ?, ?)", (os.path.basename(image_path), thumbnail_data, metadata))

    def upsert(self, data: CacheEntry):
        print(data)
        thumbnail_bytes = data.thumbnail.tobytes("xbm", "rgb")
        print(thumbnail_bytes)
        metadata = json.dumps(asdict(data.png_data), indent=4)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("INSERT INTO images VALUES (?, ?, ?)", (data.filename, metadata, thumbnail_bytes))
                connection.commit()

        print("wait)")
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                rows = cursor.execute("SELECT filename, thumbnail, metadata FROM images").fetchall()
                print(rows)