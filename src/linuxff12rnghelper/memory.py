import copy
import logging
import struct
from typing import Iterable, BinaryIO, NamedTuple, Optional


# has to be up here so the later typing annotation works ^_^
class MemoryMapRegion(NamedTuple):
    start: int
    end: int
    perms: bytes

    def __str__(self):
        return "{:x}-{:x} perms: {}".format(self.start, self.end, self.perms)


class ProcessMemory:
    """
    This class wraps the resources needed to read a process memory and
    handles initalization and cleanup, and can be used as a context manager.
    """
    def __init__(self, pid: int):
        self.pid: int = pid
        self._maps: Iterable[MemoryMapRegion] = []

    def __enter__(self):
        self.mem: BinaryIO = open_memory(self.pid)
        return self

    def __exit__(self, type, val, tb):
        close_memory(self.mem)

    def maps(self) -> Iterable[MemoryMapRegion]:
        if not self._maps:
            self._maps = memory_maps(self.pid)
        return copy.copy(self._maps)

    def find_signature(self, signature: str) -> Optional[int]:
        return find_signature(self.mem,
                              maps=self.maps(),
                              signature=signature)

    def read_memory(self, addr: int, count: int) -> bytes:
        return read_memory(self.mem, addr, count)

    def read_u32(self, address) -> int:
        bs = read_memory(self.mem, address, 4)
        ptr = struct.unpack('I', bs)[0]
        return ptr

    def __str__(self):
        return "[ProcessMemory pid=%s]" % self.pid


def memory_maps(pid: int) -> Iterable[MemoryMapRegion]:
    """
        Return the memory maps of a process (by PID)
    """

    maps = []

    # if we can't access the process' memory, this will
    # raise a PermissionError
    with open('/proc/{}/maps'.format(pid), 'rb') as f:
        for line in f:
            range, perms, *_ = line.split()
            start, end = [int(addr, 16) for addr in range.decode().split('-')]
            region = MemoryMapRegion(start, end, perms)
            maps.append(region)

    return maps


def open_memory(pid: int) -> BinaryIO:
    memfile = '/proc/{}/mem'.format(pid)
    logging.debug("Opening memory file at %s", memfile)

    return open(memfile, 'rb')


def close_memory(mem: BinaryIO):
    logging.debug("Closing memory file: %s", mem.name)
    mem.close()


def read_memory(memfile: BinaryIO, addr: int, count: int) -> bytes:
    memfile.seek(addr)
    rv = memfile.read(count)
    return rv


def find_signature(memfile: BinaryIO,
                   *_,
                   maps: Iterable[MemoryMapRegion],
                   signature: str,
                   start: Optional[int] = None) -> Optional[int]:
    """
    Try to find a memory signature in the mappped memory of a process.
    The signature is in PEID format, allowing holes in which any value is
    valid (but represent exactly one byte). Example:
        5A ?? 90 9E

    Return the address where the signature is found, or None if it
    is not found.
    """

    def byte_conv(item):
        return None if item == '??' else int(item, 16)

    sigbytes = [byte_conv(b.strip()) for b in signature.split()]

    sigpos = 0  # the current signature element being tested
    addr = 0  # the address being tested

    # Read memory in "chunks", of at most a fixed tractable size,
    # and do the searching on that chunk. The two first values are
    # the [start, end) adresses of the chunk.
    chunk = (-1, -1, b'')

    # Iterate over the memory maps, and in each mapped region try to find
    # the signature. The signature may span several regions if they are
    # contiguous.
    for _map in filter(lambda m: b'r' in m.perms, maps):
        if sigpos > 0 and sigpos < len(sigbytes) and addr == _map.start:
            # contiguous map, no need to reset the search
            logging.debug("Search bridging across memory section: %x", addr)
            pass
        else:
            sigpos = 0

        addr = _map.start

        if start is not None and _map.end < start:
            continue
        elif start is not None and start > _map.start:
            addr = start

        memfile.seek(_map.start)

        try:
            while sigpos < len(signature) and addr < _map.end:
                # read memory in chunks, instead of one per comparison
                cstart, cend, cbytes = chunk
                if addr >= cend or addr < cstart:
                    csize = min(0x10000, _map.end - addr)
                    memfile.seek(addr)
                    cstart = addr
                    cend = addr + csize
                    cbytes = memfile.read(csize)
                    chunk = (addr, addr + csize, cbytes)

                chunk_offset = addr - cstart
                val = cbytes[chunk_offset]

                sigelem = sigbytes[sigpos]
                if sigelem is not None and val != sigelem:
                    sigpos = 0
                else:
                    sigpos += 1

                addr += 1

                if sigpos == len(sigbytes):
                    # found signature
                    return addr - len(sigbytes)
        except OSError:
            # may happen on some memory regions even with +r perm
            # keep searching in the next mapped regions
            sigpos = 0
            logging.info("Can't read memory at %x in section %s",
                         addr, _map, exc_info=False)

    abbr_sig = signature[:16] \
        if len(signature) <= 16 else "{}...".format(signature[:14])

    logging.info("Signature %s not found", abbr_sig)
    return None
