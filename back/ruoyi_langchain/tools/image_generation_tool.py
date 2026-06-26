from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
import sys
import os

# 确保可以导入后端模块
_back_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _back_dir not in sys.path:
    sys.path.insert(0, _back_dir)


class ImageGenerationInput(BaseModel):
    prompt: str = Field(description="图像生成描述（中文或英文均可）")
    size: str = Field(default="1024*1024", description="图片尺寸，如 1024*1024、720*1280 等")


def generate_image_tool(prompt: str, size: str = "1024*1024") -> str:
    """调用通义千问 wanx-v1 真实生成图片，轮询等待完成后返回本地访问路径"""
    try:
        from old.tool.tool import generate_image, get_task_status
        import time

        result = generate_image(prompt, size=size)

        if not result.get('success'):
            return f"图片生成失败: {result.get('message', '未知错误')}"

        data = result.get('data', {})

        # 异步任务，轮询等待完成
        if data.get('async'):
            task_id = data.get('task_id')
            for _ in range(30):
                time.sleep(2)
                status = get_task_status(task_id, task_type='image')
                if status.get('success'):
                    output = status.get('data', {})
                    if output.get('task_status') == 'SUCCEEDED':
                        data = output
                        break
                    elif output.get('task_status') == 'FAILED':
                        return f"图片生成任务失败: {output.get('message', '')}"
            else:
                return f"图片生成超时（任务ID: {task_id}），请稍后重试"

        # 提取图片信息
        images = data.get('images', [])
        if not images:
            return "图片生成完成，但未返回图片数据"

        lines = [f"图片生成成功！共 {len(images)} 张：\n"]
        for i, img in enumerate(images, 1):
            local_url = img.get('local_url', '')
            if local_url:
                lines.append(f"图片{i}: ![生成图片]({local_url})")
            else:
                lines.append(f"图片{i}: {img.get('url', '无URL')}")
        return "\n".join(lines)

    except Exception as e:
        return f"图片生成失败: {str(e)}"


image_generation_tool = StructuredTool.from_function(
    func=generate_image_tool,
    name="generate_image",
    description="使用通义千问AI生成图片，输入描述词即可生成对应图片并返回本地访问地址",
    args_schema=ImageGenerationInput
)
