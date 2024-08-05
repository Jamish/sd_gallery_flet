
import sys
import traceback
from lib.png_data import PngData
from PIL import Image
import json
import os
import re
import lib.image_helpers as imagez
import lib.list_helpers as listz
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
    
    def __normalize_tag(self, tag):
        tag = tag.strip()

        # Replace escaped parentheses with temporary characters
        tag = tag.replace("\\(", "<").replace("\\)", ">")

        # Remove modifiers (parentheses, brackets) and leading/trailing whitespace
        tag = tag.replace("(", "")
        tag = tag.replace(")", "")
        tag = tag.replace("[", "")
        tag = tag.replace("]", "")

        # Convert underscores to spaces
        tag = tag.replace("_", " ")

        # Split by colon (:) and take the first part
        tag = tag.split(":")[0]

        # Restore parentheses if they were escaped
        tag = tag.replace("<", "(").replace(">", ")")

        tag = tag.strip() 

        return tag.lower()
    
    
    def __parse_automatic1111(self, im: Image, image_path):
        text = im.info['parameters']

        def halve(text, separator):
            tokens = text.split(separator, 1)
            return tokens[0], tokens[1]
        
        positive_prompt = ""
        negative_prompt = ""

        if "\nNegative prompt:" in text:
            positive_prompt, remains = halve(text, "\nNegative prompt:")
            negative_prompt, remains = halve(remains, "\nSteps:")
        else:
            positive_prompt, remains = halve(text, "\nSteps:")

        lora_pattern = r"<lora:([^:]+):\d+(?:\.\d+)?>"
        loras = re.findall(lora_pattern, positive_prompt)

        # Extract the model using regex
        model_match = re.search(r"Model: ([^,]+)", text)
        model_name = model_match.group(1).strip() if model_match else ""

        return {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "model_name": model_name,
            "loras": loras
        }


    
    def __parse_comfyui(self, im: Image, image_path):
        workflow = im.info['workflow']

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
            raise Exception(f"Found more than 2 CLIP nodes for file {image_path}.")
        
        model_name = ""
        if model_node is not None:
            if model_node['type'] == "CheckpointLoaderSimple":
                model_name = model_node['widgets_values'][0]
            else:
                model_name = model_node['widgets_values'][0]['content']
            model_name = model_name.replace(".safetensors", "")


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


        result =  {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "model_name": model_name,
            "loras": loras
        }
        return result


    def parse(self, image_path: str) -> PngData:
        timestamp = os.path.getctime(image_path)
        im = Image.open(image_path)
        im.load()

        raw_data = im.info
        thumbnail_base64 = imagez.make_thumbnail_base64(im)

        def default(error=""):
            return PngData(
                image_path=image_path,
                thumbnail_base64 = thumbnail_base64,
                timestamp=timestamp,
                raw_data=raw_data,
                loras=[],
                tags=[],
                error=error
            )
        result = None
        try:
            if "workflow" in im.info:
                result = self.__parse_comfyui(im, image_path)
            if "parameters" in im.info:
                result = self.__parse_automatic1111(im, image_path)

            if result == None:
                return default()
                

            positive_prompt = result["positive_prompt"]
            negative_prompt = result["negative_prompt"]
            model_name = result["model_name"]
            loras = result["loras"]

            # Split by newline and commas 
            tags = re.split(r"[,\n]+", positive_prompt.strip())

            def remove_lora_tags(tag):
                return re.split(r"<lora:[^>]+>", tag)
            tags = listz.flatmap(remove_lora_tags, tags)

            tags = [self.__normalize_tag(tag) for tag in tags if tag.strip()] # Strip whitespace from tags and Filter out empty tags
            tags = list(set(tags)) # unique
            

            model_name_trimmed = model_name.split("\\")[-1]
            tags.append(f"model:{model_name_trimmed}")
            for lora in loras:
                lora_name_trimmed = lora.split("\\")[-1]
                tags.append(f"lora:{lora_name_trimmed}")

            png_data = PngData(
                image_path=image_path,
                tags=tags,
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                checkpoint=model_name,
                loras=loras,
                thumbnail_base64 = thumbnail_base64,
                timestamp=timestamp,
                raw_data=raw_data
            )

            return png_data
        except Exception as e:
            exc_info = sys.exc_info()
            message = ''.join(traceback.format_exception(*exc_info))
            return default(message)


