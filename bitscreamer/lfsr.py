from amaranth import *

# Linear feedback shift register
class Lfsr(Elaboratable):
    def __init__(self, reset=0xACE1):
        self.out = Signal(16, reset=reset)
        self.bit = self.out[15] ^ self.out[13] ^ self.out[12] ^ self.out[10]

    def elaborate(self, platform):
        m = Module()
        ctr = Signal(8)
        with m.If(ctr == 0):
            m.d.sync += [
                self.out.eq(Cat(self.out, self.bit) >> 1),
                ctr.eq(self.out)
            ]
        with m.Else():
            m.d.sync += ctr.eq(ctr - 1)

        return m