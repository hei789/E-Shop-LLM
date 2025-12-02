## Conda环境
conda activate LLMPROVIDER
## 释放端口
lsof -i tcp:8080 // 查找PID
kill -9 <PID> // 释放 