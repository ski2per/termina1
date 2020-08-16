import os.path
import tornado.web
import tornado.ioloop
from term1nal.conf import conf
from term1nal.handlers import IndexHandler, WSHandler, UploadHandler
from term1nal.utils import get_ssl_context, check_encoding_setting, LOG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
conf.base_dir = BASE_DIR
check_encoding_setting(conf.encoding)


class Term1nal(tornado.web.Application):
    def __init__(self, loop):
        handlers = [
            (r"/", IndexHandler, dict(loop=loop)),
            (r"/ws", WSHandler, dict(loop=loop)),
            (r"/upload", UploadHandler)
        ]

        settings = dict(
            # default_handler_class=NotFoundHandler,
            websocket_ping_interval=conf.ws_ping,
            debug=conf.debug,
            xsrf_cookies=conf.xsrf,
            origin_policy=conf.origin
        )

        settings["template_path"] = os.path.join(BASE_DIR, 'templates')
        settings["static_path"] = os.path.join(BASE_DIR, 'static')

        super().__init__(handlers, **settings)


def setup_listening(app, port, address, server_settings):
    app.listen(port, address, **server_settings)
    if not server_settings.get('ssl_options'):
        server_type = 'http'
    else:
        server_type = 'https'
    LOG.info('Listening on {}:{} ({})'.format(address, port, server_type))


def main():
    loop = tornado.ioloop.IOLoop.current()
    app = Term1nal(loop=loop)
    ssl_ctx = get_ssl_context(conf)
    server_settings = dict(
        xheaders=True,
        max_body_size=1000 * 1024 * 1024,  # 1G
    )
    setup_listening(app, conf.port, conf.address, server_settings)
    if ssl_ctx:
        server_settings.update(ssl_options=ssl_ctx)
        setup_listening(app, conf.ssl_port, conf.ssl_host, server_settings)
    loop.start()


if __name__ == '__main__':
    main()
