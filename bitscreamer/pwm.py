from amaranth import *

# Simple 8 bit PWM controller
class Pwm(Elaboratable):
    def __init__(self):
        self.out = Signal()
        self.level = Signal(8)

    def elaborate(self, platform):
        ctr = Signal(8)
        m = Module()

        m.d.sync += [
            ctr.eq(ctr - 1),
            self.out.eq(self.level > ctr)
        ]

        return m