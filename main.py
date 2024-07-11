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


    def pick_files_result(e: ft.FilePickerResultEvent):
        print(f"Selected path {e.path}")
        load_images_from_directory(e.path)

    def load_images_from_directory(dir_path):
        image_paths = []
        for filename in os.listdir(dir_path):
            if filename.lower().endswith((".png")):
                image_path = os.path.join(dir_path, filename)
                png_data = png_parser.parse(image_path)
                for tag in png_data.tags:
                    tag_cache.add(tag, image_path)
                image_paths.append(image_path)
        tags = tag_cache.get_all()
        tag_buttons = [ft.ElevatedButton(f"{tag.name} ({tag.count()})", on_click=select_tag, data=tag) for tag in tags]
        tags_view.controls = tag_buttons
        tags_view.update()
        load_gallery(image_paths)

    def load_gallery(image_paths):
        image_grid.controls.clear()  # Clear existing images
        for image_path in image_paths:
            image_grid.controls.append(ft.Image(src=image_path, fit="cover"))
        page.update()

    def select_tag(e):
        tag = e.control.data
        print(f"Clicked tag {tag.name}")
        load_gallery(tag.files)

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(pick_files_dialog)


    image_grid = ft.GridView(
        expand=1,
        runs_count=5,  # Adjust columns as needed
        max_extent=256,  # Adjust maximum image size as needed
        spacing=5,
        run_spacing=5,
    )
    
    temp_view = ft.Container(
        content=ft.Text("Non clickable"),
        margin=10,
        padding=10,
        alignment=ft.alignment.center,
        bgcolor=ft.colors.AMBER,
        width=150,
        height=150,
        border_radius=10,
    )

    tag_buttons = [ft.ElevatedButton(f"Button {i}") for i in range(20)]  # Create 20 buttons
    tags_view = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=1,
        expand_loose=True,
        controls=tag_buttons,
        wrap=True,
        spacing=10,  # Spacing between buttons
        run_spacing=10,  # Spacing between rows
    )
    views = [image_grid, tags_view, temp_view]


    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        # extended=True,
        min_width=100,
        min_extended_width=400,
        leading=ft.FloatingActionButton(
            icon=ft.icons.FOLDER_OPEN, 
            text="Open Gallery", 
            on_click=lambda _: pick_files_dialog.get_directory_path(
                dialog_title="Open Image Folder", 
                initial_directory=os.getcwd()
            ),
        ),
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon_content=ft.Icon(ft.icons.GRID_VIEW_OUTLINED),
                selected_icon_content=ft.Icon(ft.icons.GRID_VIEW_SHARP),
                label="Gallery",
            ),
            ft.NavigationRailDestination(
                icon_content=ft.Icon(ft.icons.BOOKMARK_BORDER),
                selected_icon_content=ft.Icon(ft.icons.BOOKMARK),
                label="Tags",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.FAVORITE_BORDER, selected_icon=ft.icons.FAVORITE, label="Favorites"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SETTINGS_OUTLINED,
                selected_icon_content=ft.Icon(ft.icons.SETTINGS),
                label_content=ft.Text("Settings"),
            ),
        ],
        on_change=lambda e: load_view(e.control.selected_index),
    )

    def load_view(index):
        print(f"load view {index}")
        def get_page(i):
            match i:
                case 0:
                    return image_grid
                case 1:
                    return tags_view
                case _:
                    return temp_view
        for view in views:
            view.visible = False
        get_page(index).visible = True
        page.update()

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                *views
            ],
            expand=True,
        )
    )
    load_view(0)


ft.app(target=main)
print("die")