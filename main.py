
import base64
from io import BytesIO
import pyperclip
import flet as ft
import os
import concurrent.futures
from PIL import Image
import json
from dataclasses import asdict, field
from functools import partial
from lib.database import DiskCacheEntry, Database

from lib.png_data import PngData
from lib.png_parser import PngParser
from lib.image_cache import ImageCache
from lib.tag_cache import TagCache
import lib.file_helpers as filez
import lib.image_helpers as imagez

print("hi")

executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)


def main(page: ft.Page):
    cache_dir = ".cache"
    os.makedirs(cache_dir, exist_ok=True)

    png_parser = PngParser()
    tag_cache = TagCache()
    image_cache = ImageCache()
    database = Database(cache_dir, "data.sqlite3")
    database.try_create_database()

    page.title = "Image Browser"
    
    def on_keyboard(e: ft.KeyboardEvent):
        if e.key == "Escape":
            if image_popup != None:
                close_image_popup(None)

    def pick_files_result(e: ft.FilePickerResultEvent):
        print(f"Selected path {e.path}")
        load_images_from_directory(e.path)

    def load_images_from_directory(dir_path):
        def process_image(filename):
            image_path = os.path.join(dir_path, filename)

            # Check the disk cache, otherwise parse it
            png_data = database.get(filename)
            should_update_disk_cache = False
            if png_data is None:
                print(".", end="")
                png_data = png_parser.parse(image_path)
                should_update_disk_cache = True

            # Save to memory cache                
            image_cache.set(image_path, png_data)
            for tag in png_data.tags:
                tag_cache.add(tag, image_path)

            # Save to disk cache
            cache_entry = DiskCacheEntry(
                filename=filename, 
                png_data=png_data
            )
            if (should_update_disk_cache):
                database.upsert(cache_entry)

            return image_path
        
        image_grid.controls.clear()  # Clear existing images

        # Submit image processing tasks to the thread pool
        futures = []
        file_list = os.listdir(dir_path)
        print(f"Loading {len(file_list)} images")
        for filename in file_list:
            if filename.lower().endswith((".png")):
                future = executor.submit(process_image, filename)
                futures.append(future)
        
        # Wait for results and collect image paths
        total = len(file_list)
        count = 0
        def process_completed_futures(futures):
            nonlocal count
            count += len(futures)
            print(f"\nProcessing: {100*count/total}%")
            image_paths = [f.result() for f in futures]
            add_to_gallery(image_paths)
        batch_size = 64
        completed_futures = []
        for future in concurrent.futures.as_completed(futures):
            completed_futures.append(future)
            if len(completed_futures) >= batch_size:
                process_completed_futures(completed_futures)
                completed_futures.clear()
        if completed_futures:
            process_completed_futures(completed_futures)

        # Update tags when everything is loaded
        tags = tag_cache.get_all()
        tag_buttons = [ft.ElevatedButton(f"{tag.name} ({tag.count()})", on_click=select_tag, data=tag) for tag in tags]
        tags_control.controls = tag_buttons
        tags_view.update()

    def add_to_gallery(image_paths):
        for image_path in image_paths:
            png_data = image_cache.get(image_path)
            if png_data is None:
                print(f"ERROR: png_data not found for {image_path}")
                continue
            entry = ft.Container(
                on_click=partial(create_image_popup, image_path),
                content=ft.Image(
                    src_base64=png_data.thumbnail_base64, 
                    fit=ft.ImageFit.COVER,
                    key=image_path,
                    border_radius=ft.border_radius.all(5)
                    )
            )
            image_grid.controls.append(entry)
        print(f"Added {len(image_paths)} images to gallery.")
        page.update()

    def load_gallery(image_paths):
        image_grid.controls.clear()  # Clear existing images
        add_to_gallery(image_paths)
        rail.selected_index = 0
        load_subview(0)

    selected_tags = []
    def deselect_tag(e):
        tag = e.control.data
        selected_tags = []
        filters_container.controls = selected_tags
        filters_container.update()
        paths = list(map(lambda image: image.filename, image_cache.get_all()));
        print(f"image cache length is {len(image_cache.get_all())}")
        print(f"Image path is {paths}")
        load_gallery(paths)

    def select_tag(e):
        tag = e.control.data
        print(f"Clicked tag {tag.name}")
        selected_tags = [ft.ElevatedButton(f"{tag.name}", icon=ft.icons.CLEAR_ROUNDED, on_click=deselect_tag, data=tag)]
        filters_container.controls = selected_tags
        filters_container.update()
        load_gallery(tag.files)

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(pick_files_dialog)

    filters_container = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=selected_tags,
        wrap=True,
        spacing=10,  # Spacing between buttons
        run_spacing=10,  # Spacing between rows
    )

    image_grid = ft.GridView(
        expand=True,
        runs_count=5,  # Adjust columns as needed
        max_extent=256,  # Adjust maximum image size as needed
        spacing=5,
        run_spacing=5,
        padding=ft.padding.only(right=15),
    )

    gallery_view = ft.Container(
        expand=True, 
        content=ft.Column(
        [
            filters_container,
            ft.Divider(height=1),
            image_grid
        ]
    )
    )
    
    
    temp_view = ft.Column(
        [
            ft.Container(
                content=ft.Text("Non clickable"),
                margin=10,
                padding=10,
                alignment=ft.alignment.center,
                bgcolor=ft.colors.AMBER,
                width=150,
                height=150,
                border_radius=10,
            )
        ]
    )


    tags_control = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=None,
        wrap=True,
        expand=True,
        spacing=10,  # Spacing between buttons
        run_spacing=10,  # Spacing between rows
    )
    tags_view = ft.Column(
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
        controls=[tags_control])

    image_popup = None

    def close_image_popup(e):
        nonlocal image_popup
        main_view.visible=True
        gallery_key_to_scroll_to = image_popup.data
        image_popup.visible = False
        image_popup = None
        page.update()
        image_grid.scroll_to(key=gallery_key_to_scroll_to)


    def create_image_popup(image_path, e):
        nonlocal image_popup
        
        image_data = image_cache.get(image_path)
        lora_fields = []
        i = 0
        for lora in image_data.loras:
            i += 1
            lora_fields.append(ft.TextField(label=f"LoRA #{i}", read_only=True, value=lora)),
                               
        content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY, 
            controls=[
                ft.Image(
                    expand=True,
                    src=image_path, 
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.VerticalDivider(width=1),
                ft.Container(
                    padding = 10,
                    width=384,
                    content = ft.Column(
                        alignment=ft.MainAxisAlignment.START,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        scroll=ft.ScrollMode.ALWAYS,
                        controls=[
                            ft.Container(height=10), # To give visual space from the top, for the floating X button
                            ft.TextField(label="Model Checkpoint", read_only=True, value=image_data.checkpoint),
                            *lora_fields,
                            ft.Container(height=5), # To separate LoRAs and prompts
                            ft.TextField(label="Positive Prompt", read_only=True, multiline=True, value=image_data.positive_prompt),
                            ft.ElevatedButton(text="Copy Positive Prompt", on_click=lambda _: pyperclip.copy(image_data.positive_prompt)),
                            ft.TextField(label="Negative Prompt", read_only=True, multiline=True,value=image_data.negative_prompt),
                            ft.ElevatedButton(text="Copy Negative Prompt", on_click=lambda _: pyperclip.copy(image_data.positive_prompt)),
                        ]
                    )
                )
            ]
        )

        should_add_popup = False
        if image_popup == None:
            should_add_popup = True

        image_popup = ft.Stack([
            content,
            ft.Row([
                ft.FloatingActionButton(
                    mini=True,
                    icon=ft.icons.CLEAR_ROUNDED,
                    on_click=close_image_popup,
                )
            ],
            alignment=ft.MainAxisAlignment.END)
        ], expand=True, data=image_path)

        if should_add_popup:
            page.add(image_popup)
        main_view.visible = False
        page.update()
        




    subviews = [gallery_view, tags_view, temp_view]


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
        on_change=lambda e: load_subview(e.control.selected_index),
    )

    def load_subview(index):
        print(f"load subview {index}")
        def get_page(i):
            if i >= len(subviews):
                return subviews[-1]
            return subviews[i]
        for subview in subviews:
            subview.visible = False
        get_page(index).visible = True
        subview.update()
        page.update()

    main_view = ft.Row(
        [
            rail,
            ft.VerticalDivider(width=1),
            *subviews
        ],
        expand=True,
    )
    page.add(main_view)
    load_subview(0)


    #load_images_from_directory("C:/Users/jamis/Data/SDImageBrowser/gallery")


    page.on_keyboard_event = on_keyboard
ft.app(target=main)
print("Shutting down worker threads...")
executor.shutdown(wait=True, cancel_futures=True)
print("Done! Adios!")