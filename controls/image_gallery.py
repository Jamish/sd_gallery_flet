from functools import partial
import random
import threading
import math
import flet as ft

SORT_DATE_DESC = "Date: Newest First"
SORT_DATE_ASC = "Date: Oldest First"
SORT_SHUFFLE = "Shuffle"

SORT_DEFAULT = SORT_DATE_DESC


class ImageGallery:
    def __init__(self, page: ft.Page, filters_container, func_create_image_popup):
        self.page = page
        self.page_id = 0## For Pagination
        self.func_create_image_popup = func_create_image_popup
        self.selected_sort = SORT_DEFAULT

        self.images_per_page = 128

        self.images = []

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
        self.button_previous_page = ft.IconButton(
            icon=ft.icons.ARROW_BACK_IOS_ROUNDED,
            tooltip="Previous Page",
            on_click=self.paginate_previous
        )
        self.button_next_page = ft.IconButton(
            icon=ft.icons.ARROW_FORWARD_IOS_ROUNDED,
            tooltip="Next Page",
            on_click=self.paginate_next
        )
        self.page_dropdown = ft.Dropdown(
            label="Page",
            width=64,
            on_change=self.jump_to_page,
            value=1,
            options=[
                ft.dropdown.Option(1)
            ]
        )
        return ft.Row([
            ft.Slider(min=64, max=512, value=256, divisions=7, label="{value}px", on_change=self.zoom_slider_update, expand=True),
            self.button_previous_page,
            self.page_dropdown,
            self.button_next_page,
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
        self.images = []

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
        self.images.append(container)
        # self.grid.controls.insert(0, container)

    def jump_to_page(self, e):
        self.page_id = int(e.data) - 1
        self.update()

    def page_count(self):
        return math.ceil(len(self.images) / self.images_per_page)

    def paginate_next(self, e):
        print("paginate_next")
        self.page_id = (self.page_id + 1) % self.page_count()
        self.update()
        self.grid.scroll_to(offset=0)
    def paginate_previous(self, e):
        print("paginate_previous")
        self.page_id = (self.page_id - 1) % self.page_count()
        self.update() 
        self.grid.scroll_to(offset=-1)


    def update(self):
        print(f"Showing page {self.page_id + 1} of {self.page_count()}")
        start = self.images_per_page * self.page_id
        end = start + self.images_per_page
        self.grid.controls = self.images[start:end]
        self.page_dropdown.options = [ft.dropdown.Option(x) for x in range(1, self.page_count() + 1)]
        self.page_dropdown.value = self.page_id + 1
        self.page_dropdown.update()
        self.grid.update()

    async def zoom_slider_update(self, e):
        self.grid.max_extent = e.control.value
        self.page.update()

    def change_sort(self, e):
        self.selected_sort = e.data
        self.sort()
    
    def sort(self):
        if self.selected_sort == SORT_DATE_DESC:
            self.images.sort(key=lambda x: x.data.timestamp, reverse=True)
        elif self.selected_sort == SORT_DATE_ASC:
            self.images.sort(key=lambda x: x.data.timestamp, reverse=False)
        elif self.selected_sort == SORT_SHUFFLE:
            random.shuffle(self.images)
        else:
            print(f"Invalid sort selection {self.selected_sort}")
        self.update()
        self.page.update()