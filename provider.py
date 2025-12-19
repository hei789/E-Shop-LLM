from flask import Flask, request, jsonify, Response, stream_with_context
from openai import OpenAI
import psutil
import os
import signal
import json


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

# 抽取实体的工具函数
def extract_topic_entities(answer_text: str) -> list[str]:
    """
    extract_topic_entities 的 Docstring
    先用最暴利的,让LLM自己抽取实体
    :param answer_text: 说明
    :type answer_text: str
    :return: 说明
    :rtype: list[str]
    """
    prompt = (
        "下面是一段回答，请从中抽取出所有关键的话题实体（人名、作品、组织、地点等），请注意，一定要是话题实体，实体数量不要多于五个"
        "输出严格 JSON 列表，不要解释：\n\n"
        f"{answer_text}"
    )
    rsp = client.chat.completions.create(
        model = MODEL,
        messages = [{"role":"user", "content": prompt}],
        temperature = 0
    )
    try:
        print(f"{rsp.choices[0].message.content.strip()}")
        return json.loads(rsp.choices[0].message.content.strip())
    except Exception:
        return []


# 进行聊天，SSE方式返回结果
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "") or "你是谁？" # 从客户端发来的请求中获取 用户问题
    prompt = f"{prompt}"
    if not prompt:
        return jsonify(error="missing prompt"), 400
    print(prompt) # 目前是用户输入啥Prompt就是啥
    def generate():
        # 第一阶段，LLM回答问题
        answer_chunks = []
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
            answer_chunks.append(chunk.model_dump_json())
            yield f"data:{chunk.model_dump_json()}\n"
        
        # 第二阶段
        full_answer = ""
        for ck in answer_chunks:
            c = json.loads(ck)
            if len(c["choices"]) >= 1:
                delta = c["choices"][0]["delta"].get("content") or ""
                full_answer += delta
        entities = extract_topic_entities(full_answer)
        fake_chunk = {
            "choices": [{
                "delta": {"content": f"\n**话题实体**：{json.dumps(entities, ensure_ascii=False)}"}
            }],
            "role": "topic-entities" 
        }
        yield f"event: entities\ndata:{json.dumps(fake_chunk, ensure_ascii=False)}\n\n"

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
