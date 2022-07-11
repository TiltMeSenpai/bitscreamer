import usb.core

dev = usb.core.find(idVendor=0x1337)

nbytes = dev.write(1, "hello")
print("".join([chr(c) for c in dev.read(0x81, 512)]))