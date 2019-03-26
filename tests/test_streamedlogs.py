from random import randrange
from urllib.parse import urlsplit
from json import dumps

import pytest
from pytest_twisted import inlineCallbacks

from test_tahoe import reactor, tahoe

from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketServerFactory,
    WebSocketServerProtocol,

)

from twisted.internet.task import deferLater
from twisted.internet.endpoints import HostnameEndpoint

from gridsync.tahoe import Tahoe
from gridsync.streamedlogs import StreamedLogs

def test_do_nothing_before_start(reactor, tahoe):
    """
    ``StreamedLogs`` doesn't connect to anything before it is started.
    """
    assert reactor.connectTCP.call_count == 0


def test_connect_to_nodeurl(reactor, tahoe):
    """
    When ``StreamedLogs`` starts it tries to connect to the streaming log
    WebSocket endpoint run by the Tahoe-LAFS node.
    """
    tahoe.streamedlogs.start()

    host, port, factory = reactor.connectTCP.call_args[0]
    expected_url = urlsplit(tahoe.nodeurl)

    assert "{}:{}".format(host, port) == expected_url.netloc


def fake_log_server(protocol):
    from twisted.internet import reactor
    while True:
        port_number = randrange(10000, 60000)
        # Why do you make me know the port number in advance, Autobahn?
        factory = WebSocketServerFactory(u"ws://127.0.0.1:{}".format(port_number))
        factory.protocol = protocol

        try:
            server_port = reactor.listenTCP(port_number, factory)
        except CannotListenError as e:
            if e.socketError.errno == EADDRINUSE:
                continue
            raise
        else:
            break

    return server_port


class FakeLogServerProtocol(WebSocketServerProtocol):
    FAKE_MESSAGE = dumps({"fake": "message"})

    def onOpen(self):
        self.sendMessage(
            self.FAKE_MESSAGE.encode("utf-8"),
            isBinary=False,
        )


def twlog():
    from sys import stdout
    from twisted.logger import globalLogBeginner
    from twisted.logger import textFileLogObserver
    globalLogBeginner.beginLoggingTo([textFileLogObserver(stdout)])


def connect_to_log_endpoint(reactor, tahoe, real_reactor):
    server_port = fake_log_server(FakeLogServerProtocol)
    server_addr = server_port.getHost()

    # Make sure the streamed logs websocket client can compute the correct ws
    # url.  If it doesn't match the server, the handshake fails.
    tahoe.set_nodeurl("http://{}:{}".format(server_addr.host, server_addr.port))

    tahoe.streamedlogs.start()
    _, _, client_factory = reactor.connectTCP.call_args[0]

    endpoint = HostnameEndpoint(real_reactor, server_addr.host, server_addr.port)
    return endpoint.connect(client_factory)


@inlineCallbacks
def test_collect_eliot_logs(reactor, tahoe):
    """
    ``StreamedLogs`` saves the JSON log messages so that they can be retrieved
    using ``Tahoe.get_streamed_log_messages``.
    """
    from twisted.internet import reactor as real_reactor

    yield connect_to_log_endpoint(reactor, tahoe, real_reactor)

    # Arbitrarily give it about a second to deliver the message.  All the I/O
    # is loopback and the data is small.  One second should be plenty of time.
    for i in range(20):
        messages = tahoe.get_streamed_log_messages()
        if FakeLogServerProtocol.FAKE_MESSAGE in messages:
            break
        yield deferLater(real_reactor, 0.1, lambda: None)

    messages = tahoe.get_streamed_log_messages()
    assert FakeLogServerProtocol.FAKE_MESSAGE in messages


@inlineCallbacks
def test_reconnect_to_websocket(reactor, tahoe):
    """
    If the connection to the WebSocket endpoint is lost, an attempt is made to
    re-establish.
    """
    # This test might be simpler and more robust if it used
    # twisted.internet.task.Clock and twisted.test.proto_helpers.MemoryReactor
    # instead of a Mock reactor.
    from twisted.internet import reactor as real_reactor

    client_protocol = yield connect_to_log_endpoint(reactor, tahoe, real_reactor)
    client_protocol.transport.abortConnection()

    for i in range(100):
        for call in reactor.callLater.call_args_list:
            args, kwargs = call
            delay, func = args[:2]
            posargs = args[2:]
            func(*posargs, **kwargs)

        reactor.callLater.reset_mock()

        if reactor.connectTCP.call_count >= 2:
            break
        yield deferLater(real_reactor, 0.01, lambda: None)

    assert reactor.connectTCP.call_count >= 2
    host, port, _ = reactor.connectTCP.call_args[0]

    expected_url = urlsplit(tahoe.nodeurl)
    assert "{}:{}".format(host, port) == expected_url.netloc
