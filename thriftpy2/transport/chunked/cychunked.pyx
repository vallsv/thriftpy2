# cython: freethreading_compatible = True

from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
from libc.stdint cimport int32_t
from cpython.memoryview cimport PyMemoryView_FromMemory
from cpython.buffer cimport PyBUF_WRITE, PyBUF_READ

from thriftpy2.transport.cybase cimport (
    TCyBuffer,
    CyTransportBase,
    DEFAULT_BUFFER,
    STACK_STRING_LEN
)

from .. import TTransportException


cdef extern from "../../protocol/cybin/endian_port.h":
    int32_t be32toh(int32_t n)
    int32_t htobe32(int32_t n)


cdef const int FRAME_SIZE = 4


cdef class TCyChunkedTransport(CyTransportBase):
    cdef:
        TCyBuffer rframe_buf, wframe_buf
        int bytes_in_trans

    def __init__(self, trans, int buf_size=DEFAULT_BUFFER):
        self.trans = trans
        assert buf_size > FRAME_SIZE
        self.bytes_in_trans = 0
        self.rframe_buf = TCyBuffer(buf_size)
        self.wframe_buf = TCyBuffer(buf_size)
        # Prealloc the buffer size
        self.wframe_buf.data_size += FRAME_SIZE

    cdef c_read(self, int sz, char *obj_out):
        cdef int remain, size

        if sz <= 0:
            return 0

        remain = sz

        # Read the buffer
        if self.rframe_buf.data_size > 0:
            size = self.rframe_buf.move_into(remain, obj_out)
            remain -= size
            obj_out += size

        if remain:
            self.read_frame(remain, obj_out)

        return sz

    cdef read_frame(self, int sz, char *obj_out):
        cdef:
            int size
            char frame_len[4]
            char stack_frame[STACK_STRING_LEN]
            int32_t frame_size

        assert self.rframe_buf.cur == 0

        while sz:
            if self.bytes_in_trans == 0:
                # The next 4-bytes are the frame size
                # but we read everything we can in the buffer
                size = self.read_trans(FRAME_SIZE, self.rframe_buf.buf_size, self.rframe_buf.buf)
                frame_size = be32toh((<int32_t*>self.rframe_buf.buf)[0])
                self.rframe_buf.cur = FRAME_SIZE
                self.rframe_buf.data_size = size - FRAME_SIZE
                self.bytes_in_trans = frame_size - size + FRAME_SIZE

                # Move what we can in the obj_out
                size = self.rframe_buf.move_into(sz, obj_out)
                obj_out += size
                sz -= size

                # The buffer is empty or the obj_out is full
                assert self.rframe_buf.data_size == 0 or sz == 0
            else:
                # Read all we can expect the next frame_size
                if sz >= self.bytes_in_trans:
                    # The obj_out is big enough, it's the same as using the buffer,
                    # but we win a memory copy
                    size = self.bytes_in_trans
                    self.read_trans(size, size, obj_out)
                    obj_out += size
                    self.bytes_in_trans = 0
                    sz -= size
                else:
                    # Read into the buffer
                    size = min(self.rframe_buf.buf_size, self.bytes_in_trans)
                    self.read_trans(size, size, self.rframe_buf.buf)
                    self.rframe_buf.data_size += size
                    self.bytes_in_trans -= size

                    # Move what we can in the obj_out
                    size = self.rframe_buf.move_into(sz, obj_out)
                    obj_out += size
                    sz -= size

                    # The buffer is empty or the obj_out is full
                    assert self.rframe_buf.data_size == 0 or sz == 0

    cdef read_trans(self, int min, int max, char *out):
        """
        Read the transport until `min` bytes is read, and
        up to `max` bytes. Return the number of bytes read.
        """
        cdef int count, size

        view = PyMemoryView_FromMemory(out, max, PyBUF_WRITE)
        count = 0
        while count < min:
            size = self.trans.read_into(max - count, view)
            view = view[size:]
            if size <= 0:
                raise TTransportException(TTransportException.END_OF_FILE,
                                          "End of file reading from transport")
            count += size

        return count

    cdef c_write(self, const char *data, int sz):
        cdef int r
        cdef int chuck_size

        if sz == 0:
            return

        # while it can fulfill the buffer
        cdef int space_left = self.wframe_buf.buf_size - self.wframe_buf.data_size
        while sz >= space_left:
            chuck_size = min(sz, space_left)
            r = self.wframe_buf.write(chuck_size, data)
            if r == -1:
                raise MemoryError("Write to buffer error")

            data += chuck_size
            sz -= chuck_size
            self.c_flush()
            space_left = self.wframe_buf.buf_size - self.wframe_buf.data_size

        # this does not fulfill
        if sz > 0:
            r = self.wframe_buf.write(sz, data)
            if r == -1:
                raise MemoryError("Write to buffer error")

    cdef c_flush(self):
        cdef:
            int32_t frame_size
            memoryview view
            char *size_str

        if self.wframe_buf.data_size > FRAME_SIZE:
            frame_size = htobe32(self.wframe_buf.data_size - FRAME_SIZE)
            (<int32_t*>self.wframe_buf.buf)[0] = frame_size

            view = PyMemoryView_FromMemory(self.wframe_buf.buf, self.wframe_buf.data_size, PyBUF_READ)
            self.trans.write(view)
            self.trans.flush()
            self.wframe_buf.clean()
            # Prealloc the buffer size
            self.wframe_buf.data_size += FRAME_SIZE

    def read(self, int sz):
        return self.get_string(sz)

    def write(self, bytes data):
        cdef int sz = len(data)
        self.c_write(data, sz)

    def flush(self):
        self.c_flush()

    def is_open(self):
        return self.trans.is_open()

    def open(self):
        return self.trans.open()

    def close(self):
        return self.trans.close()

    def clean(self):
        self.rframe_buf.clean()
        self.wframe_buf.clean()
        # Prealloc the buffer size
        self.wframe_buf.data_size += FRAME_SIZE
        self.bytes_in_trans = 0


class TCyChunkedTransportFactory(object):
    def get_transport(self, trans):
        return TCyChunkedTransport(trans)
