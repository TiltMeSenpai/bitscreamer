import usb.core

dev = usb.core.find(idVendor=0x1337)

for i in range(1000):
    dev.write(1, [
        255, 128, 255,
        255, 128, 0,
        255, 0,   255,
        255, 0,   0])