from functools import partial
import threading
import flet as ft

from lib.configurator import Configurations
class SettingsView:
    def __init__(self, config: Configurations, func_set_images_per_page):
        self.config = config
        self.func_set_images_per_page = func_set_images_per_page

        slider_slideshow = self.__create_slider(
            value = self.config.get_config("slideshow_delay"),
            minValue = 1000,
            maxValue = 10000,
            valueIncrement = 250,
            label = "Slideshow Delay",
            units = "ms",
            func_update = lambda x: self.config.set_config("slideshow_delay", x)
        )

        def update_images_per_page(value):
            self.config.set_config("images_per_page", value)
            self.func_set_images_per_page(value)
            

        slider_images_per_page = self.__create_slider(
            value = self.config.get_config("images_per_page"),
            minValue = 8,
            maxValue = 1024,
            valueIncrement = 8,
            label = "Images Per Page",
            units = "",
            func_update = lambda x: update_images_per_page(x)
        )

        self.control = ft.Column([
            slider_slideshow[0],
            slider_slideshow[1],
            slider_images_per_page[0],
            slider_images_per_page[1],
        ], expand=True)

    def __create_slider(self, value, minValue, maxValue, valueIncrement, label, units, func_update):
        def __get_label(v):
            return f"{label}: {round(v)}{units}"
        async def __update(e):
            label_text_field.value = __get_label(e.control.value)
            func_update(e.control.value)
            await label_text_field.update_async()
        label_text_field = ft.Text(__get_label(value))
        divisions = int((maxValue - minValue) / valueIncrement)

        slider = ft.Slider(
            value=value, min=minValue, max=maxValue, divisions=divisions, 
            label="{value}" + str(units), 
            on_change_end=__update)
        return (label_text_field, slider)