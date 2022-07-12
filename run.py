import sys
from amaranth_boards.ecpix5 import ECPIX585Platform
from amaranth.cli import main

from amaranth.build import Resource, Pins, Attrs

from amaranth.sim import Simulator

from bitscreamer import Top

Platform = ECPIX585Platform()

pmod_pins = [1, 2, 3, 4, 7, 8, 9, 10]

Platform.add_resources([
    Resource("outport", n, Pins(f"{pmod_pins[n]}", dir="io", conn=("pmod", 0)), Attrs(IO_TYPE="LVCMOS33"))
    for n in range(7)
])

if __name__ == "__main__":
    top = Top()
    match sys.argv[1]:
        case "build":
            Platform.build(top, do_program=True)
        case "simulate":
            sim = Simulator(top)
            sim.add_clock(1/100_000, domain="sync", if_exists=True)
            sim.add_clock(1/12_000, domain="usb")
            with sim.write_vcd("out.vcd"):
                sim.run_until(1/10, run_passive=True)
        case other:
            main(top, platform=Platform)