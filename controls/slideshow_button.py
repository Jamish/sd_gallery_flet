from functools import partial
import threading
import flet as ft
class SlideshowButton:
    def __init__(self, func_next_popup):
        self.slideshow_timer = None
        self.func_next_popup = func_next_popup

    def new_button(self):
        self.button = ft.IconButton()
        self.button.on_click = self.toggle_slideshow
        if self.is_running():
            self.button.icon = ft.icons.STOP_ROUNDED
        else:
            self.button.icon = ft.icons.PLAY_ARROW_ROUNDED

        return self.button

    def toggle_slideshow(self, e):
        if not self.is_running():
            self.start_slideshow()
            self.button.icon = ft.icons.STOP_ROUNDED
        else:
            self.stop_slideshow()
            self.button.icon = ft.icons.PLAY_ARROW_ROUNDED
        self.button.update()
        
    def start_slideshow(self):
        next = False
        if self.is_running():
            next = True
        self.slideshow_timer = threading.Timer(3, partial(self.start_slideshow))
        self.slideshow_timer.start()
        if next:
            self.func_next_popup(1, None)

    def stop_slideshow(self):
        if self.is_running():
            self.slideshow_timer.cancel()
            self.slideshow_timer = None

    def is_running(self):
        return self.slideshow_timer != None