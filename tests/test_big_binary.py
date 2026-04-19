# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
import multiprocessing
import sys
import time
from os import path

import pytest
from unittest import TestCase

import thriftpy2
from thriftpy2.rpc import client_context, make_server
from thriftpy2.transport.buffered import TBufferedTransportFactory
from thriftpy2.protocol.binary import TBinaryProtocolFactory

from thriftpy2._compat import CYTHON
logging.basicConfig(level=logging.INFO)

big_binary = thriftpy2.load(path.join(path.dirname(__file__),
                                       "big_binary.thrift"))


class Dispatcher:
    def echo(self, data):
        return data

    def size(self, data):
        return len(data.data)


@pytest.mark.skipif(sys.platform == "win32", reason="requires fork")
class BufferedTransportTestCase(TestCase):
    TRANSPORT_FACTORY = TBufferedTransportFactory()
    PROTOCOL_FACTORY = TBinaryProtocolFactory()

    PORT = 50001

    def mk_server(self):
        server = make_server(big_binary.ComputeService, Dispatcher(),
                             host="localhost", port=self.PORT,
                             proto_factory=self.PROTOCOL_FACTORY,
                             trans_factory=self.TRANSPORT_FACTORY)
        p = multiprocessing.Process(target=server.serve)
        return p

    def client(self):
        return client_context(big_binary.ComputeService,
                              host="localhost", port=self.PORT,
                              proto_factory=self.PROTOCOL_FACTORY,
                              trans_factory=self.TRANSPORT_FACTORY)

    def setUp(self):
        self.server = self.mk_server()
        self.server.start()
        time.sleep(0.1)

    def tearDown(self):
        if self.server.is_alive():
            self.server.terminate()
        if hasattr(big_binary.Data, "_prepare_buffer"):
            delattr(big_binary.Data, "_prepare_buffer")

    def test_1000(self):
        size = 1000
        data = big_binary.Data(size=size, data=b'a' * size)
        with self.client() as c:
            size = c.size(data)
            assert size == 1000

    def test_1000_000(self):
        size = 1000_000
        data = big_binary.Data(size=size, data=b'a' * size)
        with self.client() as c:
            size = c.size(data)
            assert size == 1000_000

    def test_10_000_000(self):
        size = 10_000_000
        data = big_binary.Data(size=size, data=b'a' * size)
        with self.client() as c:
            size = c.size(data)
            assert size == 10_000_000


if CYTHON:
    from thriftpy2.transport.buffered import TCyBufferedTransportFactory
    from thriftpy2.protocol.cybin import TCyBinaryProtocolFactory

    class TCyBufferedTransportTestCase(BufferedTransportTestCase):
        TRANSPORT_FACTORY = TCyBufferedTransportFactory()
        PROTOCOL_FACTORY = TCyBinaryProtocolFactory()
