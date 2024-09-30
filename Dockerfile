# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到位于 /app 的容器中
COPY . /app

# 安装 requirements.txt 中指定的任何所需包
RUN pip install --no-cache-dir -r requirements.txt

# 使端口可用于网络
EXPOSE 7000
EXPOSE 7001


# 定义环境变量
ENV NAME World

# 在容器启动时运行 app.py
CMD ["python", "agvscheduling.py"]


# 使脚本具有可执行权限
# RUN chmod +x start.sh

# 在容器启动时运行脚本
# CMD ["./start.sh"]
