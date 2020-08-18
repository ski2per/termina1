import os.path
import json
import socket
import struct
import traceback
import weakref
import paramiko
import tornado.web

from tornado import iostream
from tornado.ioloop import IOLoop
from concurrent.futures import ThreadPoolExecutor
from tornado.process import cpu_count
from term1nal.conf import conf
from term1nal.utils import to_str, UnicodeType, is_valid_encoding
from term1nal.minion import Minion, recycle_minion, GRU
from term1nal.utils import LOG, make_sure_dir, stage2_copy, stage1_copy, rm_dir

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

DELAY = 3
DEFAULT_PORT = 22


class InvalidValueError(Exception):
    pass


class SSHClient(paramiko.SSHClient):

    def handler(self, prompt_list):
        answers = []
        for prompt_, _ in prompt_list:
            prompt = prompt_.strip().lower()
            if prompt.startswith('password'):
                answers.append(self.password)
            else:
                raise ValueError('Unknown prompt: {}'.format(prompt_))
        return answers

    def auth_interactive(self, username, handler):
        self._transport.auth_interactive(username, handler)

    def _auth(self, username, password, pkey, *args):
        self.password = password
        LOG.info('Trying password authentication')
        try:
            self._transport.auth_password(username, password)
            return
        except paramiko.SSHException as e:
            saved_exception = e
            assert saved_exception is not None
            raise saved_exception


class MixinHandler:
    def initialize(self, loop):
        self.context = self.request.connection.context
        self.loop = loop

    def get_value(self, name):
        value = self.get_argument(name)
        print(f"value: {value}")
        if not value:
            raise InvalidValueError('Missing value {}'.format(name))
        return value

    def get_query_value(self, name):
        value = self.get_query_argument(name)
        if not value:
            raise InvalidValueError('Missing value {}'.format(name))
        return value

    def get_client_endpoint(self) -> set:
        return self.get_real_client_addr() or self.context.address[:2]

    def get_real_client_addr(self):
        ip = self.request.remote_ip

        if ip == self.request.headers.get("X-Real-Ip"):
            port = self.request.headers.get("X-Real-Port")
        elif ip in self.request.headers.get("X-Forwarded-For", ""):
            port = self.request.headers.get("X-Forwarded-Port")
        else:
            return
        port = int(port)
        return ip, port


class IndexHandler(MixinHandler, tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=cpu_count() * 5)

    def initialize(self, loop):
        super(IndexHandler, self).initialize(loop=loop)
        self.ssh_client = self.get_ssh_client()
        self.debug = self.settings.get('debug', False)
        self.result = dict(id=None, status=None, encoding=None)

    def write_error(self, status_code, **kwargs):
        if self.request.method == 'POST':
            exc_info = kwargs.get('exc_info')
            if exc_info:
                reason = getattr(exc_info[1], 'log_message', None)
                if reason:
                    self._reason = reason
            self.result.update(status=self._reason)
            self.set_status(200)
            self.finish(self.result)
        else:
            super(IndexHandler, self).write_error(status_code, **kwargs)

    def get_ssh_client(self):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(paramiko.client.WarningPolicy)
        return ssh

    def get_args(self):
        hostname = self.get_value('hostname')
        port = int(self.get_value('port'))
        username = self.get_value('username')
        password = self.get_argument('password', u'')
        args = (hostname, port, username, password)
        LOG.debug(args)
        return args

    def parse_encoding(self, data):
        try:
            encoding = to_str(data.strip(), 'ascii')
        except UnicodeDecodeError:
            return

        if is_valid_encoding(encoding):
            return encoding

    def get_default_encoding(self, ssh):
        commands = [
            '$SHELL -ilc "locale charmap"',
            '$SHELL -ic "locale charmap"'
        ]

        for command in commands:
            try:
                _, stdout, _ = ssh.exec_command(command, get_pty=True)
            except paramiko.SSHException as exc:
                LOG.info(str(exc))
            else:
                data = stdout.read()
                LOG.debug('{!r} => {!r}'.format(command, data))
                result = self.parse_encoding(data)
                if result:
                    return result

        LOG.warning('Could not detect the default encoding.')
        return 'utf-8'

    def ssh_connect(self, args):
        ssh = self.ssh_client
        ssh_endpoint = args[:2]
        LOG.info('Connecting to {}:{}'.format(*ssh_endpoint))

        try:
            ssh.connect(*args, timeout=conf.timeout)
        except socket.error:
            raise ValueError('Unable to connect to {}:{}'.format(*ssh_endpoint))
        except paramiko.BadAuthenticationType:
            raise ValueError('Bad authentication type.')
        except paramiko.AuthenticationException:
            raise ValueError('Authentication failed.')
        except paramiko.BadHostKeyException:
            raise ValueError('Bad host key.')

        term = self.get_argument('term', u'') or u'xterm'
        shell_channel = ssh.invoke_shell(term=term)
        shell_channel.setblocking(0)
        minion = Minion(self.loop, ssh, shell_channel, ssh_endpoint)
        minion.encoding = conf.encoding if conf.encoding else self.get_default_encoding(ssh)
        return minion

    def get(self):
        self.render('index.html', debug=self.debug)

    @tornado.gen.coroutine
    def post(self):
        ip, port = self.get_client_endpoint()
        minions = GRU.get(ip, {})
        if minions and len(minions) >= conf.max_conn:
            raise tornado.web.HTTPError(403, 'too many connections')

        try:
            args = self.get_args()
        except InvalidValueError as err:
            raise tornado.web.HTTPError(400, str(err))

        future = self.executor.submit(self.ssh_connect, args)

        try:
            minion = yield future
        except (ValueError, paramiko.SSHException) as err:
            LOG.error(traceback.format_exc())
            self.result.update(status=str(err))
        else:
            if not minions:
                GRU[ip] = minions
            minion.src_addr = (ip, port)
            minions[minion.id] = {
                "minion": minion,
                "args": args
            }
            self.loop.call_later(conf.delay or DELAY, recycle_minion, minion)
            self.result.update(id=minion.id, encoding=minion.encoding)

        self.write(self.result)


class WSHandler(MixinHandler, tornado.websocket.WebSocketHandler):

    def initialize(self, loop):
        super(WSHandler, self).initialize(loop=loop)
        self.minion_ref = None

    def open(self):
        self.src_addr = self.get_client_endpoint()
        LOG.info('Connected from {}:{}'.format(*self.src_addr))

        minions = GRU.get(self.src_addr[0])
        if not minions:
            self.close(reason='Websocket authentication failed.')
            return

        try:
            minion_id = self.get_value('id')
            LOG.debug(f"############ minion id: {minion_id}")

        except (tornado.web.MissingArgumentError, InvalidValueError) as err:
            self.close(reason=str(err))
        else:
            minion = minions.get(minion_id)["minion"]
            if minion:
                minions[minion_id]["minion"] = None
                self.set_nodelay(True)
                minion.set_handler(self)
                self.minion_ref = weakref.ref(minion)
                self.loop.add_handler(minion.fd, minion, IOLoop.READ)
            else:
                self.close(reason='Websocket authentication failed.')

    def on_message(self, message):
        LOG.debug('{!r} from {}:{}'.format(message, *self.src_addr))
        minion = self.minion_ref()
        try:
            msg = json.loads(message)
        except JSONDecodeError:
            return

        if not isinstance(msg, dict):
            return

        resize = msg.get('resize')
        if resize and len(resize) == 2:
            try:
                minion.chan.resize_pty(*resize)
            except (TypeError, struct.error, paramiko.SSHException):
                pass

        data = msg.get('data')
        if data and isinstance(data, UnicodeType):
            minion.data_to_dst.append(data)
            minion.on_write()

    def on_close(self):
        LOG.info('Disconnected from {}:{}'.format(*self.src_addr))
        if not self.close_reason:
            self.close_reason = 'client disconnected'

        minion = self.minion_ref() if self.minion_ref else None
        if minion:
            minion.close(reason=self.close_reason)


class UploadHandler(MixinHandler, tornado.web.RequestHandler):
    def initialize(self, loop):
        super(UploadHandler, self).initialize(loop=loop)

    def post(self):
        minion_id = self.get_value("minion")
        client_ip = self.get_client_endpoint()[0]
        gru = GRU.get(client_ip, {})
        args = gru[minion_id]["args"]

        file = self.request.files["upload"][0]
        original_filename = file["filename"]
        file_path = f"/tmp/{minion_id}/{original_filename}"

        make_sure_dir(f"/tmp/{minion_id}")
        with open(file_path, "wb") as f:
            f.write(file["body"])

        stage2_copy(file_path, *args)

        # self.finish(f"中转完成，目标位置: /tmp/{original_filename}")
        self.finish(f"/tmp/{original_filename}")
        print("upload ended")
        rm_dir(f"/tmp/{minion_id}")


class DownloadHandler(MixinHandler, tornado.web.RequestHandler):
    def initialize(self, loop):
        super(DownloadHandler, self).initialize(loop=loop)

    async def get(self):
        chunk_size = 1024 * 1024 * 1  # 1 MiB

        remote_file_path = self.get_query_value("filepath")
        print(remote_file_path)
        minion_id = self.get_value("minion")
        print(f"minion ID: {minion_id}")
        client_ip = self.get_client_endpoint()[0]
        gru = GRU.get(client_ip, {})
        args = gru[minion_id]["args"]

        try:
            stage1_copy(minion_id, remote_file_path, *args)
        except FileNotFoundError as err:
            LOG.error(err)
            raise tornado.web.HTTPError(404)
            return

        filename = os.path.basename(remote_file_path)
        local_file = os.path.join("/tmp", minion_id, filename)

        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Disposition", f"attachment; filename={filename}")
        # with open(local_file, "rb") as f:
        #     self.write(f.read())
        with open(local_file, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                try:
                    # write the chunk to response
                    self.write(chunk)
                    # send the chunk to client
                    await self.flush()
                except iostream.StreamClosedError:
                    break
                finally:
                    del chunk
                    await tornado.web.gen.sleep(0.000000001)  # 1 nanosecond


        print("download ended")
        rm_dir(f"/tmp/{minion_id}")
