FROM alpine:3.10

WORKDIR /
COPY . /

RUN sed -i s/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g /etc/apk/repositories \
    # Install SSHD deps
    && apk update \
    && apk add bash git openssh rsync augeas shadow rssh python3 python3-dev py3-pip \
    # Install Python deps
    && apk add --no-cache --virtual .build-deps \
        gcc \
        make \
        linux-headers \
        bash \        
        alpine-sdk \
        libffi-dev \
        openssl-dev \
    && pip3 install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt \
    && apk del .build-deps \
    && deluser $(getent passwd 33 | cut -d: -f1) \
    && delgroup $(getent group 33 | cut -d: -f1) 2>/dev/null || true \
    && mkdir -p ~root/.ssh /etc/authorized_keys && chmod 700 ~root/.ssh/ \
    && augtool 'set /files/etc/ssh/sshd_config/AuthorizedKeysFile ".ssh/authorized_keys /etc/authorized_keys/%u"' \
    && echo -e "Port 22\n" >> /etc/ssh/sshd_config \
    && cp -a /etc/ssh /etc/ssh.cache \
    && rm -rf /var/cache/apk/*

EXPOSE 22
#EXPOSE 8000 4433
#ENTRYPOINT ["python", "main.py", "--address=0.0.0.0"]

COPY entry.sh /entry.sh

ENTRYPOINT ["/entry.sh"]

CMD ["/usr/sbin/sshd", "-D", "-e", "-f", "/etc/ssh/sshd_config"]
