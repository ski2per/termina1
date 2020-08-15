import os
import os.path
import logging
import ssl
from term1nal.utils import to_ip_address, parse_origin_from_url, is_valid_encoding

def get_bool_env(name, default=False) -> bool:
    """
    Return boolean value from environment varialbes, e.g.:
    ENV_NAME=true or ENV_NAME=1 will return True, or return False
    """
    result = default
    env_value = os.getenv(name)
    if env_value is not None:
        result = os.getenv(name).upper() in ("TRUE", "1")
    return result

class Conf(dict):
    def __init__(self, *args, **kwargs):
        super(Conf, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v
            if kwargs:
                for k, v in kwargs.items():
                    self[k] = v

    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Conf, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Conf, self).__delitem__(key)
        del self.__dict__[key]

conf = Conf()
conf.host = os.getenv("TERM_HOST", "")
conf.port = int(os.getenv("TERM_PORT", 8000))
conf.ssl_host = os.getenv("TERM_SSL_HOST", 0)
conf.ssl_port = int(os.getenv("TERM_SSL_PORT", 4433))
conf.cert_file= os.getenv("TERM_CERT_FILE", "")
conf.key_file= os.getenv("TERM_KEY_FILE", "")
conf.key_file= os.getenv("TERM_KEY_FILE", "")
conf.debug = get_bool_env("TERM_DEBUG", True)
conf.redirect = get_bool_env("TERM_REDIRECT", True)
conf.xsrf = get_bool_env("TERM_XSRF", False)
conf.origin = os.getenv("TERM_ORIGIN", "*")
conf.ws_ping = int(os.getenv("TERM_WS_PING", 0))
conf.timeout = int(os.getenv("TERM_TIMEOUT", 3))
conf.max_conn = int(os.getenv("TERM_MAX_CONN", 20))
conf.delay = int(os.getenv("TERM_MAX_CONN", 0))
conf.encoding = os.getenv("TERM_ENCODING", "")


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


def get_trusted_downstream(tdstream):
    result = set()
    for ip in tdstream.split(','):
        ip = ip.strip()
        if ip:
            to_ip_address(ip)
            result.add(ip)
    return result


def get_origin_setting(options):
    if options.origin == '*':
        if not options.debug:
            raise ValueError(
                'Wildcard origin policy is only allowed in debug mode.'
            )
        else:
            return '*'

    origin = options.origin.lower()
    if origin in ['same', 'primary']:
        return origin

    origins = set()
    for url in origin.split(','):
        orig = parse_origin_from_url(url)
        if orig:
            origins.add(orig)

    if not origins:
        raise ValueError('Empty origin list')

    return origins


def check_encoding_setting(encoding):
    if encoding and not is_valid_encoding(encoding):
        raise ValueError('Unknown character encoding {!r}.'.format(encoding))
