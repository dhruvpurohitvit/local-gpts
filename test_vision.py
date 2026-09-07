import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import base64
import mimetypes

def encode_image(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_image}"

# Create dummy image
from PIL import Image
img = Image.new('RGB', (100, 100), color = 'red')
img.save('test.png')

llm = ChatOllama(model="qwen2.5vl:7b", num_ctx=8192)
image_data = encode_image("test.png")

print("Testing direct URL...")
try:
    message = HumanMessage(content=[{"type": "text", "text": "What color is this?"}, {"type": "image_url", "image_url": image_data}])
    res = llm.invoke([message])
    print(res.content)
except Exception as e:
    print(f"Error direct URL: {e}")

print("Testing dict URL...")
try:
    message = HumanMessage(content=[{"type": "text", "text": "What color is this?"}, {"type": "image_url", "image_url": {"url": image_data}}])
    res = llm.invoke([message])
    print(res.content)
except Exception as e:
    print(f"Error dict URL: {e}")
