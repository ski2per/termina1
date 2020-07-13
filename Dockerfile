FROM python:3.7-slim
WORKDIR /
COPY . /
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt
EXPOSE 4433
ENTRYPOINT ["python", "main.py", "--address=0.0.0.0", "--certfile=/ssl.crt", "--keyfile=/ssl.key"]
