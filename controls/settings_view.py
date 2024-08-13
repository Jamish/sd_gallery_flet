from functools import partial
import threading
import flet as ft

from lib.configurator import Configurations
class SettingsView:
    def __init__(self, config: Configurations):
        self.config = config


        def get_slider_label(value):
            return f"Slideshow Delay: {value} ms"
        async def slider_changed(e):
            slideshow_delay_label.value = get_slider_label(e.control.value)
            config.set_slideshow_delay(e.control.value)
            await slideshow_delay_label.update_async()
        slideshow_delay_value = config.get_slideshow_delay()
        slideshow_delay_label = ft.Text(get_slider_label(slideshow_delay_value))
        maxDelay = 10000
        minDelay = 1000
        divisions = int((maxDelay - minDelay) / 250)
        self.slideshowDelaySlider = ft.Slider(value=slideshow_delay_value, min=minDelay, max=maxDelay, divisions=divisions, label="{value}ms", on_change=slider_changed)
        self.control = ft.Column([
            slideshow_delay_label,
            self.slideshowDelaySlider
        ], expand=True)
