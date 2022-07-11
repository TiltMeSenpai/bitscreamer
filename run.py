import sys
from amaranth_boards.ecpix5 import ECPIX585Platform
from amaranth.cli import main

from amaranth.build import Resource, Pins, Subsignal, Attrs

from bitscreamer import Top

Platform = ECPIX585Platform()

pmod_pins = [1, 2, 3, 4, 7, 8, 9, 10]

Platform.add_resources([
    Resource("outport", n, Pins(f"{pmod_pins[n]}", dir="io", conn=("pmod", 0)), Attrs(IO_TYPE="LVCMOS33"))
    for n in range(7)
])

if __name__ == "__main__":
    top = Top()
    if sys.argv[1] == "build":
        Platform.build(top, do_program=True)
    else:
        main(top, platform=Platform)