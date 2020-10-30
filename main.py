import os.path
import tornado.web
import tornado.ioloop
from term1nal.conf import conf
from term1nal.handlers import IndexHandler, WSHandler, UploadHandler, DownloadHandler
from term1nal.utils import get_ssl_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
conf.base_dir = BASE_DIR


# check_encoding_setting(conf.encoding)


class Term1nal(tornado.web.Application):
    def __init__(self, loop):
        handlers = [
            (r"/", IndexHandler, dict(loop=loop)),
            (r"/ws", WSHandler, dict(loop=loop)),
            (r"/upload", UploadHandler, dict(loop=loop)),
            (r"/download", DownloadHandler, dict(loop=loop))
        ]

        settings = dict(
            websocket_ping_interval=conf.ws_ping,
            debug=conf.debug,
            xsrf_cookies=conf.xsrf,
            origin_policy=conf.origin,
            cookie_secret="_Valar_Morghulis_Valar_Dohaeris_"
        )

        settings["template_path"] = os.path.join(BASE_DIR, 'templates')
        settings["static_path"] = os.path.join(BASE_DIR, 'static')

        super().__init__(handlers, **settings)


def main():
    loop = tornado.ioloop.IOLoop.current()
    app = Term1nal(loop=loop)
    ssl_ctx = get_ssl_context(conf)
    server_settings = dict(
        xheaders=True,
        max_body_size=6000 * 1024 * 1024,  # 6G
    )
    app.listen(conf.port, conf.address, **server_settings)
    if ssl_ctx:
        server_settings.update(ssl_options=ssl_ctx)
        app.listen(conf.ssl_port, conf.host, **server_settings)
    loop.start()


if __name__ == '__main__':
    main()
