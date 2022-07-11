__version__ = '0.1.0'
from amaranth import *
from amaranth.build import ResourceError

from amaranth.lib.fifo import AsyncFIFO

import itertools

from bitscreamer.sim import SimStream

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

        out_pins = Cat([pin.o for pin in pins])

        out_enable = [pin.oe for pin in pins]

        m = Module()

        m.submodules.rle = rle = RleDecoder(8, 16)

        m.submodules.packetizer = p = Packetizer()

        # m.domains.usb = ClockDomain()

        # m.d.comb += ClockSignal("usb").eq(ClockSignal("sync"))

        m.submodules.car = ECPIX5DomainGenerator()

        m.submodules.usb = usb = UsbInterface(platform.request("ulpi"))

        m.submodules.pwm = pwm = Pwm()

        m.submodules.level_ = l_pwm = Pwm()

        # m.submodules.stream = stream = SimStream()

        stream = usb.output.stream

        for led in rgb_leds:
            m.d.comb += [
                led.r.eq(pwm.out & stream.valid),
                led.g.eq(pwm.out & rle.running),
                led.b.eq(l_pwm.out),
            ]

        m.submodules.fifo = fifo = AsyncFIFO(width=24, depth=255, w_domain="usb", r_domain="sync")

        m.d.usb += [
            usb.input.stream.payload.eq(rle.ctr),
            usb.input.stream.valid.eq(1),
            usb.input.stream.first.eq(1),
            usb.input.stream.last.eq(1),

            # Pass USB packets to packetizer
            p.in_packet.eq(stream.payload),
            p.in_valid.eq(stream.valid),
            # p.rst.eq(stream.first),
            stream.ready.eq(~p.rdy),

            fifo.w_data.eq(p.out),
            fifo.w_en.eq(p.rdy),
            p.ack.eq(fifo.w_rdy)
        ]

        m.d.sync += [
            Cat(rle.count, rle.data).eq(fifo.r_data),
            fifo.r_en.eq(rle.ack),
            rle.ready.eq(fifo.r_rdy),
            l_pwm.level.eq(fifo.r_level),
            out_pins.eq(rle.out)
        ]

        for pin in out_enable:
            m.d.comb += pin.eq(rle.running)

        m.d.comb += pwm.level.eq(64)

        return m