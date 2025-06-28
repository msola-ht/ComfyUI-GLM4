# ComfyUI-GLM4 极简使用指南

------

**ComfyUI-GLM4** 是一个 ComfyUI 自定义节点，让您可以在 ComfyUI 中直接使用智谱AI的 **GLM-4 大语言模型**，为您的图像生成或自动化流程提供智能文本支持。

从 https://github.com/heshengtao/comfyui_LLM_party 获取的FLUX提示词模版

参考 https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet 新增了翻译节点，目前只有中英文

## 视频反推及扩写

![ComfyUI-GLM4](/image/PixPin_2025-06-21_23-10-51.png)

## Flux 提示词

### 反推

![](/image/PixPin_2025-06-21_23-09-55.png)

### 扩写

![](/image/PixPin_2025-06-21_23-09-47.png)

## 核心功能

*   **ComfyUI 内置 GLM-4：** 直接在 ComfyUI 工作流中调用 GLM-4 模型。
*   **智能文本生成：** 视频提示词扩写，反推提示词
*   **简单易用：** 只需填入智谱AI API Key 即可开始。

## 快速上手（三步走）

### 步骤一：安装节点与依赖

1.  **打开 ComfyUI 安装目录**：进入 `ComfyUI/custom_nodes` 文件夹。
2.  **克隆仓库**：在此文件夹内打开命令行（或Git Bash），运行以下命令：
    ```bash
    git clone https://github.com/msola-ht/ComfyUI-GLM4.git
    ```
3.  **安装依赖**：进入新克隆的 `ComfyUI-GLM4` 文件夹，运行以下命令安装必要的Python库：
    ```bash
    cd ComfyUI-GLM4
    pip install -r requirements.txt
    ```
    *(如果 `requirements.txt` 不存在，请尝试运行 `pip install zhipuai`)*
4.  **重启 ComfyUI**：安装完成后，**务必重启 ComfyUI 应用程序**。

### 步骤二：获取智谱AI API Key

1.  **访问智谱AI开放平台**：[bigmodel.cn](https://www.bigmodel.cn/invite?icode=2X%2FldpUyTOnXZGJ6GSyycbC%2Fk7jQAKmT1mpEiZXXnFw%3D)。
2.  **注册/登录**：完成注册并登录您的账号。
3.  **生成 API Key**：在用户中心或 API Key 管理页面生成您的 API Key。**请妥善保管此Key。**

### 步骤三：在 ComfyUI 中使用

1.  **拖出节点**：
    *   启动 ComfyUI。
    *   在工作流画布中**右键点击**，选择 `Add Node` -> `ComfyUI-GLM4` (或类似名称)。
2.  **配置 API Key**：
    *   在 ComfyUI-GLM4 节点上，找到 `api_key` 输入框。
    *   将您在智谱AI平台获取到的 API Key 粘贴到此框中（替换 `YOUR_ZHIPU_AI_API_KEY_HERE`）。<img src="/image/PixPin_2025-06-21_23-19-24.png" alt="ComfyUI-GLM4" width="200px" />
    *   环境变量设置 ZHIPUAI_API_KEY："YOUR_ZHIPUAI_API_KEY_HERE"
    *   Config 设置 KEY
3.  **连接并运行**：
    *   将您的文本输入（Prompt）连接到 `text_input` 端。
    *   将节点的 `text_output` 端连接到需要接收文本的节点（例如：`CLIP Text Encode` 用于图像生成，或 `Text` 节点用于显示结果）。
    *   点击 ComfyUI 的 `Queue Prompt` 按钮，即可看到 GLM-4 生成的文本。

### **重要提示：免费模型选择**

在 `ComfyUI-GLM4` 节点的 `model_name` 参数中，您可以选择不同的 GLM 模型。为了**免费使用**，请优先选择以下模型：

*   **`GLM-4-Flash`** (或其最新版本如 `GLM-4-Flash-250414`)
*   **`GLM-4V-Flash`** (如果您需要多模态能力，例如图像理解)

这些是智谱AI提供的免费或有大量免费额度的模型，可以满足大部分日常使用需求。

---

<img src="/image/微信图片_20250620124237.png" alt="ComfyUI-GLM4" width="200px" />
