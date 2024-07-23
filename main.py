
import base64
from io import BytesIO
from typing import List
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
from lib.tag_data import TagData

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
        print(f"Key Pressed: {e.key}")
        if e.key == "Escape":
            if image_popup != None:
                close_image_popup(None)
        if e.key == "F":
            if image_popup != None:
                toggle_favorite(image_popup.data, None)

    def pick_files_result(e: ft.FilePickerResultEvent):
        print(f"Selected path {e.path}")
        load_images_from_directory(e.path)

    def save_png_data(png_data: PngData):
        cache_entry = DiskCacheEntry(
            image_path=png_data.image_path, 
            png_data=png_data
        )
        print(f"Saving {png_data.image_path}")
        database.upsert(cache_entry)

    def load_images_from_directory(dir_path):
        def process_image(filename):
            image_path = os.path.join(dir_path, filename)

            # Check the disk cache, otherwise parse it
            png_data = database.get(image_path)
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
            if (should_update_disk_cache):
                save_png_data(png_data)

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
        show_tag_buttons(tags)

    def create_image_gallery_entry(png_data: PngData):
        image_path=png_data.image_path
        return ft.Container(
            on_click=partial(create_image_popup, image_path),
            content=ft.Image(
                src_base64=png_data.thumbnail_base64, 
                fit=ft.ImageFit.COVER,
                key=image_path,
                border_radius=ft.border_radius.all(5)
                ),
            data=image_path
        )

    def add_to_gallery(image_paths):
        for image_path in image_paths:
            png_data = image_cache.get(image_path)
            if png_data is None:
                print(f"ERROR: png_data not found for {image_path}")
                continue
            image_grid.controls.append(create_image_gallery_entry(png_data))
            if png_data.favorite:
                image_grid_favorites.controls.append(create_image_gallery_entry(png_data))
        print(f"Added {len(image_paths)} images to gallery.")
        page.update()

    def load_gallery(image_paths):
        image_grid.controls.clear()  # Clear existing images
        add_to_gallery(image_paths)
        rail.selected_index = 0
        load_subview(0)

    selected_tag_buttons = []
    selected_files = []
    def deselect_tag(e):
        nonlocal selected_tag_buttons
        nonlocal selected_files
        tag = e.control.data
        # Remove the clicked button from the filters list
        for button in selected_tag_buttons:
            print(f"Current Buttons: {button.data.name}")
            print(f"looking for: {tag.name}")
        selected_tag_buttons = [button for button in selected_tag_buttons if button.data.name != tag.name]
        
        all_files = list(map(lambda image: image.image_path, image_cache.get_all()));
        if len(selected_tag_buttons) == 0:
            # Last filter removed.
            selected_tag_buttons.clear()
            selected_files.clear()
            filters_container.controls = selected_tag_buttons
            filters_container.update()
            load_gallery(all_files)

        else:
            # Re-filter the master file list against each seleted tag 
            selected_tags = [button.data for button in selected_tag_buttons]
            for tag in selected_tags:
                selected_files = [file for file in all_files if file in tag.files]
            filters_container.controls = selected_tag_buttons
            filters_container.update()
            load_gallery(selected_files)

    def select_tag(e):
        nonlocal selected_files
        tag = e.control.data
        print(f"Clicked tag {tag.name}")
        selected_tag_buttons.append(ft.ElevatedButton(f"{tag.name}", icon=ft.icons.CLEAR_ROUNDED, on_click=deselect_tag, data=tag))
        print(f"Seleted tags: {len(selected_tag_buttons)}")
        filters_container.controls = selected_tag_buttons
        filters_container.update()

        if len(selected_tag_buttons) == 1:
            selected_files.extend(tag.files)
        else:
            selected_files = [file for file in selected_files if file in tag.files]
        load_gallery(selected_files)

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(pick_files_dialog)

    filters_container = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=selected_tag_buttons,
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
        content=ft.Column([
            filters_container,
            ft.Divider(height=1),
            image_grid
        ])
    )

    image_grid_favorites = ft.GridView(
        expand=True,
        runs_count=5,  # Adjust columns as needed
        max_extent=256,  # Adjust maximum image size as needed
        spacing=5,
        run_spacing=5,
        padding=ft.padding.only(right=15),
    )

    favorites_view = ft.Container(
        expand=True, 
        content=ft.Column([
            image_grid_favorites
        ])
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

    def show_tag_buttons(tags: List[TagData]):
        tag_controls["models"].controls.clear()
        tag_controls["loras"].controls.clear()
        tag_controls["tags"].controls.clear()
        tag_buttons = [ft.ElevatedButton(f"{tag.name} ({tag.count()})", on_click=select_tag, data=tag) for tag in tags]
        for tag_button in tag_buttons:
            if tag_button.data.name.startswith("model:"):
                tag_controls["models"].controls.append(tag_button)
            elif tag_button.data.name.startswith("lora:"):
                tag_controls["loras"].controls.append(tag_button)
            else:
                tag_controls["tags"].controls.append(tag_button)
        tags_view.update()

    async def update_tag_filter(e):
        filter = e.control.value
        tags = tag_cache.get_all()
        matched_tags = [tag for tag in tags if filter in tag.name]
        show_tag_buttons(matched_tags)
        
    def clear_filter(e):
        nonlocal tag_filter_textfield
        tag_filter_textfield.value = ""
        show_tag_buttons(tag_cache.get_all())
        page.update()


    def make_tags_button_row():
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=None,
            wrap=True,
            expand=True,
            scroll=ft.ScrollMode.ALWAYS,
            spacing=10,  # Spacing between buttons
            run_spacing=10,  # Spacing between rows
        )
    tag_controls = {
        "models": make_tags_button_row(),
        "loras": make_tags_button_row(),
        "tags": make_tags_button_row(),
    }
    
    tag_filter_textfield =  ft.TextField(label="Filter...", on_change=update_tag_filter)
    tags_view = ft.Column(
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        expand=True,
        controls=[
            ft.Container(height=10),
            ft.Row([
                tag_filter_textfield,
                ft.IconButton(
                    icon=ft.icons.CLEAR_ROUNDED,
                    icon_color="blue400",
                    icon_size=20,
                    on_click=clear_filter
                ),
            ]),
            # TODO Move these to a collapsible section?
            ft.Tabs(
                selected_index=0,
                animation_duration=100,
                expand=True,
                tabs=[
                    ft.Tab(
                        text="Tags",
                        content=tag_controls["tags"],
                    ),
                    ft.Tab(
                        text="Loras",
                        content=tag_controls["loras"],
                    ),
                    ft.Tab(
                        text="Models",
                        content=tag_controls["models"],
                    ),
                ],
            )
        ])
    
    


    image_popup = None

    def close_image_popup(e):
        nonlocal image_popup
        image_popup.visible = False
        image_popup = None
        page.update()

    favorites_button = None

    def toggle_favorite(image_data: PngData, e):
        image_data.favorite = not image_data.favorite

        favorite_icon = ft.icons.FAVORITE_BORDER
        if image_data.favorite:
            favorite_icon = ft.icons.FAVORITE
        save_png_data(image_data)

        favorites_button.icon = favorite_icon

        if image_data.favorite:
            image_grid_favorites.controls.append(create_image_gallery_entry(image_data))
        else:
            for i, entry in enumerate(image_grid_favorites.controls):
                if entry.data == image_data.image_path:
                    del image_grid_favorites.controls[i]

        image_grid_favorites.update()
        favorites_button.update()
        page.update()


    def create_image_popup(image_path, e):
        nonlocal image_popup
        nonlocal favorites_button
        
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

        favorite_icon = ft.icons.FAVORITE_BORDER
        if image_data.favorite:
            favorite_icon = ft.icons.FAVORITE

        should_add_popup = False
        if image_popup == None:
            should_add_popup = True

        favorites_button = ft.IconButton(
            icon=favorite_icon,
            on_click=partial(toggle_favorite, image_data),
        )

        image_popup = ft.Container(
            ft.Stack([
                content,
                ft.Row([
                    favorites_button,
                    ft.FloatingActionButton(
                        mini=True,
                        icon=ft.icons.CLEAR_ROUNDED,
                        on_click=close_image_popup,
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                # ft.Row([
                    
                # ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.END, expand=True)
            ], expand=True, data=image_path),
            bgcolor=ft.colors.BACKGROUND,
            data=image_data
        )

        if should_add_popup:
            page_stack.controls.append(image_popup)
        page.update()
        




    subviews = [gallery_view, tags_view, favorites_view, temp_view]


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
    page_stack = ft.Stack([main_view], expand=True)
    page.add(page_stack)
    load_subview(0)


    #load_images_from_directory("C:/Users/jamis/Data/SDImageBrowser/gallery")


    page.on_keyboard_event = on_keyboard
ft.app(target=main)
print("Shutting down worker threads...")
executor.shutdown(wait=True, cancel_futures=True)
print("Done! Adios!")