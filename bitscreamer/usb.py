from re import A
from xml import dom
from amaranth import *
from luna.usb2 import USBDevice, USBStreamInEndpoint, USBStreamOutEndpoint

from usb_protocol.emitters import DeviceDescriptorCollection
from usb_protocol.types import DescriptorTypes

from math import ceil

MAX_PACKET_SIZE=512

class UsbInterface(Elaboratable):
    def __init__(self, bus):

        self.bus = bus

        self.output = USBStreamOutEndpoint(
            endpoint_number=1,
            max_packet_size=MAX_PACKET_SIZE
        )
        self.input = USBStreamInEndpoint(
            endpoint_number=1,
            max_packet_size=MAX_PACKET_SIZE
        )

    def elaborate(self, platform):
        m = Module()


        m.submodules.usb = usb = USBDevice(bus=self.bus, handle_clocking=True)

        descriptors = DeviceDescriptorCollection()

        with descriptors.DeviceDescriptor() as d:
            d.idVendor  = 0x1337
            d.idProduct = 0x1337

            d.iManufacturer = "bitscreamer test"
            d.iProduct      = "fpga go brrr"
            d.iSerialNumber = "test"

            d.bNumConfigurations = 1

        with descriptors.ConfigurationDescriptor() as c:

            with c.InterfaceDescriptor() as i:
                i.bInterfaceNumber = 0

                with i.EndpointDescriptor() as e:
                    e.bEndpointAddress = 0x01
                    e.wMaxPacketSize   = MAX_PACKET_SIZE

                with i.EndpointDescriptor() as e:
                    e.bEndpointAddress = 0x81
                    e.wMaxPacketSize   = MAX_PACKET_SIZE
        
        usb.add_standard_control_endpoint(descriptors)
        usb.add_endpoint(self.input)
        usb.add_endpoint(self.output)

        print(self.bus.clk)

        m.d.comb += [
            usb.connect.eq(1),
        ]


        return m

class Packetizer(Elaboratable):
    def __init__(self, in_packet: Signal, valid: Signal, ack: Signal, out_packet_width = 24):
        self.in_packet = in_packet
        self.in_valid  = valid
        self.in_ack    = ack

        self.out_packet = Signal(out_packet_width)
        self.out_valid  = Signal()
        self.out_ack    = Signal()

        self.n_bytes = ceil(out_packet_width / 8)
        self.byte_ctr = Signal(range(self.n_bytes), reset=self.n_bytes)
    
    def elaborate(self, platform):
        m = Module()

        ready_latch = Signal()

        m.d.comb += [
            self.out_valid.eq(self.byte_ctr == 0),
            self.in_ack.eq(~self.out_valid & ready_latch)
        ]
        with m.FSM(domain="usb"):
            with m.State("READ"):
                m.d.usb += ready_latch.eq(self.byte_ctr != 0)
                with m.If(self.in_valid & self.in_ack):
                    m.d.usb += [
                        self.out_packet.eq(Cat(self.in_packet, self.out_packet)),
                        self.byte_ctr.eq(self.byte_ctr - 1),
                    ]
                with m.If(self.byte_ctr == 0):
                    m.next = "WRITE"
            with m.State("WRITE"):
                with m.If(self.out_ack):
                    m.next = "READ"
                    m.d.usb += self.byte_ctr.eq(self.byte_ctr.reset)
        
        return m


# Borrowed from upstream Luna
class ECPIX5DomainGenerator(Elaboratable):
    """ Clock generator for ECPIX5 boards. """

    def __init__(self, *, clock_frequencies=None, clock_signal_name=None):
        pass

    def elaborate(self, platform):
        m = Module()

        # Create our domains.
        m.domains.ss     = ClockDomain()
        m.domains.sync   = ClockDomain()
        m.domains.usb    = ClockDomain()
        m.domains.usb_io = ClockDomain()
        m.domains.fast   = ClockDomain()


        # Grab our clock and global reset signals.
        clk100 = platform.request(platform.default_clk)
        reset  = platform.request(platform.default_rst)

        # Generate the clocks we need for running our SerDes.
        feedback = Signal()
        locked   = Signal()
        m.submodules.pll = Instance("EHXPLLL",

                # Clock in.
                i_CLKI=clk100,

                # Generated clock outputs.
                o_CLKOP=feedback,
                o_CLKOS= ClockSignal("sync"),
                o_CLKOS2=ClockSignal("fast"),

                # Status.
                o_LOCK=locked,

                # PLL parameters...
                p_CLKI_DIV=1,
                p_PLLRST_ENA="ENABLED",
                p_INTFB_WAKE="DISABLED",
                p_STDBY_ENABLE="DISABLED",
                p_DPHASE_SOURCE="DISABLED",
                p_CLKOS3_FPHASE=0,
                p_CLKOS3_CPHASE=0,
                p_CLKOS2_FPHASE=0,
                p_CLKOS2_CPHASE=5,
                p_CLKOS_FPHASE=0,
                p_CLKOS_CPHASE=5,
                p_CLKOP_FPHASE=0,
                p_CLKOP_CPHASE=4,
                p_PLL_LOCK_MODE=0,
                p_CLKOS_TRIM_DELAY="0",
                p_CLKOS_TRIM_POL="FALLING",
                p_CLKOP_TRIM_DELAY="0",
                p_CLKOP_TRIM_POL="FALLING",
                p_OUTDIVIDER_MUXD="DIVD",
                p_CLKOS3_ENABLE="DISABLED",
                p_OUTDIVIDER_MUXC="DIVC",
                p_CLKOS2_ENABLE="ENABLED",
                p_OUTDIVIDER_MUXB="DIVB",
                p_CLKOS_ENABLE="ENABLED",
                p_OUTDIVIDER_MUXA="DIVA",
                p_CLKOP_ENABLE="ENABLED",
                p_CLKOS3_DIV=1,
                p_CLKOS2_DIV=2,
                p_CLKOS_DIV=4,
                p_CLKOP_DIV=5,
                p_CLKFB_DIV=1,
                p_FEEDBK_PATH="CLKOP",

                # Internal feedback.
                i_CLKFB=feedback,

                # Control signals.
                i_RST=reset,
                i_PHASESEL0=0,
                i_PHASESEL1=0,
                i_PHASEDIR=1,
                i_PHASESTEP=1,
                i_PHASELOADREG=1,
                i_STDBY=0,
                i_PLLWAKESYNC=0,

                # Output Enables.
                i_ENCLKOP=0,
                i_ENCLKOS=0,
                i_ENCLKOS2=0,
                i_ENCLKOS3=0,

                # Synthesis attributes.
                a_ICP_CURRENT="12",
                a_LPF_RESISTOR="8"
        )

        # Temporary: USB FS PLL
        feedback    = Signal()
        usb2_locked = Signal()
        m.submodules.fs_pll = Instance("EHXPLLL",

                # Status.
                o_LOCK=usb2_locked,

                # PLL parameters...
                p_PLLRST_ENA="ENABLED",
                p_INTFB_WAKE="DISABLED",
                p_STDBY_ENABLE="DISABLED",
                p_DPHASE_SOURCE="DISABLED",
                p_OUTDIVIDER_MUXA="DIVA",
                p_OUTDIVIDER_MUXB="DIVB",
                p_OUTDIVIDER_MUXC="DIVC",
                p_OUTDIVIDER_MUXD="DIVD",

                p_CLKI_DIV = 20,
                p_CLKOP_ENABLE = "ENABLED",
                p_CLKOP_DIV = 16,
                p_CLKOP_CPHASE = 15,
                p_CLKOP_FPHASE = 0,

                p_CLKOS_DIV = 12,
                p_CLKOS_CPHASE = 0,
                p_CLKOS_FPHASE = 0,


                p_CLKOS2_ENABLE = "ENABLED",
                p_CLKOS2_DIV = 10,
                p_CLKOS2_CPHASE = 0,
                p_CLKOS2_FPHASE = 0,

                p_CLKOS3_ENABLE = "ENABLED",
                p_CLKOS3_DIV = 40,
                p_CLKOS3_CPHASE = 5,
                p_CLKOS3_FPHASE = 0,

                p_FEEDBK_PATH = "CLKOP",
                p_CLKFB_DIV = 6,

                # Clock in.
                i_CLKI=clk100,

                # Internal feedback.
                i_CLKFB=feedback,

                # Control signals.
                i_RST=reset,
                i_PHASESEL0=0,
                i_PHASESEL1=0,
                i_PHASEDIR=1,
                i_PHASESTEP=1,
                i_PHASELOADREG=1,
                i_STDBY=0,
                i_PLLWAKESYNC=0,

                # Output Enables.
                i_ENCLKOP=0,
                i_ENCLKOS2=0,

                # Generated clock outputs.
                o_CLKOP=feedback,
                o_CLKOS2=ClockSignal("usb_io"),
                # o_CLKOS3=ClockSignal("usb"),
                # This should be driven from the ULPI pny

                # Synthesis attributes.
                a_FREQUENCY_PIN_CLKI="25",
                a_FREQUENCY_PIN_CLKOP="48",
                a_FREQUENCY_PIN_CLKOS="48",
                a_FREQUENCY_PIN_CLKOS2="12",
                a_ICP_CURRENT="12",
                a_LPF_RESISTOR="8",
                a_MFG_ENABLE_FILTEROPAMP="1",
                a_MFG_GMCREF_SEL="2"
        )

        # Control our resets.
        m.d.comb += [
            ClockSignal("ss")      .eq(ClockSignal("sync")),

            ResetSignal("ss")      .eq(~locked),
            ResetSignal("sync")    .eq(~locked),
            ResetSignal("fast")    .eq(~locked),

            ResetSignal("usb")     .eq(~usb2_locked),
            ResetSignal("usb_io")  .eq(~usb2_locked),
        ]

        return m