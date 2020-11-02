FROM python:3.7.9-alpine3.12

WORKDIR /
COPY . /
RUN sed -i s/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g /etc/apk/repositories \
    && apk add --no-cache --virtual .build-deps \
        gcc \
        make \
        linux-headers \
        bash \        
        alpine-sdk \
        libffi-dev \
        openssl-dev \
    && pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt \
    && apk del .build-deps

EXPOSE 8000 4433
ENTRYPOINT ["python", "main.py", "--address=0.0.0.0"]
