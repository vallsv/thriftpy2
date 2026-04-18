# -*- coding: utf-8 -*-

import struct

from thriftpy2._compat import CYTHON
from thriftpy2.transport.base import TTransportBase, readall, readall_into


BUFFER_SIZE = 4


class TChunkedTransport(TTransportBase):
    """
    Framed transport which chunk the data
    """
    DEFAULT_BUFFER = 4096

    def __init__(self, trans: TTransportBase, buf_size: int = DEFAULT_BUFFER):
        self.__buf_size = buf_size
        self.__trans = trans
        self.__rremain = 0
        self.__rbuf = memoryview(bytearray(buf_size)).cast("B")
        self.__rbuf_data = self.__rbuf[0:0]
        """Store the remaining nbytes of the frame to read"""
        self.__wbuf = memoryview(bytearray(buf_size + BUFFER_SIZE))
        # let the space for the final buffer size i32
        self.__wbuf_data = self.__wbuf[BUFFER_SIZE:].cast("B")
        self.__wcount = 0

    def is_open(self):
        return self.__trans.is_open()

    def open(self):
        return self.__trans.open()

    def close(self):
        self.__rremain = 0
        self.__wcount = 0
        return self.__trans.close()

    def read(self, sz: int) -> bytes:
        result = bytearray(sz)
        cur = memoryview(result)
        self.read_into(sz, cur)
        return result

    def read_into(self, sz: int, buf: memoryview):
        """
        Read a fixed `sz` amount of bytes into a pre-allocated `buf` buffer.

        FIXME: Do not create views
        """
        if sz == 0:
            return
        assert sz > 0
        buf = buf.cast("B")

        while sz > 0:
            if self.__rbuf_data.nbytes == 0:
                if self.__rremain == 0:
                    # read a frame
                    bsize = readall(self.__trans.read, BUFFER_SIZE)
                    size, = struct.unpack('!i', bsize)
                    assert size > 0

                    if size <= sz:
                        # Shortcut the intermediate buffer
                        readall_into(self.__trans.read_into, size, buf)
                        buf = buf[size:]
                        sz -= size
                        continue

                    self.__rbuf_data = self.__rbuf[0:0]
                    self.__rremain = size

                bread = min(self.__rremain, self.__buf_size)
                readall_into(self.__trans.read_into, bread, self.__rbuf)
                self.__rremain -= bread
                self.__rbuf_data = self.__rbuf[0:bread]

            size = min(self.__rbuf_data.nbytes, sz)
            buf[0:size] = self.__rbuf_data[0:size]
            self.__rbuf_data = self.__rbuf_data[size:]
            buf = buf[size:]
            sz -= size

    def write(self, buf: bytes | memoryview):
        """
        FIXME: Do not create views
        """
        buf = memoryview(buf)
        buf = buf.cast("B")
        if buf.nbytes == 0:
            return
        space_left = self.__buf_size - self.__wcount

        # while it can fulfill the buffer
        while buf.nbytes >= space_left:
            chuck_size = min(buf.nbytes, space_left)
            self.__wbuf_data[self.__wcount:self.__wcount + chuck_size] = buf[0:chuck_size]
            self.__wcount += chuck_size
            self.flush()
            buf = buf[chuck_size:]
            space_left = self.__buf_size

        # this does not fulfill
        if buf.nbytes > 0:
            self.__wbuf_data[self.__wcount:self.__wcount+buf.nbytes] = buf[:]
            self.__wcount += buf.nbytes

    def flush(self):
        if self.__wcount == 0:
            self.__trans.flush()
            return
        # get a view
        wout = self.__wbuf[0:self.__wcount + BUFFER_SIZE]
        # prepend the final size
        wout[0:4] = struct.pack("!i", len(wout) - BUFFER_SIZE)
        buf = struct.pack("!i", len(wout))
        self.__trans.write(wout)
        self.__trans.flush()
        # release the buffer
        self.__wcount = 0


class TChunkedTransportFactory(object):
    def __init__(self, buffer_size: int | None = None):
        self.buffer_size = buffer_size

    def get_transport(self, trans):
        kwargs = {}
        if self.buffer_size is not None:
            kwargs["buffer_size"] = self.buffer_size
        return TChunkedTransport(trans, **kwargs)


if CYTHON:
    from .cychunked import TCyChunkedTransport, TCyChunkedTransportFactory  # noqa
