from nmigen import *

class SimStream(Elaboratable):
    def __init__(self):
        self.payload = Signal(8)
        self.valid = Signal()
        self.first = Signal()
        self.ready = Signal()
    def elaborate(self, platform):
        m = Module()
        ready = Signal()
        m.d.sync += [
            ready.eq(self.ready),
            self.valid.eq(ready)
        ]

        with m.If(self.ready):
            m.d.sync += self.payload.eq(self.payload + 1),


        return m