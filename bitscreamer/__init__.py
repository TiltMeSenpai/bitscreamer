__version__ = '0.1.0'
from amaranth import *
from amaranth.build import ResourceError

from amaranth.lib.fifo import AsyncFIFO

import itertools

from bitscreamer.sim import make_sim_stream

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


        m = Module()


        if platform: 
            rgb_leds = [res for res in get_all_resources("rgb_led", platform)]
            pins = [platform.request("outport", n) for n in range(7)]
            out_pins = Cat([pin.o for pin in pins])
            out_enable = [pin.oe for pin in pins]

            m.submodules.usb = usb = UsbInterface(platform.request("ulpi"))
            m.submodules.car = ECPIX5DomainGenerator()
            stream = usb.output.stream
        else:
            rgb_leds = []
            pins = []
            out_pins = Signal(8)
            out_enable = Signal(8)
            m.submodules.stream = m_stream = make_sim_stream()
            stream = m_stream.stream

            stream_start = Signal(reset=1)
            with m.If(stream_start | m_stream.done):
                m.d.usb += [
                    m_stream.start.eq(1),
                    m_stream.max_length.eq(255 * 3),
                    stream_start.eq(0)
                ]
            with m.Else():
                m.d.usb += m_stream.start.eq(0)

        m.submodules.rle = rle = RleDecoder(8, 16)

        m.submodules.packetizer = p = Packetizer(
            in_packet = stream.payload,
            valid     = stream.valid,
            ack       = stream.ready
        )

        m.submodules.pwm = pwm = Pwm()

        m.submodules.level_ = l_pwm = Pwm()

        for led in rgb_leds:
            m.d.comb += [
                led.r.eq(pwm.out & stream.valid),
                led.g.eq(pwm.out & rle.running),
                led.b.eq(l_pwm.out),
            ]

        m.submodules.fifo = fifo = AsyncFIFO(width=24, depth=255, w_domain="usb", r_domain="sync")

        w_shift = Signal()
        m.d.usb += [
            w_shift.eq(p.out_valid),
            fifo.w_data.eq(p.out_packet),
            fifo.w_en.eq(p.out_valid & ~w_shift),
            p.out_ack.eq(fifo.w_rdy)
        ]

        m.d.comb += [
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