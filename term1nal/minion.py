import tornado.websocket

from tornado.ioloop import IOLoop
from tornado.iostream import _ERRNO_CONNRESET
from tornado.util import errno_from_exception
from term1nal.utils import LOG


BUFFER_SIZE = 64 * 1024
clients = {}  # {ip: {id: minion}}


class Minion:
    def __init__(self, loop, ssh, chan, dst_addr):
        self.loop = loop
        self.ssh = ssh
        self.chan = chan
        self.dst_addr = dst_addr
        self.fd = chan.fileno()
        self.id = str(id(self))
        self.data_to_dst = []
        self.handler = None
        self.mode = IOLoop.READ
        self.closed = False

    def __call__(self, fd, events):
        if events & IOLoop.READ:
            self.on_read()
        if events & IOLoop.WRITE:
            self.on_write()
        if events & IOLoop.ERROR:
            self.close(reason='ioloop error')

    def set_handler(self, handler):
        if not self.handler:
            self.handler = handler

    def update_handler(self, mode):
        if self.mode != mode:
            self.loop.update_handler(self.fd, mode)
            self.mode = mode
        if mode == IOLoop.WRITE:
            self.loop.call_later(0.1, self, self.fd, IOLoop.WRITE)

    def on_read(self):
        print(f"------------clients:{clients}")
        LOG.debug('minion {} on read'.format(self.id))
        try:
            data = self.chan.recv(BUFFER_SIZE)
        except (OSError, IOError) as e:
            LOG.error(e)
            if errno_from_exception(e) in _ERRNO_CONNRESET:
                self.close(reason='chan error on reading')
        else:
            LOG.debug('{!r} from {}:{}'.format(data, *self.dst_addr))
            if not data:
                self.close(reason='Bye ~')
                return

            LOG.debug('{!r} to {}:{}'.format(data, *self.handler.src_addr))
            try:
                self.handler.write_message(data, binary=True)
            except tornado.websocket.WebSocketClosedError:
                self.close(reason='websocket closed')

    def on_write(self):
        LOG.debug('minion {} on write'.format(self.id))
        if not self.data_to_dst:
            return

        data = ''.join(self.data_to_dst)
        LOG.debug('{!r} to {}:{}'.format(data, *self.dst_addr))

        try:
            sent = self.chan.send(data)
        except (OSError, IOError) as e:
            LOG.error(e)
            if errno_from_exception(e) in _ERRNO_CONNRESET:
                self.close(reason='chan error on writing')
            else:
                self.update_handler(IOLoop.WRITE)
        else:
            self.data_to_dst = []
            data = data[sent:]
            if data:
                self.data_to_dst.append(data)
                self.update_handler(IOLoop.WRITE)
            else:
                self.update_handler(IOLoop.READ)

    def close(self, reason=None):
        if self.closed:
            return
        self.closed = True

        LOG.info(
            'Closing minion {} with reason: {}'.format(self.id, reason)
        )
        if self.handler:
            self.loop.remove_handler(self.fd)
            self.handler.close(reason=reason)
        self.chan.close()
        self.ssh.close()
        LOG.info('Connection to {}:{} lost'.format(*self.dst_addr))

        clear_minion(self, clients)
        LOG.debug(clients)


def clear_minion(minion, clients):
    ip = minion.src_addr[0]
    minions = clients.get(ip)
    assert minion.id in minions
    minions.pop(minion.id)

    if not minions:
        clients.pop(ip)
        if not clients:
            clients.clear()


def recycle_minion(minion):
    if minion.handler:
        return
    LOG.warning('Recycling minion {}'.format(minion.id))
    minion.close(reason='minion recycled')
