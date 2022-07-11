from amaranth import *

from amaranth.lib.fifo import FIFOInterface, SyncFIFOBuffered

from math import ceil, log

# Run length encoder w/ builtin FIFO
# fifo_depth and max_run will round up to nearest power of 2
class RleEncoder(Elaboratable):
    def __init__(self, sig: Signal, max_run: int, fifo_depth: int):
        self.run_bits = ceil(log(max_run, 2))
        self.sig = sig
        self.fifo = SyncFIFOBuffered(width = sig.shape().width + self.run_bits, depth = fifo_depth)
        self.n_err = self.fifo.w_rdy
        self.adv = Signal()

    def elaborate(self, platform):
        sig = self.sig
        sig_prev = Signal(self.sig.shape())
        ctr = Signal(self.run_bits)
        adv = ctr.all() | (sig ^ sig_prev)

        m = Module()

        m.submodules.fifo = self.fifo

        with m.If(adv):
            m.d.sync += [
                ctr.eq(0),
                self.fifo.w_data.eq(Cat(ctr, sig_prev)),
                self.fifo.w_en.eq(1)
            ]
        with m.Else():
            m.d.sync += [
                ctr.eq(ctr + 1),
                self.fifo.w_en.eq(0)
            ]

        m.d.sync += sig_prev.eq(sig)
        m.d.comb += self.adv.eq(adv)

        return m

class RleDecoder(Elaboratable):
    def __init__(self, width, count_width):
        self.data = Signal(width)
        self.count = Signal(count_width)
        self.ctr   = Signal(count_width)
        self.out = Signal(width)
        self.ready = Signal()
        self.ack = Signal()
        self.running = Signal()

    def elaborate(self, platform):
        ctr = self.ctr

        m = Module()

        with m.If(ctr == 0):
            with m.If(self.ready):
                m.d.sync += [
                    self.out.eq(self.data),
                    self.ctr.eq(self.count),
                    self.ack.eq(1),
                    self.running.eq(1)
                ]
            with m.Else():
                m.d.sync += [
                    self.ack.eq(0),
                    self.running.eq(0)
                ]
        with m.Else():
            m.d.sync += [
                self.ctr.eq(self.ctr - 1),
                self.ack.eq(0),
                self.running.eq(1)
            ]

        return m