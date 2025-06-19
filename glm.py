# glm.py

import os
import json
import base64 # 尽管不再有 ImageToBase64 节点，但 base64 库本身可能仍被其他地方（例如未来的多模态输入）用到，暂时保留导入。
from zhipuai import ZhipuAI
import random
# from PIL import Image # 不再需要PIL，因为没有图像处理了
# import io # 不再需要io，因为没有图像处理了
# import torch # 不再需要torch，因为没有图像处理了

# 确保 zhipuai 库已安装：pip install zhipuai

# 辅助函数：尝试从环境变量或配置文件获取智谱AI API Key
def get_ZhipuAI_api_key():
    """
    尝试从环境变量 ZHIPU_API_KEY 获取智谱AI API Key。
    如果环境变量不存在，则尝试从同目录下的 config.json 文件中读取。
    返回 API Key 字符串，如果未找到则返回空字符串。
    """
    # 1. 优先从环境变量获取
    env_api_key = os.getenv("ZHIPU_API_KEY")
    if env_api_key:
        print("[GLM_Nodes] 使用环境变量 ZHIPU_API_KEY。")
        return env_api_key

    # 2. 如果环境变量不存在，尝试从 config.json 文件读取
    try:
        # 获取当前脚本文件的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config.json')

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f: # 明确指定编码
                config = json.load(f)
            api_key = config.get("ZHIPU_API_KEY") # 使用 .get() 避免 KeyError
            if api_key:
                print(f"[GLM_Nodes] 从 {config_path} 读取 API Key。")
                return api_key
            else:
                print(f"[GLM_Nodes] 警告：在 {config_path} 中未找到有效的 ZHIPU_API_KEY 字段。")
                return ""
        else:
            print(f"[GLM_Nodes] 警告：未找到 API Key 配置文件 {config_path}。")
            return ""
    except json.JSONDecodeError:
        print(f"[GLM_Nodes] 错误：配置文件 {config_path} 格式不正确 (非有效 JSON)。")
        return ""
    except Exception as e:
        print(f"[GLM_Nodes] 读取配置文件时发生未知错误: {e}")
        return ""


class GLM_Text_Chat:
    """
    一个用于在 ComfyUI 中调用智谱AI GLM-4 模型进行文本聊天的节点。
    增加了固定提示词用于视频提示词的扩写指导。
    节点中暴露了seed参数，当seed为0时，内部生成随机种子。
    """
    CATEGORY = "GLM"  # 插件在 ComfyUI 菜单中的分类
    RETURN_TYPES = ("STRING",)  # 节点输出的类型
    RETURN_NAMES = ("response_text",)  # 节点输出的名称
    FUNCTION = "glm_chat_function"  # 实际执行函数名

    # 将固定系统提示词定义为类属性，方便在其他地方引用
    FIXED_SYSTEM_PROMPT = """
请根据以下提示内容，将文生视频的提示词扩写成一段完整的话。最终的视频提示词应包含六个核心要素：主体(主体描述)、场景(场景描述)、运动(运动描述)、镜头语言、氛围词和风格化。

主体描述是对主体外观特征细节的描述，可通过形容词或短句列举，例如“一位身着少数民族服饰的黑发苗族少女”或“一位来自异世界的飞天仙子，身着破旧却华丽的服饰，背后展开一对由废墟碎片构成的奇异翅膀”。场景描述是对主体所处环境特征细节的描述，可通过形容词或短句列举。运动描述是对运动特征细节的描述，包含运动的幅度、速率和运动作用的效果，例如“猛烈地摇摆”、“缓慢地移动”或“打碎了玻璃”。镜头语言包含景别、视角、镜头、运镜等，常见镜头语言详见下方提示词词典。氛围词是对预期画面氛围的描述，例如“梦幻”、“孤独”或“宏伟”，常见氛围词详见下方提示词词典。风格化是对画面风格语言的描述，例如“赛博朋克”、“勾线插画”或“废土风格”，常见风格化详见下方提示词词典。

#只显示最终扩写后的视频提示词，并且用一段话呈现
"""

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
        定义节点输入参数。
        """
        return {
            "required": {
                "system_prompt_override": ("STRING", {"multiline": True, "default": GLM_Text_Chat.FIXED_SYSTEM_PROMPT, "placeholder": "系统提示词 (留空则使用默认固定提示词)"}),
                "api_key": ("STRING", {"default": get_ZhipuAI_api_key(), "multiline": False, "placeholder": "可选：智谱AI API Key (推荐设为环境变量 ZHIPU_API_KEY 或 config.json)"}),
                "model_name": ("STRING", {"default": "glm-4-flash-250414", "placeholder": "请输入模型名称，如 glm-4-flash-250414"}),
                "temperature": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01}),
                "top_p": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 4096}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "设置为0时，每次运行生成随机种子；设置为其他值时，使用固定种子。注意：此种子仅影响ComfyUI节点内部的随机数生成，不直接影响智谱AI模型的输出结果。"}),
                "text_input": ("STRING", {"multiline": True, "default": "请扩写关于一只小狗在草地上玩耍的视频提示词。", "placeholder": "请输入需要扩写的视频提示词内容"}),
            }
        }

    def glm_chat_function(self, text_input, api_key, model_name, temperature, top_p, max_tokens, seed, system_prompt_override):
        """
        执行智谱AI GLM-4 文本聊天功能。
        """
        # API Key 获取逻辑优化，优先使用节点输入，其次通过 get_ZhipuAI_api_key 获取
        final_api_key = api_key.strip() if api_key and api_key.strip() else get_ZhipuAI_api_key()

        if not final_api_key:
            return ("Error: 智谱AI API Key 未提供。请在节点输入中填写，或设置环境变量 'ZHIPU_API_KEY'，或在 config.json 中配置。",)

        try:
            current_client = ZhipuAI(api_key=final_api_key)
        except Exception as e:
            return (f"Error: 初始化智谱AI客户端失败。请检查API Key是否有效。详细信息: {e}",)

        # 确定最终使用的系统提示词
        final_system_prompt = system_prompt_override.strip() if system_prompt_override.strip() else GLM_Text_Chat.FIXED_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": text_input}
        ]

        # 处理种子逻辑
        effective_seed = seed
        if seed == 0:
            effective_seed = random.randint(0, 0xffffffffffffffff)
            print(f"[GLM_Nodes] seed为0，节点内部生成随机种子: {effective_seed}")
        else: # 当 seed 不为 0 时，使用固定种子
            print(f"[GLM_Nodes] 使用固定种子: {effective_seed}")

        # 此处设置的种子仅影响ComfyUI节点内部的Python随机数生成，不影响智谱AI模型生成结果。
        random.seed(effective_seed) 

        print(f"\n[GLM_Nodes] 开始调用智谱AI GLM-4 模型进行文本聊天...")
        print(f"[GLM_Nodes]   模型: {model_name}")
        print(f"[GLM_Nodes]   系统提示词 (前100字): '{final_system_prompt[:100]}...'")
        print(f"[GLM_Nodes]   用户输入: '{text_input}'")
        print(f"[GLM_Nodes]   参数: temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")
        print(f"[GLM_Nodes]   ComfyUI节点内部种子: {effective_seed} (不影响智谱AI模型生成结果)")
      
        try:
            api_params = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            }
            response = current_client.chat.completions.create(**api_params)

            response_text = response.choices[0].message.content
            print("[GLM_Nodes] 成功接收到智谱AI GLM-4 响应。")
            print(f"[GLM_Nodes] 调用智谱AI GLM-4 结束。\n")
            return (response_text,)
        except Exception as e:
            error_message = f"调用智谱AI GLM-4 API 失败: {e}"
            print(f"[GLM_Nodes] 错误: {error_message}")
            print(f"[GLM_Nodes] 调用智谱AI GLM-4 结束 (失败)。\n")
            return (error_message,)


class GLM_Vision_ImageToPrompt:
    """
    一个用于在 ComfyUI 中调用智谱AI GLM-4V 模型，
    根据图片 URL 或 Base64 编码的图片数据和文本提示生成图片描述提示词的节点。
    """
    CATEGORY = "GLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("GETPrompt",)
    FUNCTION = "generate_prompt"

    def __init__(self):
        pass
      
    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点输入参数。
        """
        return {
            "required": {
                # 调整顺序：image_base64 作为第一个必需参数
                "image_base64": ("STRING", {
                    "multiline": True, # Base64字符串通常很长
                    "default": "",
                    "placeholder": "请输入Base64编码的图片数据 (与URL二选一)"
                }),
                # 接着是 model_name
                "model_name": ("STRING", {
                    "default": "glm-4v-flash",
                    "placeholder": "请输入模型名称，如 glm-4v-flash"
                }),
                # 然后是 api_key
                "api_key":  ("STRING", {
                    "multiline": False,
                    "default": get_ZhipuAI_api_key(),
                    "placeholder": "可选：智谱AI API Key (推荐设为环境变量 ZHIPU_API_KEY 或 config.json)"
                }),
                # 增加随机种子 (智谱AI GLM-4V API通常不支持直接的seed参数，此参数仅用于ComfyUI节点内部)
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                    "display": "number",
                    "tooltip": "设置为0时，每次运行生成随机种子；设置为其他值时，使用固定种子。注意：此种子仅影响ComfyUI节点内部的随机数生成，不直接影响智谱AI模型的输出结果。"
                }),
                # 最后是 prompt
                "prompt": ("STRING", {
                    "default": "先理解这个图片上面的内容，然后生成描绘主体对象的[[英文]]短语，语言是english。生成规范是，记住你需要描绘我提供给你的图片细节尽可能的多，角度尽可能更加丰富，多写[逗号‘，']相连接的英文短语,切记一定需要在生成的prompt文本当中中添加下面这堆prompt，[[best quality, high resolution, 4k, high quality]]，描绘人称都用第三人称",
                    "multiline": True,
                    "placeholder": "请输入用于描述图片的文本提示词"
                }),
            },
            # optional 保持不变，包含 image_url
            "optional": {
                "image_url": ("STRING", {
                    "default": "",
                    "placeholder": "请输入图片URL (与Base64二选一)"
                }),
            }
        }
  
    def generate_prompt(self, api_key, prompt, model_name, seed, image_url="", image_base64=""): 
        """
        执行智谱AI GLM-4V 识图生成提示词功能。
        """
        # API Key 获取逻辑优化，优先使用节点输入，其次通过 get_ZhipuAI_api_key 获取
        final_api_key = api_key.strip() if api_key and api_key.strip() else get_ZhipuAI_api_key()

        if not final_api_key:
            return ("Error: 智谱AI API Key 未提供。请在节点输入中填写，或设置环境变量 'ZHIPU_API_KEY'，或在 config.json 中配置。",)

        try:
            client = ZhipuAI(api_key=final_api_key)
        except Exception as e:
            return (f"Error: 初始化智谱AI客户端失败。请检查API Key是否有效。详细信息: {e}",)
      
        # 输入校验：图片URL和Base64图片至少提供一个
        image_url_provided = image_url and image_url.strip()
        image_base64_provided = image_base64 and image_base64.strip()

        if not image_url_provided and not image_base64_provided:
            return ("Error: 必须提供图片URL或Base64编码的图片数据之一。",)
      
        if image_url_provided and image_base64_provided:
            print("[GLM_Nodes] 警告：同时提供了图片URL和Base64图片，将优先使用Base64图片。")
      
        if not prompt or not prompt.strip():
            return ("Error: 提示词(prompt)不能为空。",) 
      
        # 构建消息内容
        content_parts = []
        content_parts.append({"type": "text", "text": prompt})

        if image_base64_provided:
            # 智谱AI的API中，Base64图片是通过 "image_url" 字段，其url值是 "data:image/jpeg;base64,..." 格式
            if image_base64.startswith("data:image/"):
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    }
                })
                print(f"[GLM_Nodes] 使用完整Base64 URI图片数据。")
            else:
                # 智谱AI的API要求Base64图片必须是完整的Data URI格式
                # 如果输入没有 'data:image/...;base64,' 前缀，则尝试添加默认的JPEG前缀
                print("[GLM_Nodes] 警告：输入的Base64字符串缺少'data:image/...;base64,'前缀。已尝试添加默认JPEG前缀 'data:image/jpeg;base64,'。如果原始图片不是JPEG格式，可能会导致识别失败。建议上游节点提供完整的Data URI格式。")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                })
        elif image_url_provided:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })
            print(f"[GLM_Nodes] 使用图片URL: {image_url}")

        # 处理种子逻辑 (智谱AI GLM-4V API通常不支持直接的seed参数，此参数仅用于ComfyUI节点内部)
        effective_seed = seed
        if seed == 0:
            effective_seed = random.randint(0, 0xffffffffffffffff)
            print(f"[GLM_Nodes] seed为0，节点内部生成随机种子: {effective_seed}")
        else:
            print(f"[GLM_Nodes] 使用固定种子: {effective_seed}")

        random.seed(effective_seed)
        print(f"[GLM_Nodes] ComfyUI节点内部种子: {effective_seed} (不影响智谱AI模型生成结果)")

        print(f"\n[GLM_Nodes] 开始调用智谱AI GLM-4V 模型进行识图...")
        print(f"[GLM_Nodes]   模型: {model_name}")
        print(f"[GLM_Nodes]   用户提示词 (前100字): '{prompt[:100]}...'")

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": content_parts
                    }
                ]
            )
            response_content = str(response.choices[0].message.content)
            print("[GLM_Nodes] 成功接收到智谱AI GLM-4V 响应。")
            print(f"[GLM_Nodes] 调用智谱AI GLM-4V 结束。\n")
            return (response_content,)
        except Exception as e:
            error_message = f"调用智谱AI GLM-4V API 失败: {e}"
            print(f"[GLM_Nodes] 错误: {error_message}")
            print(f"[GLM_Nodes] 调用智谱AI GLM-4V 结束 (失败)。\n")
            return (error_message,)


# ComfyUI 节点映射
NODE_CLASS_MAPPINGS = {
    "GLM_Text_Chat": GLM_Text_Chat,
    "GLM_Vision_ImageToPrompt": GLM_Vision_ImageToPrompt,
    # "ImageToBase64": ImageToBase64, # 移除 ImageToBase64 节点
}

# ComfyUI 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "GLM_Text_Chat": "GLM文本对话",
    "GLM_Vision_ImageToPrompt": "GLM识图生成提示词",
    # "ImageToBase64": "图像转Base64 (自动格式)", # 移除 ImageToBase64 节点显示名称
}

