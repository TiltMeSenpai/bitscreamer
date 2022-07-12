from more_itertools import flatten
from nmigen import *
from luna.gateware.stream.generator import ConstantStreamGenerator

import itertools

def make_sim_stream():
    return ConstantStreamGenerator(
        constant_data = list(itertools.chain.from_iterable([
            [n, 0, 255-n] for n in range(255)
        ])),
        max_length_width=10,
        domain="usb"
    )