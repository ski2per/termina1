import os
import re
import ssl
import shutil
import paramiko
import logging
import socket
import asyncio
import concurrent.futures
from paramiko.ssh_exception import AuthenticationException, SSHException
from tornado.log import enable_pretty_logging
from urllib.parse import urlparse

enable_pretty_logging()

# GRU =  {
#     '172.16.66.66': {
#         '140580981443160': {
#             'minion': <term1nal.minion.Minion object at 0x7fdb8f760a58>,
#             'args': ('172.16.66.10', 22, 'root', 'P@ssw0rd')}
#     }
# }
GRU = {}


def get_logging_level():
    """ Return logging level by the value of environment variable"""
    log_dict = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "warning": logging.WARNING,
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
    }

    lvl = os.getenv("TERM_LOG_LEVEL", "info").strip().lower()
    return log_dict[lvl]


def logger(name='term1nal'):
    log = logging.getLogger(name)
    log.setLevel(get_logging_level())
    return log


LOG = logger()

UnicodeType = str

numeric = re.compile(r'[0-9]+$')
allowed = re.compile(r'(?!-)[a-z0-9-]{1,63}(?<!-)$', re.IGNORECASE)


def to_str(bstr, encoding='utf-8'):
    if isinstance(bstr, bytes):
        return bstr.decode(encoding)
    return bstr


def is_valid_encoding(encoding):
    try:
        'ted'.encode(encoding)
    except LookupError:
        return False
    return True


def get_ssl_context(options):
    if not options.cert_file and not options.key_file:
        return None
    elif not options.cert_file:
        raise ValueError('cert_file is not provided')
    elif not options.key_file:
        raise ValueError('key_file is not provided')
    elif not os.path.isfile(options.cert_file):
        raise ValueError(f'File {options.cert_file} does not exist')
    elif not os.path.isfile(options.key_file):
        raise ValueError(f'File {options.key_file} does not exist')
    else:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(options.cert_file, options.key_file)
        return ssl_ctx



def get_sftp_client(*args):
    host, port, username, password = args
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        client.connect(hostname=host, port=port, username=username, password=password)
        sftp = client.open_sftp()
        return sftp
    except (AuthenticationException, SSHException, socket.error) as err:
        print(err)


async def run_async_func(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, func, *args)
        return result
