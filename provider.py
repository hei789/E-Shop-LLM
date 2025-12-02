from flask import Flask, request, jsonify, Response, stream_with_context
from openai import OpenAI
import psutil
import os
import signal


# ----------------- 模型配置 -----------------
client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key="sk-9aeb4541a01144b1a63fe6f41f439b9c",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL = "qwen-flash"               # 想换模型直接改
# ---------------------------------------

PORT=5006

import socket

app = Flask(__name__)

# 进行聊天
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "") or "你是谁？"
    prompt = f"{prompt}"
    if not prompt:
        return jsonify(error="missing prompt"), 400
    print(prompt) # 目前是用户输入啥Prompt就是啥
    def generate():
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            stream_options={"include_usage": True}
        )
        for chunk in completion:
            # 每块都立即 flush 出去
            print(chunk.model_dump_json())
            print("下一个")
            yield f"data:{chunk.model_dump_json()}\n"

    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream")

@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok")

# # 在这里直接返回一组数据
# @app.route("/postGet", methods=["POST"])
# def postGet():


if __name__ == "__main__":
    # debug=True 便于看日志，生产环境可关掉
    app.run(host="0.0.0.0", port=PORT, debug=True)
