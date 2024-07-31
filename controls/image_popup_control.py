from lib.png_data import PngData
import flet as ft
import pyperclip
from functools import partial

class ImagePopupControl:
    def __init__(self, toggle_favorite, close_image_popup):
        self.control = None
        self.toggle_favorite = toggle_favorite
        self.close_image_popup = close_image_popup
        return
    
    def build_image_details(self):
        self.lora_fields = []
        i = 0
        for lora in self.image_data.loras:
            i += 1
            self.lora_fields.append(ft.TextField(label=f"LoRA #{i}", read_only=True, value=lora)),
        
        return ft.Column(
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.END,
            scroll=ft.ScrollMode.ALWAYS,
            controls=[
                ft.Container(height=10), # To give visual space from the top, for the floating X button
                ft.TextField(label="Model Checkpoint", read_only=True, value=self.image_data.checkpoint),
                *self.lora_fields,
                ft.Container(height=5), # To separate LoRAs and prompts
                ft.TextField(label="Positive Prompt", read_only=True, multiline=True, value=self.image_data.positive_prompt),
                ft.ElevatedButton(text="Copy Positive Prompt", on_click=lambda _: pyperclip.copy(self.image_data.positive_prompt)),
                ft.TextField(label="Negative Prompt", read_only=True, multiline=True,value=self.image_data.negative_prompt),
                ft.ElevatedButton(text="Copy Negative Prompt", on_click=lambda _: pyperclip.copy(self.image_data.positive_prompt)),
            ]
        )
    def build_favorite_button(self):
        favorite_icon = ft.icons.FAVORITE_BORDER
        if self.image_data.favorite:
            favorite_icon = ft.icons.FAVORITE

        return ft.IconButton(
            icon=favorite_icon,
            on_click=partial(self.toggle_favorite, self.image_data),
        )

    
    def load_data(self, image_data: PngData):
        self.image_data = image_data

        self.image_details = self.build_image_details()
        self.favorite_button = self.build_favorite_button()

        self.image = ft.Image(
            expand=True,
            src=image_data.image_path,
            fit=ft.ImageFit.CONTAIN,
        )

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_EVENLY, 
            controls=[
                self.image,
                ft.VerticalDivider(width=1),
                ft.Container(
                    padding = 10,
                    width=384,
                    content = self.image_details
                )
            ]
        )
        
        if self.control == None:
            self.control = ft.Container(
                ft.Stack([
                    self.content,
                    ft.Row([
                        self.favorite_button,
                        ft.FloatingActionButton(
                            mini=True,
                            icon=ft.icons.CLEAR_ROUNDED,
                            on_click=self.close_image_popup,
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ], expand=True),
                bgcolor=ft.colors.BACKGROUND,
                data=image_data
            )