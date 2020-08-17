import shutil
import os
import re
import ipaddress
import paramiko
import logging
import socket
from paramiko.ssh_exception import AuthenticationException, SSHException
from tornado.web import HTTPError
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


def to_bytes(ustr, encoding='utf-8'):
    if isinstance(ustr, UnicodeType):
        return ustr.encode(encoding)
    return ustr


def to_int(string):
    try:
        return int(string)
    except (TypeError, ValueError):
        pass


def to_ip_address(ipstr):
    ip = to_str(ipstr)
    if ip.startswith('fe80::'):
        ip = ip.split('%')[0]
    return ipaddress.ip_address(ip)


def is_valid_ip_address(ipstr):
    try:
        to_ip_address(ipstr)
    except ValueError:
        return False
    return True


def is_valid_port(port):
    return 0 < port < 65536


def is_valid_encoding(encoding):
    try:
        u'test'.encode(encoding)
    except LookupError:
        return False
    return True


def is_ip_hostname(hostname):
    it = iter(hostname)
    if next(it) == '[':
        return True
    for ch in it:
        if ch != '.' and not ch.isdigit():
            return False
    return True


def is_valid_hostname(hostname):
    if hostname[-1] == '.':
        # strip exactly one dot from the right, if present
        hostname = hostname[:-1]
    if len(hostname) > 253:
        return False

    labels = hostname.split('.')

    # the TLD must be not all-numeric
    if numeric.match(labels[-1]):
        return False

    return all(allowed.match(label) for label in labels)


def is_same_primary_domain(domain1, domain2):
    i = -1
    dots = 0
    l1 = len(domain1)
    l2 = len(domain2)
    m = min(l1, l2)

    while i >= -m:
        c1 = domain1[i]
        c2 = domain2[i]

        if c1 == c2:
            if c1 == '.':
                dots += 1
                if dots == 2:
                    return True
        else:
            return False

        i -= 1

    if l1 == l2:
        return True

    if dots == 0:
        return False

    c = domain1[i] if l1 > m else domain2[i]
    return c == '.'


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
        raise ValueError('File {!r} does not exist'.format(options.cert_file))
    elif not os.path.isfile(options.key_file):
        raise ValueError('File {!r} does not exist'.format(options.key_file))
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


