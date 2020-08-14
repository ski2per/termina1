import os.path
import logging
import tornado.web
import tornado.ioloop
from tornado.options import options
from term1nal import handlers
from term1nal.handlers import IndexHandler, WSHandler, NotFoundHandler
from term1nal.settings import get_app_settings, get_host_keys_settings, get_policy_setting, get_ssl_context, \
    get_server_settings, check_encoding_setting


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
options.parse_command_line()
check_encoding_setting(options.encoding)


class Term1nal(tornado.web.Application):
    def __init__(self, loop):
        host_keys_settings = get_host_keys_settings(options)
        policy = get_policy_setting(options, host_keys_settings)

        handlers = [
            (r'/', IndexHandler, dict(loop=loop, policy=policy,
                                      host_keys_settings=host_keys_settings)),
            (r'/ws', WSHandler, dict(loop=loop,))
        ]

        settings =  get_app_settings(options)

        # template_path=os.path.join(BASE_DIR, 'templates'),
        # static_path=os.path.join(BASE_DIR, 'static'),
        settings["template_path"] = os.path.join(BASE_DIR, 'templates')
        settings["static_path"] = os.path.join(BASE_DIR, 'static')

        super().__init__(handlers, **settings)


# def make_handlers(loop, options):
#     host_keys_settings = get_host_keys_settings(options)
#     policy = get_policy_setting(options, host_keys_settings)
#
#     handlers = [
#         (r'/', IndexHandler, dict(loop=loop, policy=policy,
#                                   host_keys_settings=host_keys_settings)),
#         (r'/ws', WSHandler, dict(loop=loop))
#     ]
#     return handlers


def setup_listening(app, port, address, server_settings):
    app.listen(port, address, **server_settings)
    if not server_settings.get('ssl_options'):
        server_type = 'http'
    else:
        server_type = 'https'
        handlers.redirecting = True if options.redirect else False
    logging.info(
        'Listening on {}:{} ({})'.format(address, port, server_type)
    )


def main():
    handlers.redirecting = True if options.redirect else False
    loop = tornado.ioloop.IOLoop.current()
    app = Term1nal(loop=loop)
    ssl_ctx = get_ssl_context(options)
    server_settings = get_server_settings(options)
    setup_listening(app, options.port, options.address, server_settings)
    if ssl_ctx:
        server_settings.update(ssl_options=ssl_ctx)
        setup_listening(app, options.sslport, options.ssladdress, server_settings)
    loop.start()


if __name__ == '__main__':
    main()
