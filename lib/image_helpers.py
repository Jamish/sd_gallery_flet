
import base64
from io import BytesIO
from PIL import Image

def make_thumbnail_base64(image: Image) -> str:
    membuf = BytesIO()
    image = image.convert('RGB')
    image.thumbnail((256, 256))  
    image.save(membuf, format="JPEG", quality=85)
    return base64.b64encode(membuf.getvalue()).decode('utf-8')