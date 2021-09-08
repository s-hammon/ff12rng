from importlib import reload
from linuxff12rnghelper import process as p, memory as m, setup_logging
from linuxff12rnghelper import mt19937  # noqa: F401
import linuxff12rnghelper  # noqa: F401

import array
import os
import random
import struct


def r():
    reload(p)
    reload(m)


setup_logging()


print("linuxff12rnghelper REPL")
print("Namespaces:")
print()
print("    p     - linuxff12rnghelper.process")
print("    m     - linuxff12rnghelper.memory")
print("Helper functions:")
print()
print("    r()   - Reloads modules under linuxff12rnghelper namespace")

SG = '\x00\x0a\xf9\xde\xad\xbe\xef\x00\x00'
SGADDR = id(SG)


current_pid = os.getpid()
current_maps = m.memory_maps(current_pid)
current_memfile = open('/proc/{}/mem'.format(current_pid), 'rb')

print("SGADDR:", hex(SGADDR))


def scan_tza(pid):
    MTI_SIGNATURE = "8B 15 ?? ?? ?? ?? 48 63 ?? 48 8D ?? ?? ?? ?? ?? FF C2 89 15 ?? ?? ?? ?? 8B 0C 81 8B C1 C1 E8 0B 33 C8 8B C1 25 ?? ?? ?? ?? C1 E0 07 33 C8 8B C1 25 ?? ?? ?? ?? C1 E0 0F 33 C8 8B C1 C1 E8 12 33 C1 48 83 C4 28"  # noqa: E501

    za_pid = pid
    za_maps = m.memory_maps(za_pid)
    za_memfile = open('/proc/{}/mem'.format(za_pid), 'rb')

    mti_sigaddr = m.find_signature(za_memfile, maps=za_maps,
                                   signature=MTI_SIGNATURE)
    print("Found signature at", hex(mti_sigaddr))
    return mti_sigaddr


def gen_random_mt() -> array.array:
    rnd_bytes = bytearray(random.getrandbits(8) for _ in range(4 * 624))
    rv = array.array('I', struct.unpack('624I', rnd_bytes))
    return rv
