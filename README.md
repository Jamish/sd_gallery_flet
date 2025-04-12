### Intro

A Stable Diffusion image browser written in Python with Flet for the UI. I wrote this for personal use.

This tool lets you load up a folder and see all models, LORAs, and tags (with a frequency counter)! 

https://github.com/user-attachments/assets/78f90fc8-0c8b-48ac-8485-f2d8bf9e4557

It supports
* Loads an entire directory as a collection; supports multiple collections
* Gallery view, with zoom, sorting, and shuffling
* Image viewer that shows the resources and prompts used, along with Copy Prompt buttons
* Parses the models, LORAs, and tags used, and has tabs to show the frequency of models, LORAs, and tags, as well as filtering the gallery based on model/LORA/tag
* Optimized for remote servers: It uses a local cache with image thumbnails and metadata, so images are only parsed once, and the gallery view loads fast. The full-sized file is asynchronously loaded when you click into the image from the gallery view.
* A favorites feature
* A slideshow feature

Caveats:
* Currently, it only supports parsing A111 and ComfyUI metadata. The different parsers can be found in https://github.com/Jamish/sd_gallery_flet/blob/main/lib/png_parser.py
  * The ComfyUI parsing is **VERY** specifically tailored to the workflows that I personally use, so you may have to get your hands dirty and customize your own parser for your images' metadata.
* I don't have good documentation. This was a private repo until today.
* Performance is sus when filtering your list of tags, especially if you have tons of different tags
* Speaking of parsing tags -- it's a fairly naive approach that splits on commas and line breaks. There is no referencing of existing tag datsets, and natural language prompts will probably appear as long, unique tags.

### Installation
`pip install -r requirements.txt`

### Running
python main.py

### Re-generating main.spec
`pip install pyinstaller`
`pyinstaller --onefile main.py`

### Compiling for Windows
Note: This was a failed attempt at creating a .exe for Windows. It doesn't work.
`rm -rf build/ && rm -rf dist/ && pyinstaller main.spec`
