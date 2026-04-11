import os
import time
import numpy

import thriftpy2
from thriftpy2.utils import serialize, deserialize
from thriftpy2.protocol.binary import TBinaryProtocolFactory
from thriftpy2.protocol.cybin import TCyBinaryProtocolFactory
from thriftpy2.protocol.cybin2 import TCyBinaryProtocolFactory2

HERE = os.path.dirname(__file__)
ndarray = thriftpy2.load(os.path.join(HERE, "ndarray.thrift"))


def make_ndarray(array: numpy.ndarray):
    msg = ndarray.NDArray()
    array = numpy.ascontiguousarray(array)
    msg.buffer = array.data
    msg.shape = array.shape
    msg.dtype = array.dtype.str
    return msg




SIZES = [
    1,
    2,
    5,
    10,
    20,
    50,
    100,
    200,
    500,
    1000,
    2000,
    5000,
    10_000,
    20_000,
    50_000,
    100_000,
    200_000,
    500_000,
    1_000_000,
    2_000_000,
    5_000_000,
    10_000_000,
    20_000_000,
    50_000_000,
    100_000_000,
]


def decode(n, proto_factory):
    ab = ndarray.NDArray()
    for size in SIZES:
        data = numpy.random.randint(0, 255, size=size, dtype=numpy.uint8)
        array_encoded = serialize(make_ndarray(data))
        durations = []
        for i in range(n):
            start = time.time()
            deserialize(ab, array_encoded, proto_factory)
            end = time.time()
            durations.append(end - start)
        duration = numpy.mean(durations)
        print(f"{type(proto_factory).__name__}\t{size}\t{duration}")


def main():
    n = 5

    decode(n, TBinaryProtocolFactory())
    decode(n, TCyBinaryProtocolFactory())
    decode(n, TCyBinaryProtocolFactory2())


if __name__ == "__main__":
    main()
