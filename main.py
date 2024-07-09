# pip install flet

import flet as ft
import os

from lib.png_parser import PngParser
from lib.image_cache import ImageCache
from lib.tag_cache import TagCache
print("hi")
def main(page: ft.Page):
    png_parser = PngParser()
    tag_cache = TagCache()
    image_cache = ImageCache()

    page.title = "Image Browser"
    image_grid = ft.GridView(
        expand=1,
        runs_count=5,  # Adjust columns as needed
        max_extent=256,  # Adjust maximum image size as needed
        spacing=5,
        run_spacing=5,
    )
    

    def pick_files_result(e: ft.FilePickerResultEvent):
        print(f"Selected path {e.path}")
        load_images_from_directory(e.path)
    
    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(pick_files_dialog)

    def load_images_from_directory(dir_path):
        image_grid.controls.clear()  # Clear existing images
        for filename in os.listdir(dir_path):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                image_path = os.path.join(dir_path, filename)
                png_data = png_parser.parse(image_path)
                for tag in png_data.tags:
                    tag_cache.add(tag, image_path)
                print(png_data.positive_prompt)
                image_grid.controls.append(ft.Image(src=image_path, fit="cover"))
        page.update()

    page.add(
        ft.ElevatedButton(
            "Open Image Directory", 
            on_click=lambda _: pick_files_dialog.get_directory_path(
                dialog_title="Open Image Folder", 
                initial_directory=os.getcwd()
            )
        ),
        image_grid,
    )

ft.app(target=main)
print("die")