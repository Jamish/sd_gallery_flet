
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
from controls.slideshow_button import SlideshowButton
from lib.configurator import Configurations, ImageCollection
from lib.database import DiskCacheEntry, Database

from lib.png_data import PngData
from lib.png_parser import PngParser
from lib.image_cache import ImageCache
from lib.tag_cache import TagCache
import lib.file_helpers as filez
import lib.image_helpers as imagez
from lib.tag_data import TagData
import threading


print("hi")

executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
stop_functions = []


def main(page: ft.Page):
    cache_dir = ".cache"
    os.makedirs(cache_dir, exist_ok=True)

    png_parser = PngParser()

    tag_cache = TagCache()
    image_cache = ImageCache()
    database = Database(cache_dir, "data.sqlite3")
    database.try_create_database()

    config = Configurations(cache_dir, "config.json")

    page.title = "Image Browser"
    
    def on_keyboard(e: ft.KeyboardEvent):


        # print(f"Key Pressed: {e.key}")
        if image_popup and image_popup.visible:
            if e.key == "Escape":
                close_image_popup(None)
            if e.key == "F":
                toggle_favorite(image_popup.data, None)
            if e.key == "Arrow Right" or e.key == "D":
                next_popup(1, None)
            if e.key == "Arrow Left" or e.key == "A":
                next_popup(-1, None)

    def next_popup(plus_or_minus_one, e):
        image_data = image_popup.data
        for i, entry in enumerate(current_image_grid.controls):
            if entry.data.image_path == image_data.image_path:
                next_index = (i+plus_or_minus_one) % len(current_image_grid.controls)
                print("Creating popup")
                create_image_popup(current_image_grid.controls[next_index].data.image_path, None)
                return
    slideshow_button = SlideshowButton(next_popup)
    stop_functions.append(slideshow_button.stop_slideshow)
        

    # def pick_files_result(e: ft.FilePickerResultEvent):
    #     print(f"Selected path {e.path}")
    #     load_images_from_directory(e.path)

    def save_png_data(png_data: PngData):
        cache_entry = DiskCacheEntry(
            image_path=png_data.image_path, 
            png_data=png_data
        )
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

        def get_all_files(dir_path):
            all_files = []
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    all_files.append(os.path.join(root, file))  # Get the full path
            return all_files
        # file_list = os.listdir(dir_path)
        file_list = get_all_files(dir_path)
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
            data=png_data
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

        image_grid.controls.sort(key=lambda x: x.data.timestamp, reverse=True)
        image_grid_favorites.controls.sort(key=lambda x: x.data.timestamp, reverse=True)

        page.update()

    def close_collection():
        nonlocal tag_cache
        nonlocal image_cache
        clear_gallery()
        tag_cache = TagCache()
        image_cache = ImageCache()
        clear_filter(None)
        clear_selected_tags(None)

    def clear_gallery():
        image_grid.controls.clear()  # Clear existing images
        image_grid_favorites.controls.clear()  # Clear existing images
 
    def go_to_gallery_view():
        rail.selected_index = 1
        rail.update()
        load_subview(1)

    def load_gallery(image_paths):
        clear_gallery()
        add_to_gallery(image_paths)
        go_to_gallery_view()

    selected_tag_buttons = []
    selected_files = []
    def clear_selected_tags(e):
        selected_tag_buttons.clear()
        selected_files.clear()
        filters_container.controls = selected_tag_buttons
        filters_container.update()

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
            clear_selected_tags(e)
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


    def open_collection(collection: ImageCollection, e):
        close_collection()
        go_to_gallery_view()
        load_images_from_directory(collection.directory_path)

    def delete_collection(collection: ImageCollection, e):
        close_collection()
        for i, collection_widget in enumerate(collection_grid.controls):
                if collection_widget.data == collection:
                    del collection_grid.controls[i]
        collection_grid.update()
        config.delete_collection(collection)
        # TODO This would be avoided if I just used different Database files for each gallery
        database.delete_by_prefix(collection.directory_path)



    def create_collection_widget(collection: ImageCollection):
        print("Creating collection!")
        print(collection)

        def handle_confirm(e):
            delete_collection(collection, None)
            page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Delete {collection.name}"),
            content=ft.Text(f"Do you really want to delete collection {collection.name}, including favorites?"),
            actions=[
                ft.TextButton("Yes", on_click=handle_confirm),
                ft.TextButton("No", on_click=lambda e: page.close(dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        return ft.Container(
                data=collection,
                expand=True,
                content=ft.Column([
                    ft.Text(collection.name),
                    ft.Row([
                        ft.FilledButton(
                            text="Open",
                            icon=ft.icons.FOLDER_OPEN,
                            on_click=partial(open_collection, collection)
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE_FOREVER,
                            on_click=lambda e: page.open(dialog)
                        )
                    ])
                ])
            )
    def open_new_collection_popup(e):
        def handle_create(e):
            name = input_name.value.strip()
            folder = input_folder.value
            has_errors = False
            # TODO CHeck if name already exists
            if name == "":
                input_name.error_text = "Required!"
                input_name.update()
                has_errors = True
            if config.collection_exists(name):
                input_name.error_text = "That name already exists!"
                input_name.update()
                has_errors = True
            
            if folder is None:
                input_folder.value = "Choose a folder first!"
                input_folder.update()
                has_errors = True
            if has_errors:
                return

            page.close(dlg_modal)

            collection = ImageCollection(name, folder)
            config.save_collection(collection)
            collection_widget = create_collection_widget(collection)
            collection_grid.controls.append(collection_widget)
            collection_grid.update()


        def select_folder(e):
            def select_folder_result(e: ft.FilePickerResultEvent):
                input_folder.value = e.path
                input_folder.update()
            pick_files_dialog = ft.FilePicker(on_result=select_folder_result)
            page.overlay.append(pick_files_dialog)
            page.update()
            pick_files_dialog.get_directory_path(
                dialog_title="Open Image Folder", 
                initial_directory=os.getcwd()
            )

        input_name = ft.TextField(label="Name")
        input_folder = ft.Text("")
        text_errors = ft.Text()
        dlg_modal = ft.AlertDialog(
            title=ft.Text("New Collection"),
            content=ft.Column([
                input_name,
                ft.Row([
                    ft.FilledButton(
                        text="Choose",
                        icon=ft.icons.FOLDER_OPEN, 
                        on_click=select_folder
                    ),
                    input_folder,
                ]),
                text_errors,
            ]),
            actions=[
                ft.TextButton("Create", on_click=handle_create),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Closed")
        )


        page.open(dlg_modal)

    collection_grid = ft.GridView(
        expand=True,
        runs_count=5,  # Adjust columns as needed
        max_extent=256,  # Adjust maximum image size as needed
        spacing=5,
        run_spacing=5,
        padding=ft.padding.only(right=15),
    )
    collection_view = ft.Container(
        expand=True,
        content=collection_grid
    )
    new_collection_button = ft.FloatingActionButton(
        icon=ft.icons.ADD_BOX_OUTLINED,
        text="New Collection",
        on_click=open_new_collection_popup
    )
    collection_grid.controls.append(new_collection_button)

    for collection in config.get_collections():
        collection_grid.controls.append(create_collection_widget(collection))


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
    current_image_grid = image_grid

    
    async def zoom_slider_update(grid, e):
        grid.max_extent = e.control.value
        page.update()

    gallery_view = ft.Container(
        expand=True, 
        content=ft.Column([
            filters_container,
            ft.Divider(height=1),
            image_grid,
            ft.Slider(min=64, max=512, value=256, label="{value}px", on_change=partial(zoom_slider_update, image_grid)),
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
            image_grid_favorites,
            ft.Slider(min=64, max=512, value=256, label="{value}px", on_change=partial(zoom_slider_update, image_grid_favorites)),
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
    


    ## TODO Use page.overlay instead of your own stack, dummy
    image_popup = None

    def close_image_popup(e):
        nonlocal image_popup
        image_popup.visible = False
        slideshow_button.stop_slideshow()
        page.update()

    favorites_button = None

    def toggle_favorite(image_data: PngData, e):
        image_data.favorite = not image_data.favorite

        save_png_data(image_data)

        favorites_button.selected = image_data.favorite

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
        
        sidebar_controls = [
            ft.Container(height=10), # To give visual space from the top, for the floating X button
        ]
        if image_data.checkpoint:
            sidebar_controls.append(ft.TextField(label="Model Checkpoint", read_only=True, value=image_data.checkpoint))
        sidebar_controls.extend(lora_fields)
        sidebar_controls.append(ft.Container(height=5))
        if image_data.positive_prompt:
            sidebar_controls.extend([
                ft.TextField(label="Positive Prompt", read_only=True, multiline=True, value=image_data.positive_prompt),
                ft.ElevatedButton(text="Copy Positive Prompt", on_click=lambda _: pyperclip.copy(image_data.positive_prompt)),
            ])
        if image_data.negative_prompt:
            sidebar_controls.extend([
                ft.TextField(label="Negative Prompt", read_only=True, multiline=True, value=image_data.negative_prompt),
                ft.ElevatedButton(text="Copy Negative Prompt", on_click=lambda _: pyperclip.copy(image_data.positive_prompt)),
            ])
        if image_data.raw_data:
            sidebar_controls.extend([
                ft.TextField(label="Raw Data", read_only=True, multiline=True, value=image_data.raw_data)
            ])
        if image_data.error:
            sidebar_controls.extend([
                ft.TextField(label="Error", read_only=True, multiline=True, value=image_data.error)
            ])

                               
        content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY, 
            controls=[
                ft.Container(
                    content = ft.Stack([
                        ft.Image(
                            expand=True,
                            src_base64=image_data.thumbnail_base64, 
                            fit=ft.ImageFit.CONTAIN,
                        ),
                        ft.Image(
                            expand=True,
                            src=image_path, 
                            fit=ft.ImageFit.CONTAIN,
                        ),
                    ], expand=True, fit=ft.StackFit.EXPAND),
                    expand=True,
                    alignment=ft.alignment.center,
                ),
                ft.VerticalDivider(width=1),
                ft.Container(
                    padding = 10,
                    width=384,
                    content = ft.Column(
                        alignment=ft.MainAxisAlignment.START,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        scroll=ft.ScrollMode.ALWAYS,
                        controls=sidebar_controls,
                    )
                )
            ]
        )

        favorites_button = ft.IconButton(
            icon=ft.icons.FAVORITE_BORDER,
            selected_icon=ft.icons.FAVORITE,
            selected=image_data.favorite,
            icon_color=ft.colors.PINK_100,
            selected_icon_color=ft.colors.PINK_300,
            on_click=partial(toggle_favorite, image_data),
        )

        image_popup = ft.Container(
            ft.Stack([
                content,
                ft.Column([
                    ft.Row([
                        favorites_button,
                        ft.FloatingActionButton(
                            mini=True,
                            icon=ft.icons.CLEAR_ROUNDED,
                            on_click=close_image_popup,
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.IconButton(
                            icon=ft.icons.ARROW_CIRCLE_LEFT_ROUNDED,
                            icon_color=ft.colors.BLUE_300,
                            # visual_density=ft.ThemeVisualDensity.COMPACT,
                            on_click=partial(next_popup, -1),
                        ),
                        slideshow_button.new_button(),
                        ft.IconButton(
                            icon=ft.icons.ARROW_CIRCLE_RIGHT_ROUNDED,
                            icon_color=ft.colors.BLUE_300,
                            on_click=partial(next_popup, 1),
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ], expand=True, data=image_path),
            bgcolor=ft.colors.BACKGROUND,
            data=image_data
        )

        page_stack.controls = [main_view, image_popup]
        page.update()
        




    subviews = [collection_view, gallery_view, tags_view, favorites_view, temp_view]


    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        # extended=True,
        min_width=100,
        min_extended_width=400,
        # leading=ft.FloatingActionButton(
        #     icon=ft.icons.FOLDER_OPEN, 
        #     text="Open Gallery", 
        #     on_click=lambda _: pick_files_dialog.get_directory_path(
        #         dialog_title="Open Image Folder", 
        #         initial_directory=os.getcwd()
        #     ),
        # ),
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon_content=ft.Icon(ft.icons.FOLDER_COPY_OUTLINED),
                selected_icon_content=ft.Icon(ft.icons.FOLDER_COPY_ROUNDED),
                label="Collections",
            ),
            ft.NavigationRailDestination(
                icon_content=ft.Icon(ft.icons.GRID_VIEW_OUTLINED),
                selected_icon_content=ft.Icon(ft.icons.GRID_VIEW_SHARP),
                label="Images",
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
        nonlocal current_image_grid
        print(f"load subview {index}")
        def get_page(i):
            if i >= len(subviews):
                return subviews[-1]
            return subviews[i]
        for subview in subviews:
            subview.visible = False

        current_subview = get_page(index)
        current_subview.visible = True

        if current_subview == gallery_view:
            current_image_grid = image_grid
        if current_subview == favorites_view:
            current_image_grid = image_grid_favorites

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
for stop_func in stop_functions:
    stop_func()
print("Done! Adios!")