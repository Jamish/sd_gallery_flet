from functools import partial
import random
import threading
import flet as ft

from lib.configurator import Configurations
from lib.image_cache import ImageCache
from lib.png_data import PngData

SORT_DATE_DESC = "Date: Newest First"
SORT_DATE_ASC = "Date: Oldest First"
SORT_SHUFFLE = "Shuffle"

SORT_DEFAULT = SORT_DATE_DESC


class ImageGallery:
    def __init__(self, page: ft.Page, filters_container, func_create_image_popup):
        self.page = page
        self.func_create_image_popup = func_create_image_popup
        self.selected_sort = SORT_DEFAULT

        self.grid = ft.GridView(
            expand=True,
            runs_count=5,  # Adjust columns as needed
            max_extent=256,  # Adjust maximum image size as needed
            spacing=5,
            run_spacing=5,
            padding=ft.padding.only(right=15),
        )


        optional = []
        if filters_container:
            optional = [filters_container]
            
        self.view = ft.Container(
            expand=True, 
            content=ft.Column([
                *optional,
                self.grid,
                self.__create_bottom_bar()
            ])
    )

    def __create_bottom_bar(self):
        return ft.Row([
            ft.Slider(min=64, max=512, value=256, divisions=7, label="{value}px", on_change=self.zoom_slider_update, expand=True),
            ft.Dropdown(
                label="Sort By",
                width=200,
                on_change=partial(self.change_sort),
                value=SORT_DATE_DESC,
                options=[
                    ft.dropdown.Option(SORT_DATE_DESC),
                    ft.dropdown.Option(SORT_DATE_ASC),
                    ft.dropdown.Option(SORT_SHUFFLE),
                ],
            )
        ])
    

    def clear(self):
        self.grid.controls.clear()

    def add_image(self, png_data):
        image_path=png_data.image_path
        container = ft.Container(
            on_click=partial(self.func_create_image_popup, image_path),
            content=ft.Image(
                src_base64=png_data.thumbnail_base64, 
                fit=ft.ImageFit.COVER,
                key=image_path,
                border_radius=ft.border_radius.all(5)
                ),
            data=png_data
        )
        self.grid.controls.insert(0, container)

    async def zoom_slider_update(self, e):
        self.grid.max_extent = e.control.value
        self.page.update()

    def change_sort(self, e):
        self.selected_sort = e.data
        self.sort()
        return
    
    def sort(self):
        if self.selected_sort == SORT_DATE_DESC:
            self.grid.controls.sort(key=lambda x: x.data.timestamp, reverse=True)
        elif self.selected_sort == SORT_DATE_ASC:
            self.grid.controls.sort(key=lambda x: x.data.timestamp, reverse=False)
        elif self.selected_sort == SORT_SHUFFLE:
            random.shuffle(self.grid.controls)
        else:
            print(f"Invalid sort selection {self.selected_sort}")
        self.grid.update()