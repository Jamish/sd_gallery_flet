from dataclasses import asdict, dataclass
import json
import sqlite3
import os
import uuid
from contextlib import closing
from typing import Optional

from lib.png_data import PngData


@dataclass
class DiskCacheEntry:
    collection_id: str
    relative_path: str
    png_data: PngData


class Database:
    def __init__(self, cache_dir, database_filename):
        self.database_filename = database_filename
        self.cache_dir = cache_dir
        self.database_path = os.path.join(self.cache_dir, self.database_filename)
        self.__setup_schema()

    def __get_table_names(self, connection):
        rows = connection.cursor().execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {r[0] for r in rows}

    def __setup_schema(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = self.__get_table_names(connection)
            if 'images' in tables and 'collections' not in tables:
                print("Migrating database schema v1 → v2...")
                self.__migrate_v1_to_v2(connection)
            elif 'collections' not in tables:
                self.__create_schema(connection)

    def __create_schema(self, connection):
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                directory_path TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE images (
                collection_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                metadata BLOB,
                PRIMARY KEY (collection_id, relative_path),
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            )
        """)
        connection.commit()

    def __migrate_v1_to_v2(self, connection):
        config_path = os.path.join(self.cache_dir, "config.json")
        try:
            with open(config_path) as f:
                old_collections = json.load(f).get("collections", [])
        except FileNotFoundError:
            old_collections = []

        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                directory_path TEXT NOT NULL
            )
        """)

        # Insert old collections and build path → id map
        collection_map = {}
        for col in old_collections:
            col_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO collections VALUES (?, ?, ?)",
                           (col_id, col['name'], col['directory_path']))
            collection_map[col['directory_path']] = col_id

        old_rows = cursor.execute("SELECT image_path, metadata FROM images").fetchall()

        cursor.execute("""
            CREATE TABLE images_new (
                collection_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                metadata BLOB,
                PRIMARY KEY (collection_id, relative_path),
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            )
        """)

        migrated = 0
        skipped = 0
        for (image_path, metadata) in old_rows:
            # Find the longest-matching collection path for this image
            matched_col_id = None
            matched_col_path = None
            for col_path, col_id in collection_map.items():
                if image_path.startswith(col_path):
                    if matched_col_path is None or len(col_path) > len(matched_col_path):
                        matched_col_id = col_id
                        matched_col_path = col_path

            if matched_col_id is None:
                print(f"  Warning: no collection matched {image_path}, skipping")
                skipped += 1
                continue

            relative_path = os.path.relpath(image_path, matched_col_path)

            # Strip image_path from the stored BLOB
            try:
                meta_dict = json.loads(metadata)
                meta_dict.pop('image_path', None)
                metadata = json.dumps(meta_dict, indent=4)
            except Exception:
                pass

            cursor.execute("INSERT OR IGNORE INTO images_new VALUES (?, ?, ?)",
                           (matched_col_id, relative_path, metadata))
            migrated += 1

        cursor.execute("DROP TABLE images")
        cursor.execute("ALTER TABLE images_new RENAME TO images")
        connection.commit()
        print(f"Migration complete: {migrated} images migrated, {skipped} skipped.")

    # --- Collections (raw tuples — Configurator wraps these into ImageCollection) ---

    def save_collection(self, col_id: str, name: str, directory_path: str):
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("INSERT INTO collections VALUES (?, ?, ?)",
                               (col_id, name, directory_path))
                connection.commit()

    def get_collections(self) -> list:
        """Returns list of (id, name, directory_path) tuples."""
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                return cursor.execute(
                    "SELECT id, name, directory_path FROM collections"
                ).fetchall()

    def delete_collection(self, col_id: str):
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("DELETE FROM collections WHERE id = ?", (col_id,))
                connection.commit()

    # --- Images ---

    def get(self, collection_id: str, relative_path: str, collection_dir: str = "") -> Optional[PngData]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                rows = cursor.execute(
                    "SELECT metadata FROM images WHERE collection_id = ? AND relative_path = ?",
                    (collection_id, relative_path)
                ).fetchall()
                if not rows:
                    return None
                meta = json.loads(rows[0][0])
                meta['image_path'] = os.path.join(collection_dir, relative_path) if collection_dir else ""
                return PngData(**meta)

    def upsert(self, entry: DiskCacheEntry):
        meta = asdict(entry.png_data)
        meta.pop('image_path', None)  # derived at runtime, not stored
        metadata = json.dumps(meta, indent=4)
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "REPLACE INTO images VALUES (?, ?, ?)",
                    (entry.collection_id, entry.relative_path, metadata)
                )
                connection.commit()

    def delete_by_collection(self, collection_id: str):
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute("DELETE FROM images WHERE collection_id = ?", (collection_id,))
                connection.commit()

    def delete(self, collection_id: str, relative_path: str):
        with closing(sqlite3.connect(self.database_path)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "DELETE FROM images WHERE collection_id = ? AND relative_path = ?",
                    (collection_id, relative_path)
                )
                connection.commit()
