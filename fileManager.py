import os
import pathlib
from flask import Flask, request, jsonify, send_file, abort, Response

app = Flask(__name__)

UPLOAD_FOLDER = pathlib.Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

CHUNK_SIZE = 1024 * 1024   # 1 MB

# -------------------- 1. 带断点续传的下载 --------------------
@app.route("/download/<path:filename>")
def download(filename):
    file_path = UPLOAD_FOLDER / filename
    if not file_path.is_file():
        abort(404)

    file_size = file_path.stat().st_size
    start, end = 0, file_size - 1

    range_header = request.headers.get("Range")
    if range_header:
        # Range: bytes=start-end
        try:
            h = range_header.replace("bytes=", "").split("-")
            start = int(h[0]) if h[0] else 0
            end   = int(h[1]) if h[1] else file_size - 1
        except ValueError:
            abort(416)  # Range Not Satisfiable
        if start > end or start < 0 or end >= file_size:
            abort(416)

    def generate():
        with open(file_path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                read_size = min(CHUNK_SIZE, left)
                data = f.read(read_size)
                if not data:
                    break
                yield data
                left -= read_size

    rv = Response(generate(), 206 if range_header else 200,
                  mimetype="application/octet-stream")
    rv.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    rv.headers["Accept-Ranges"] = "bytes"
    rv.headers["Content-Length"] = str(end - start + 1)
    if range_header:
        rv.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return rv

# -------------------- 2. 上传 --------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify(error="Empty filename"), 400

    save_path = UPLOAD_FOLDER / file.filename
    file.save(save_path)
    return jsonify(message="uploaded", filename=file.filename)


if __name__ == "__main__":
    # 0.0.0.0 保证局域网可访问
    app.run(host="0.0.0.0", port=5003, threaded=True)