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
    # log_format = '[%(asctime)s] %(levelname)s [%(threadName)s]: %(message)s'
    # date_format = '%Y-%m-%d %H:%M:%S'
    # logging.basicConfig(format=log_format, datefmt=date_format)
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
        u'test'.encode(encoding)
    except LookupError:
        return False
    return True


def parse_origin_from_url(url):
    url = url.strip()
    if not url:
        return

    if not (url.startswith('http://') or url.startswith('https://') or
            url.startswith('//')):
        url = '//' + url

    parsed = urlparse(url)
    port = parsed.port
    scheme = parsed.scheme

    if scheme == '':
        scheme = 'https' if port == 443 else 'http'

    if port == 443 and scheme == 'https':
        netloc = parsed.netloc.replace(':443', '')
    elif port == 80 and scheme == 'http':
        netloc = parsed.netloc.replace(':80', '')
    else:
        netloc = parsed.netloc

    return '{}://{}'.format(scheme, netloc)


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


def check_encoding_setting(encoding):
    if encoding and not is_valid_encoding(encoding):
        raise ValueError('Unknown character encoding {!r}.'.format(encoding))


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


def make_sure_dir(dir):
    try:
        os.mkdir(dir)
    except FileExistsError:
        pass


def stage2_copy(src, *args):
    filename = os.path.basename(src)
    sftp = get_sftp_client(*args)
    sftp.put(src, os.path.join("/tmp", filename))


def stage1_copy(minion_id, dst, *args):
    local_dir = f"/tmp/{minion_id}"
    make_sure_dir(local_dir)

    file_name = os.path.basename(dst)

    sftp = get_sftp_client(*args)
    sftp.get(dst, os.path.join(local_dir, file_name))


def rm_dir(dir):
    shutil.rmtree(dir)

async def run_async_func(func, *args):
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, func, *args)
        return result