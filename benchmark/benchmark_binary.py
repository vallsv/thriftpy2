import os
import time
import numpy

import thriftpy2
from thriftpy2.utils import serialize, deserialize
from thriftpy2.protocol.binary import TBinaryProtocolFactory
from thriftpy2.protocol.cybin import TCyBinaryProtocolFactory

HERE = os.path.dirname(__file__)
ndarray = thriftpy2.load(os.path.join(HERE, "ndarray.thrift"))


DATA = numpy.random.rand(1000, 1000)


def make_ndarray(array: numpy.ndarray):
    msg = ndarray.NDArray()
    array = numpy.ascontiguousarray(array)
    msg.buffer = array.data
    msg.shape = array.shape
    msg.dtype = array.dtype.str
    return msg


array_encoded = serialize(make_ndarray(DATA))


def encode(n, proto_factory):
    ab = make_ndarray(DATA)
    start = time.time()
    for i in range(n):
        serialize(ab, proto_factory)
    end = time.time()
    print(f"encode\t-> {end - start}")


def decode(n, proto_factory):
    ab = ndarray.NDArray()
    start = time.time()
    for i in range(n):
        deserialize(ab, array_encoded, proto_factory)
    end = time.time()
    print(f"decode\t-> {end - start}")


def main():
    n = 1000

    print(f"binary protocol struct benchmark for {n} times:")
    encode(n, TBinaryProtocolFactory())
    decode(n, TBinaryProtocolFactory())

    print(f"\ncybin protocol struct benchmark for {n} times:")
    encode(n, TCyBinaryProtocolFactory())
    decode(n, TCyBinaryProtocolFactory())


if __name__ == "__main__":
    main()
