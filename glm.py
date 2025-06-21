import os
import json
import base64
import random
from zhipuai import ZhipuAI

# --- 全局常量和配置 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_NAME = 'config.json'
TEXT_PROMPTS_FILE_NAME = 'text_prompts.json'
IMAGE_PROMPTS_FILE_NAME = 'image_prompts.json'
DEFAULT_TEXT_PROMPT_TEMPLATE = 'video_prompt_system_template.txt'
DEFAULT_IMAGE_PROMPT_TEMPLATE = 'image_to_prompt_template.txt'

# --- 辅助函数 ---

def _log_info(message):
    """统一的日志输出函数"""
    print(f"[GLM_Nodes] {message}")

def _log_warning(message):
    """统一的警告输出函数"""
    print(f"[GLM_Nodes] 警告：{message}")

def _log_error(message):
    """统一的错误输出函数"""
    print(f"[GLM_Nodes] 错误：{message}")

def get_zhipuai_api_key():
    """
    尝试从环境变量 ZHIPUAI_API_KEY 获取智谱AI API Key。
    如果环境变量不存在，则尝试从同目录下的 config.json 文件中读取。
    返回 API Key 字符串，如果未找到则返回空字符串。
    """
    env_api_key = os.getenv("ZHIPUAI_API_KEY")
    if env_api_key:
        _log_info("使用环境变量 ZHIPUAI_API_KEY。")
        return env_api_key

    config_path = os.path.join(CURRENT_DIR, CONFIG_FILE_NAME)
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get("ZHIPUAI_API_KEY")
            if api_key:
                _log_info(f"从 {config_path} 读取 API Key。")
                return api_key
            else:
                _log_warning(f"在 {config_path} 中未找到有效的 ZHIPUAI_API_KEY 字段。")
                return ""
        else:
            _log_warning(f"未找到 API Key 配置文件 {config_path}。")
            return ""
    except json.JSONDecodeError:
        _log_error(f"配置文件 {config_path} 格式不正确 (非有效 JSON)。")
        return ""
    except Exception as e:
        _log_error(f"读取配置文件时发生未知错误: {e}")
        return ""

def load_text_from_file(file_path):
    """
    从指定文件路径加载文本内容。
    返回文件内容字符串，如果文件不存在或读取失败则返回空字符串。
    """
    if not file_path or not os.path.exists(file_path):
        _log_warning(f"文件 '{file_path}' 不存在或路径为空。")
        return ""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        _log_info(f"成功从文件 '{file_path}' 加载内容。")
        return content
    except Exception as e:
        _log_error(f"从文件 '{file_path}' 加载内容失败: {e}")
        return ""

def load_prompt_dict_from_json(json_file_path, default_built_in_prompts):
    """
    从 JSON 文件加载提示词字典。
    如果文件不存在、格式错误或为空，则返回提供的 default_built_in_prompts。
    """
    if not os.path.exists(json_file_path):
        _log_warning(f"提示词字典文件 '{json_file_path}' 不存在。将使用内置默认提示词。")
        return default_built_in_prompts
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict) or not data:
                _log_warning(f"提示词字典文件 '{json_file_path}' 内容为空或格式不正确 (不是非空字典)。将使用内置默认提示词。")
                return default_built_in_prompts
            _log_info(f"成功从文件 '{json_file_path}' 加载提示词字典。")
            return data
    except json.JSONDecodeError:
        _log_error(f"提示词字典文件 '{json_file_path}' 格式不正确 (非有效 JSON)。将使用内置默认提示词。")
        return default_built_in_prompts
    except Exception as e:
        _log_error(f"读取提示词字典文件 '{json_file_path}' 时发生未知错误: {e}。将使用内置默认提示词。")
        return default_built_in_prompts

# --- GLM文本对话节点 ---

class GLM_Text_Chat:
    """
    一个用于在 ComfyUI 中调用智谱AI GLM-4 模型进行文本聊天的节点。
    支持多个预设系统提示词，并有优先级管理。
    节点中暴露了seed参数，当seed为0时，内部生成随机种子。
    """
    CATEGORY = "GLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response_text",)
    FUNCTION = "glm_chat_function"

    # 内置的默认系统提示词
    _BUILT_IN_TEXT_PROMPTS = {
        "默认视频扩写提示 (内置)": """
你是一个专业的视频脚本和提示词生成助手。你的任务是根据用户提供的核心概念，将其扩写成一个详细、具体、富有画面感的视频生成提示词。请严格遵循以下结构和要求：

1.  **主体描述：** 详细刻画视频中的主要对象或人物的外观、特征、状态。
2.  **场景描述：** 细致描绘主体所处环境，包括时间、地点、背景元素、光线、天气等。
3.  **运动描述：** 明确主体的动作细节（幅度、速率、效果）。
4.  **镜头语言：** 指定景别（如特写、近景、中景、全景）、视角（如平视、仰视、俯视）、镜头类型（如广角、长焦）、运镜方式（如推、拉、摇、移、跟、升、降）。
5.  **氛围词：** 定义画面的情感与气氛。
6.  **风格化：** 设定画面的艺术风格（如写实、卡通、赛博朋克、水墨画、电影感、抽象）。

**输出格式要求：**
-   只输出最终扩写后的视频提示词，不要包含任何解释性文字或额外的对话。
-   将所有要素融合为一段连贯的描述性文字，确保逻辑流畅。
-   最终提示词应该尽可能详细，包含丰富的细节，以便AI模型能准确理解并生成高质量视频。

**举例：**
用户输入：一只小狗在草地上玩耍。
你的输出：一只毛茸茸的金毛幼犬，披着阳光般金色的毛发，眼神好奇而活泼，在阳光明媚的广阔草地上奔跑。它欢快地追逐着一只飞舞的蝴蝶，时而跳跃，时而打滚，草屑和泥土溅起细小的弧线。中景，低角度仰拍，镜头随着小狗的奔跑而平稳地横向移动，展现出草地的广阔和小狗的活力。画面充满温暖、快乐、生机勃勃的氛围，色彩鲜艳，如田园诗般的卡通风格。
"""
    }

    @classmethod
    def get_text_prompts(cls):
        """加载外部或内置的文本提示词字典。"""
        # 尝试从外部JSON加载，如果失败则回退到内置默认
        return load_prompt_dict_from_json(
            os.path.join(CURRENT_DIR, TEXT_PROMPTS_FILE_NAME),
            cls._BUILT_IN_TEXT_PROMPTS
        )

    @classmethod
    def INPUT_TYPES(s):
        available_prompts = s.get_text_prompts()
        prompt_keys = list(available_prompts.keys())
        default_selection = prompt_keys[0] if prompt_keys else "无可用提示词"

        return {
            "required": {
                "text_system_prompt_preset": (prompt_keys, {"default": default_selection}),
                "system_prompt_override": ("STRING", {"multiline": True, "default": "", "placeholder": "系统提示词 (留空则尝试从预设或默认文件加载)"}),
                "api_key": ("STRING", {"default": "", "multiline": False, "placeholder": "可选：智谱AI API Key (留空则尝试从环境变量或config.json读取)"}),
                "model_name": ("STRING", {"default": "glm-4-flash-250414", "placeholder": "请输入模型名称，如 glm-4-flash-250414"}),
                "temperature": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01}),
                "top_p": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 4096}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "设置为0时，每次运行生成随机种子；设置为其他值时，使用固定种子。注意：此种子仅影响ComfyUI节点内部的随机数生成，不直接影响智谱AI模型的输出结果。"}),
                "text_input": ("STRING", {"multiline": True, "default": "请扩写关于一只小狗在草地上玩耍的视频提示词。", "placeholder": "请输入需要扩写的视频提示词内容"}),
            }
        }

    def glm_chat_function(self, text_input, api_key, model_name, temperature, top_p, max_tokens, seed, system_prompt_override, text_system_prompt_preset):
        """
        执行智谱AI GLM-4 文本聊天功能。
        """
        final_api_key = api_key.strip() or get_zhipuai_api_key()
        if not final_api_key:
            return (_log_error("智谱AI API Key 未提供。请在节点输入中填写，或设置环境变量 'ZHIPUAI_API_KEY'，或在 config.json 中配置。"),)
        _log_info("使用API Key进行智谱AI客户端初始化。")

        try:
            client = ZhipuAI(api_key=final_api_key)
        except Exception as e:
            return (_log_error(f"初始化智谱AI客户端失败。请检查API Key是否有效。详细信息: {e}"),)

        # --- 系统提示词确定优先级 ---
        final_system_prompt = ""
        available_prompts = self.get_text_prompts()

        if system_prompt_override and system_prompt_override.strip():
            final_system_prompt = system_prompt_override.strip()
            _log_info("使用节点输入 'system_prompt_override' 作为系统提示词 (最高优先级)。")
        elif text_system_prompt_preset in available_prompts:
            final_system_prompt = available_prompts[text_system_prompt_preset]
            _log_info(f"使用预设系统提示词: '{text_system_prompt_preset}'。")
        else:
            # 尝试从默认文件加载，否则使用内置兜底
            loaded_prompt = load_text_from_file(os.path.join(CURRENT_DIR, DEFAULT_TEXT_PROMPT_TEMPLATE))
            if loaded_prompt:
                final_system_prompt = loaded_prompt
                _log_info(f"从默认文件 '{DEFAULT_TEXT_PROMPT_TEMPLATE}' 加载系统提示词。")
            else:
                final_system_prompt = list(self._BUILT_IN_TEXT_PROMPTS.values())[0]
                _log_warning("无法从文件或指定预设加载，使用内置预设中唯一的系统提示词。")

        if not final_system_prompt:
            return (_log_error("最终系统提示词不能为空。"),)

        # 确保 final_system_prompt 确实是字符串
        if not isinstance(final_system_prompt, str):
            _log_warning(f"final_system_prompt 类型异常: {type(final_system_prompt)}. 尝试转换为字符串。")
            final_system_prompt = str(final_system_prompt)

        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": text_input}
        ]

        # --- 种子逻辑 ---
        effective_seed = seed if seed != 0 else random.randint(0, 0xffffffffffffffff)
        _log_info(f"ComfyUI节点内部种子: {effective_seed} (不影响智谱AI模型生成结果)")
        random.seed(effective_seed) # 仅影响节点内部的随机性，如未来可能扩展的随机选择逻辑

        _log_info(f"开始调用智谱AI GLM-4 模型进行文本聊天...")
        _log_info(f"  模型: {model_name}")
        _log_info(f"  系统提示词 (前100字): '{final_system_prompt[:100]}...'")
        _log_info(f"  用户输入: '{text_input}'")
        _log_info(f"  参数: temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            response_text = response.choices[0].message.content
            _log_info("成功接收到智谱AI GLM-4 响应。")
            _log_info("调用智谱AI GLM-4 结束。\n")
            return (response_text,)
        except Exception as e:
            error_message = f"调用智谱AI GLM-4 API 失败: {e}"
            _log_error(error_message)
            _log_error("调用智谱AI GLM-4 结束 (失败)。\n")
            return (error_message,)

# --- GLM识图生成提示词节点 ---

class GLM_Vision_ImageToPrompt:
    """
    一个用于在 ComfyUI 中调用智谱AI GLM-4V 模型，
    根据图片 URL 或 Base64 编码的图片数据和文本提示生成图片描述提示词的节点。
    支持多个预设识图提示词，并有优先级管理。
    """
    CATEGORY = "GLM"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("GETPrompt",)
    FUNCTION = "generate_prompt"

    # 内置的默认识图提示词
    _BUILT_IN_IMAGE_PROMPTS = {
        "通用高质量英文描述 (内置)": "你是一个专业的图像描述专家，能够将图片内容转化为高质量的英文提示词，用于文本到图像的生成模型。请仔细观察提供的图片，并生成一段详细、具体、富有创造性的英文短语，描述图片中的主体对象、场景、动作、光线、材质、色彩、构图和艺术风格。要求：语言：严格使用英文。细节：尽可能多地描绘图片细节，包括但不限于物体、人物、背景、前景、纹理、表情、动作、服装、道具等。角度：尽可能从多个角度丰富描述，例如特写、广角、俯视、仰视等，但不要直接写“角度”。连接：使用逗号（,）连接不同的短语，形成一个连贯的提示词。人物：描绘人物时，使用第三人称（如 'a woman', 'the man'）。质量词：在生成的提示词末尾，务必添加以下质量增强词：', best quality, high resolution, 4k, high quality, masterpiece, photorealistic'"
    }

    @classmethod
    def get_image_prompts(cls):
        """加载外部或内置的图像提示词字典。"""
        return load_prompt_dict_from_json(
            os.path.join(CURRENT_DIR, IMAGE_PROMPTS_FILE_NAME),
            cls._BUILT_IN_IMAGE_PROMPTS
        )

    @classmethod
    def INPUT_TYPES(cls):
        available_prompts = cls.get_image_prompts()
        prompt_keys = list(available_prompts.keys())
        default_selection = prompt_keys[0] if prompt_keys else "无可用提示词"

        return {
            "required": {
                "image_prompt_preset": (prompt_keys, {"default": default_selection}),
                "image_base64": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "请输入Base64编码的图片数据 (与URL二选一)"
                }),
                "model_name": ("STRING", {
                    "default": "glm-4v-flash",
                    "placeholder": "请输入模型名称，如 glm-4v-flash"
                }),
                "api_key":  ("STRING", {
                    "multiline": False,
                    "default": "",
                    "placeholder": "可选：智谱AI API Key (留空则尝试从环境变量或config.json读取)"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                    "display": "number",
                    "tooltip": "设置为0时，每次运行生成随机种子；设置为其他值时，使用固定种子。注意：此种子仅影响ComfyUI节点内部的随机数生成，不直接影响智谱AI模型的输出结果。"
                }),
                "prompt_override": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "请输入用于描述图片的文本提示词 (留空则尝试从预设或默认文件加载)"
                }),
            },
            "optional": {
                "image_url": ("STRING", {
                    "default": "",
                    "placeholder": "请输入图片URL (与Base64二选一)"
                }),
            }
        }

    def generate_prompt(self, api_key, prompt_override, model_name, seed, image_url="", image_base64="", image_prompt_preset=""):
        """
        执行智谱AI GLM-4V 识图生成提示词功能。
        """
        final_api_key = api_key.strip() or get_zhipuai_api_key()
        if not final_api_key:
            return (_log_error("智谱AI API Key 未提供。请在节点输入中填写，或设置环境变量 'ZHIPUAI_API_KEY'，或在 config.json 中配置。"),)
        _log_info("使用API Key进行智谱AI客户端初始化。")

        try:
            client = ZhipuAI(api_key=final_api_key)
        except Exception as e:
            return (_log_error(f"初始化智谱AI客户端失败。请检查API Key是否有效。详细信息: {e}"),)

        # --- 输入校验：图片URL和Base64图片至少提供一个 ---
        image_url_provided = bool(image_url and image_url.strip())
        image_base64_provided = bool(image_base64 and image_base64.strip())

        if not image_url_provided and not image_base64_provided:
            return (_log_error("必须提供图片URL或Base64编码的图片数据之一。"),)

        if image_url_provided and image_base64_provided:
            _log_warning("同时提供了图片URL和Base64图片，将优先使用Base64图片。")

        # --- 识图提示词确定优先级 ---
        final_prompt_text = ""
        available_prompts = self.get_image_prompts()

        if prompt_override and prompt_override.strip():
            final_prompt_text = prompt_override.strip()
            _log_info("使用节点输入 'prompt_override' 作为识图提示词 (最高优先级)。")
        elif image_prompt_preset in available_prompts:
            final_prompt_text = available_prompts[image_prompt_preset]
            _log_info(f"使用预设识图提示词: '{image_prompt_preset}'。")
        else:
            # 尝试从默认文件加载，否则使用内置兜底
            loaded_prompt = load_text_from_file(os.path.join(CURRENT_DIR, DEFAULT_IMAGE_PROMPT_TEMPLATE))
            if loaded_prompt:
                final_prompt_text = loaded_prompt
                _log_info(f"从默认文件 '{DEFAULT_IMAGE_PROMPT_TEMPLATE}' 加载识图提示词。")
            else:
                final_prompt_text = list(self._BUILT_IN_IMAGE_PROMPTS.values())[0]
                _log_warning("无法从文件或指定预设加载，使用内置预设中唯一的识图提示词。")

        if not final_prompt_text:
             return (_log_error("最终识图提示词不能为空。"),)

        # 确保 final_prompt_text 确实是字符串
        if not isinstance(final_prompt_text, str):
            _log_warning(f"final_prompt_text 类型异常: {type(final_prompt_text)}. 尝试转换为字符串。")
            final_prompt_text = str(final_prompt_text)

        # --- 构建消息内容 ---
        content_parts = [{"type": "text", "text": final_prompt_text}]

        if image_base64_provided:
            if image_base64.startswith("data:image/"):
                content_parts.append({"type": "image_url", "image_url": {"url": image_base64}})
                _log_info("使用完整Base64 URI图片数据。")
            else:
                _log_warning("输入的Base64字符串缺少'data:image/...;base64,'前缀。已尝试添加默认JPEG前缀。")
                content_parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
        elif image_url_provided:
            content_parts.append({"type": "image_url", "image_url": {"url": image_url}})
            _log_info(f"使用图片URL: {image_url}")

        # --- 种子逻辑 (智谱AI GLM-4V API通常不支持直接的seed参数，此参数仅用于ComfyUI节点内部) ---
        effective_seed = seed if seed != 0 else random.randint(0, 0xffffffffffffffff)
        _log_info(f"ComfyUI节点内部种子: {effective_seed} (不影响智谱AI模型生成结果)")
        random.seed(effective_seed) # 仅影响节点内部的随机性

        _log_info(f"开始调用智谱AI GLM-4V 模型进行识图...")
        _log_info(f"  模型: {model_name}")
        _log_info(f"  用户提示词 (前100字): '{final_prompt_text[:100]}...'")
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": content_parts}]
            )
            response_content = str(response.choices[0].message.content)
            _log_info("成功接收到智谱AI GLM-4V 响应。")
            _log_info("调用智谱AI GLM-4V 结束。\n")
            return (response_content,)
        except Exception as e:
            error_message = f"调用智谱AI GLM-4V API 失败: {e}"
            _log_error(error_message)
            _log_error("调用智谱AI GLM-4V 结束 (失败)。\n")
            return (error_message,)

# --- ComfyUI 节点映射 ---
NODE_CLASS_MAPPINGS = {
    "GLM_Text_Chat": GLM_Text_Chat,
    "GLM_Vision_ImageToPrompt": GLM_Vision_ImageToPrompt,
}

# ComfyUI 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "GLM_Text_Chat": "GLM文本对话",
    "GLM_Vision_ImageToPrompt": "GLM识图生成提示词",
}
