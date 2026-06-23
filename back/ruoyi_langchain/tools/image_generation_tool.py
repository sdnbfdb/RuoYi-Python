from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class ImageGenerationInput(BaseModel):
    prompt: str = Field(description="图像生成描述")

def generate_image(prompt: str) -> str:
    return f"图像生成: {prompt}"

image_generation_tool = StructuredTool.from_function(
    func=generate_image,
    name="generate_image",
    description="生成图像，根据描述创建视觉内容",
    args_schema=ImageGenerationInput
)
