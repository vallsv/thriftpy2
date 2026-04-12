import sys
import os
import time
import random
try:
    import numpy
except ImportError:
    numpy = None
import thriftpy2
from thriftpy2.utils import serialize, deserialize
from thriftpy2.protocol.binary import TBinaryProtocolFactory
from thriftpy2.protocol.cybin import TCyBinaryProtocolFactory
from thriftpy2.protocol.cybin2 import TCyBinaryProtocolFactory2

HERE = os.path.dirname(__file__)
data_thrift = thriftpy2.load(os.path.join(HERE, "data.thrift"))


def make_string(size: int):
    msg = data_thrift.String()
    msg.data = random.randbytes(size).decode("ascii", errors="replace")
    return msg


def make_binary(size: int):
    msg = data_thrift.String()
    msg.data = random.randbytes(size)
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
    # 100_000_000,
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


def decode(
    proto_factory,
    min_n=1,
    min_time=None,
    binary=False,
):
    if binary:
        ab = data_thrift.Binary()
    else:
        ab = data_thrift.String()

    for size in SIZES:
        if binary:
            array_encoded = serialize(make_binary(size))
        else:
            array_encoded = serialize(make_string(size))

        durations = []
        start_test = time.time()
        i = 0
        while True:
            d = time.time() - start_test
            if i >= min_n and (min_time is None or d > min_time):
                break
            start = time.time()
            result = deserialize(ab, array_encoded, proto_factory)
            end = time.time()
            durations.append(end - start)
            i = i + 1

        if numpy is None:
            durations = sorted(durations)
            duration = durations[len(durations) // 2]
        else:
            duration = mean_without_outliers(durations)
        print(f"{type(proto_factory).__name__}\t{size}\t{i}\t{duration}")


def main():
    args = ""
    if len(sys.argv) > 1:
        args = sys.argv[1]

    binary = "b" in args
    fast = "f" in args

    if fast:
        min_n = 10
        min_time = 1
    else:
        min_n = 100
        min_time = 10

    if binary:
        print("Benchmark for binary decoding")
    else:
        print("Benchmark for string decoding")
    if numpy is None:
        print(f"  - Median")
    else:
        print(f"  - Mean without outliers")
    print(f"  - From least {min_n} iterations")
    print(f"  - And at least {min_time}s of iterating")
    print()

    proto_factories = [
        TBinaryProtocolFactory(),
        TCyBinaryProtocolFactory(),
        TCyBinaryProtocolFactory2(),
    ]

    for proto_factory in proto_factories:
        decode(
            proto_factory=proto_factory,
            min_n=min_n,
            min_time=min_time,
        )


if __name__ == "__main__":
    main()
