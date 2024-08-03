from dataclasses import asdict, dataclass
import json
import sqlite3
import os
from contextlib import closing

from lib.png_data import PngData
from PIL import Image

@dataclass
class DiskCacheEntry:
    image_path: str
    png_data: PngData


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
                cursor.execute("CREATE TABLE images (image_path TEXT PRIMARY KEY, metadata BLOB)")

    def get(self, image_path: str) -> PngData:
         with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                rows = cursor.execute("SELECT image_path, metadata FROM images WHERE image_path = ?", (image_path,)).fetchall()
                if len(rows) == 0:
                    return None
                json_metadata = json.loads(rows[0][1])
                return PngData(**json_metadata)

    def upsert(self, data: DiskCacheEntry):
        metadata = json.dumps(asdict(data.png_data), indent=4)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("REPLACE INTO images VALUES (?, ?)", (data.image_path, metadata))
                connection.commit()

    def delete_by_prefix(self, directory):
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("DELETE FROM images WHERE image_path LIKE ?", (directory + '%',))
                connection.commit()
