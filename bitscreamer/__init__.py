__version__ = '0.1.0'
from amaranth import *
from amaranth.build import ResourceError

import itertools

from .rle import RleEncoder, RleDecoder
from .lfsr import Lfsr
from .usb import Packetizer, UsbInterface, ECPIX5DomainGenerator
from .pwm import Pwm

def get_all_resources(name, platform):
    resources = []
    for number in itertools.count():
        try:
            resources.append(platform.request(name, number))
        except ResourceError:
            break
    return resources

class Top(Elaboratable):
    def elaborate(self, platform):
        rgb_leds = [res for res in get_all_resources("rgb_led", platform)]

        pins = [platform.request("outport", n) for n in range(7)]

        out_pins = [pin.o for pin in pins]

        out_enable = [pin.oe for pin in pins]

        m = Module()

        m.submodules.out = out = RleDecoder(8, 16)

        m.submodules.packetizer = p = Packetizer()

        # m.submodules.car = ECPIX5DomainGenerator()

        # m.submodules.usb = usb = UsbInterface(platform.request("ulpi"))

        m.submodules.lfsr = lfsr = Lfsr()

        m.submodules.pwm = pwm = Pwm()

        for led in rgb_leds:
            m.d.comb += [
                led.r.eq(pwm.out),
                led.g.eq(0),
                led.b.eq(0),
            ]

        lfsr_latch = Signal(8)

        adv = lfsr_latch != lfsr.out[:8]

        m.d.sync += [
            lfsr_latch.eq(lfsr.out[:8]),
            p.in_packet.eq(lfsr_latch),
            p.in_valid.eq(adv),
            p.ack.eq(1)
        ]


        # for pin in out_enable:
        #     m.d.comb += pin.eq(out.running)

        # for (pin, drive) in zip(out_enable, out.out):
        #     m.d.comb += pin.eq(drive)

        # m.d.comb += pwm.level.eq(127)

        return m