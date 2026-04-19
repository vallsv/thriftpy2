import sys
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


def NDArray_prepare_buffer(obj, attr_name: bytes) -> memoryview | None:
    """
    Prepare the memory for the buffer.
    """
    if attr_name == "buffer":
        array = numpy.empty(obj.shape, dtype=obj.dtype)
        obj.array = array
        return memoryview(array.data)

    return None


def decode_numpy(msg, enforce_writable: bool, enforce_prepared: bool) -> numpy.ndarray:
    if enforce_prepared:
        return msg.array

    array = numpy.frombuffer(
        msg.buffer,
        msg.dtype,
    )

    if enforce_writable and not array.flags.writeable:
        # if the buffer is not writable (from bytes)
        # we have to copy the memory
        array = numpy.array(array)

    array.shape = msg.shape
    return array


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


def mean_without_outliers(dd):
    """
    Return the mean, removing outliers.

    The 10% percent smallest and biggest values are ignored.
    """
    if len(dd) == 0:
        return float("nan")
    dd = numpy.array(dd)
    vmin, vmax = numpy.percentile(dd, (10, 90))
    dd[numpy.logical_or(vmin < dd, dd > vmax)] = numpy.nan
    vmean = numpy.nanmean(dd)
    return float(vmean)


ab = ndarray.NDArray()


def decode(
    name: str,
    size: int,
    proto_factory,
    min_n=1,
    min_time=None,
    as_numpy_array=False,
    as_writable=False,
    as_prepared=False,
):
    if as_prepared:
        ndarray.NDArray._prepare_buffer = NDArray_prepare_buffer
    else:
        if hasattr(ndarray.NDArray, "_prepare_buffer"):
            delattr(ndarray.NDArray, "_prepare_buffer")

    data = numpy.random.randint(0, 255, size=size, dtype=numpy.uint8)
    array_encoded = serialize(make_ndarray(data))
    durations = []
    start_test = time.time()
    i = 0
    while True:
        d = time.time() - start_test
        if i >= min_n and (min_time is None or d > min_time):
            break
        start = time.time()
        result = deserialize(ab, array_encoded, proto_factory)
        if as_numpy_array:
            result = decode_numpy(
                result,
                enforce_writable=as_writable,
                enforce_prepared=as_prepared,
            )
        end = time.time()
        durations.append(end - start)
        if i == 0:
            # sanity check only once
            if as_numpy_array:
                numpy.testing.assert_allclose(data, result)
        i = i + 1

    duration = mean_without_outliers(durations)
    print(f"{name:<12s}\t{size}\t{i}\t{duration}")


def main():
    args = ""
    if len(sys.argv) > 1:
        args = sys.argv[1]
    fast = "f" in args
    as_writable = "w" in args
    as_numpy_array = "n" in args

    if fast:
        min_n = 10
        min_time = 1
    else:
        min_n = 100
        min_time = 10

    print("Benchmark for numpy decoding")
    print(f"  - Mean without outliers")
    print(f"  - From least {min_n} iterations")
    print(f"  - And at least {min_time}s of iterating")
    if as_numpy_array:
        print("  - Decode as numpy array")
        if as_writable:
            print("  - Enforce writable numpy array")
    print()

    options_series = [
        ("bin-py", TBinaryProtocolFactory(), False),
        ("bin-cy", TCyBinaryProtocolFactory(), False),
        ("binp-cy", TCyBinaryProtocolFactory2(), False),
        ("bin-py-pref", TBinaryProtocolFactory(), True),
    ]

    for size in SIZES:
        for options in options_series:
            name, proto_factory, as_prepared = options
            decode(
                name=name,
                size=size,
                proto_factory=proto_factory,
                min_n=min_n,
                min_time=min_time,
                as_numpy_array=as_numpy_array,
                as_writable=as_writable,
                as_prepared=as_prepared,
            )


if __name__ == "__main__":
    main()
