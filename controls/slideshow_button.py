from functools import partial
import threading
import flet as ft

from lib.configurator import Configurations
class SlideshowButton:
    def __init__(self, func_next_popup, config: Configurations):
        self.slideshow_timer = None
        self.func_next_popup = func_next_popup
        self.config = config

    def new_button(self):
        self.button = ft.IconButton(
            icon=ft.icons.PLAY_ARROW_ROUNDED,
            selected_icon=ft.icons.STOP_ROUNDED,
            icon_color=ft.colors.BLUE_300,
            selected_icon_color = ft.colors.BLUE,
            style=ft.ButtonStyle(bgcolor='#66ffffff'),
        )
        self.button.on_click = self.toggle_slideshow
        self.button.selected = self.is_running()

        return self.button

    def toggle_slideshow(self, e):
        if not self.is_running():
            self.start_slideshow()
            self.button.selected = True
        else:
            self.stop_slideshow()
            self.button.selected = False
        self.button.update()
        
    def start_slideshow(self):
        next = False
        if self.is_running():
            next = True
        seconds = self.config.get_config("slideshow_delay")/1000
        self.slideshow_timer = threading.Timer(seconds, partial(self.start_slideshow))
        self.slideshow_timer.start()
        if next:
            self.func_next_popup(1, None)

    def stop_slideshow(self):
        if self.is_running():
            self.slideshow_timer.cancel()
            self.slideshow_timer = None

    def is_running(self):
        return self.slideshow_timer != None