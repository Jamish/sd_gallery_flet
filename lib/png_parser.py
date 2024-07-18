
from lib.png_data import PngData
from PIL import Image
import json
import os
import re
import lib.image_helpers as imagez
NODE_NAMES_SAMPLER = ["KSampler"]
NODE_NAMES_MODEL = ["CheckpointLoader"]
NODE_NAMES_CLIP = ["CLIPTextEncode", "CLIP"]
NODE_NAMES_LORA = ["LoraLoader"]
BLOCK_LIST = ["CLIPSetLastLayer"]

class PngParser:
    def __init__(self):
        self.foo = 1

    def __matches(self, node_type, search_strings):
        for search_string in search_strings:
            if search_string.lower() in node_type.lower() and not node_type in BLOCK_LIST:
                return True
        return False

    def parse(self, filename: str) -> PngData:
        print(f"Parsing metadata: {os.path.basename(filename)}")
        im = Image.open(filename)
        im.load()

        workflow = im.info['workflow']
        # print(workflow)

        data = json.loads(workflow)

        sampler_node = None
        clip_nodes = []

        model_node = None
        lora_nodes = []

        for node in data['nodes']:
            type = node['type']
            if self.__matches(type, NODE_NAMES_CLIP):
                #print(f"Found clip node: {type}")
                clip_nodes.append(node)
            if self.__matches(type, NODE_NAMES_SAMPLER):
                sampler_node = node
            if self.__matches(type, NODE_NAMES_LORA):
                lora_nodes.append(node)
            if self.__matches(type, NODE_NAMES_MODEL):
                model_node = node
        
        positive_link_id = -1
        negative_link_id = -1
        for input in sampler_node['inputs']:
            if input['name'] == "positive":
                positive_link_id = input['link']
            if input['name'] == "negative":
                negative_link_id = input['link']

        if len(clip_nodes) == 0:
            raise Exception(f"CLIPTextEncode nodes not found")
        if positive_link_id == -1:
            raise Exception(f"KSampler not found")
        
        sampler_positive_link_source_node_id = -1
        sampler_negative_link_source_node_id = -1
        for link in data['links']:
            # [linkId, sourceNodeId, ?, destinationNodeId, inputId]
            if link[0] == positive_link_id:
                sampler_positive_link_source_node_id = link[1]
            if link[0] == negative_link_id:
                sampler_negative_link_source_node_id = link[1]

        if sampler_positive_link_source_node_id == -1:
            raise Exception(f"Could not find sampler's positive text link with id {positive_link_id}")
        if sampler_negative_link_source_node_id == -1:
            raise Exception(f"Could not find sampler's negative text link with id {negative_link_id}")

        positive_prompt = ""
        negative_prompt = ""
        if len(clip_nodes) > 1:
            for clip_node in clip_nodes:
                if clip_node['id'] == sampler_positive_link_source_node_id:
                    if clip_node['properties']['Node name for S&R'] == "workflow/CLIP":
                        positive_prompt = clip_node['widgets_values'][1] # le hack for  ComfyUI-2024-05_00747_.png
                    else:
                        positive_prompt = clip_node['widgets_values'][0]
                if clip_node['id'] == sampler_negative_link_source_node_id:
                    if clip_node['properties']['Node name for S&R'] == "workflow/CLIP":
                        negative_prompt = clip_node['widgets_values'][2] # le hack for  ComfyUI-2024-05_00747_.png
                    else:
                        negative_prompt = clip_node['widgets_values'][0]
        elif len(clip_nodes) == 1:
            positive_prompt = clip_nodes[0]['widgets_values'][1]
            negative_prompt = clip_nodes[0]['widgets_values'][2]
        else:
            raise Exception(f"Found more than 2 CLIP nodes for file {filename}.")

        # pyperclip.copy(prompt)

        # Split by newline and commas 
        tags = re.split(r"[,\n]+", positive_prompt.strip())
        tags = [tag.strip() for tag in tags if tag.strip()] # Strip whitespace from tags and Filter out empty tags
        #print(f"Positive tags: {tags}")
        
        condensed_positive_prompt = positive_prompt.replace("\n", " ")
        condensed_negative_prompt = negative_prompt.replace("\n", " ")
        
        display_text = ""
        model_name = ""
        if model_node is not None:
            if model_node['type'] == "CheckpointLoaderSimple":
                model_name = model_node['widgets_values'][0]
            else:
                model_name = model_node['widgets_values'][0]['content']
            model_name = model_name.replace(".safetensors", "")
            display_text = f"MODEL: {model_name}\n\n"


        has_lora = False
        loras = []
        for lora_node in lora_nodes:
            if lora_node['mode'] == 4: # Mode 4 is "bypass"
                continue 
            if lora_node['type'] == "LoraLoader":
                lora_name = model_node['widgets_values'][0]
            else:
                lora_name = lora_node['widgets_values'][0]['content'].replace(".safetensors", "")
            strength = lora_node['widgets_values'][1]
            loras.append(lora_name)
            display_text = f"{display_text}LORA: {lora_name} (weight: {strength:.2f})\n"
            has_lora = True

        if has_lora:
            display_text = f"{display_text}\n"        

        display_text = f"{display_text}POSITIVE:\n{condensed_positive_prompt}\n\n"
        display_text = f"{display_text}NEGATIVE:\n{condensed_negative_prompt}\n"
        
        thumbnail_base64 = imagez.make_thumbnail_base64(im)

        png_data = PngData(
            filename=filename,
            tags=tags,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            checkpoint=model_name,
            loras=loras,
            thumbnail_base64 = thumbnail_base64,
        )

        return png_data


