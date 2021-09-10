import functools
from queue import Queue
from threading import Event, Thread
from linuxff12rnghelper import memory, util, message
from linuxff12rnghelper.message import emit_message
from linuxff12rnghelper.mt19937 import N_MT, MT19937

import logging
import struct
import time
from typing import Iterable, NamedTuple, Optional


MTI_SIGNATURE = '8B 15 ?? ?? ?? ?? 48 63 ?? 48 8D ?? ?? ?? ?? ?? FF C2 89 15 ?? ?? ?? ?? 8B 0C 81 8B C1 C1 E8 0B 33 C8 8B C1 25 ?? ?? ?? ?? C1 E0 07 33 C8 8B C1 25 ?? ?? ?? ?? C1 E0 0F 33 C8 8B C1 C1 E8 12 33 C1 48 83 C4 28'  # noqa: E501
MT_SIZE = 624
MT_NUM_BYTES = 625 * 4
MT_UNPACK_STR = '{}I'.format(MT_SIZE)


class Mt19937Addresses(NamedTuple):
    mti_addr: int
    mt_addr: int


class MtData(NamedTuple):
    mt_els: Iterable[int]
    mti: int

    def is_valid(self):
        return len(self.mt_els) > 0 and self.mti >= 0 and self.mti < N_MT


def get_tza_process() -> Optional[util.ProcessInfo]:
    proc = util.find_process('FFXII_TZA')
    logging.debug("FFXII pid: %s", getattr(proc, "pid", "(not found)"))
    return proc


def find_mt_addresses(p: memory.ProcessMemory) -> Optional[Mt19937Addresses]:
    if p is None:
        logging.error('Cant find MTI signature: no process', p)
        return None

    sig_ptr = p.find_signature(MTI_SIGNATURE)
    if sig_ptr is None:
        logging.warning('Cant find MTI signature for process %s', p)
        return None

    # the argument to the instruction the sig starts with is
    # after two instruction bytes
    sig_arg_ptr = sig_ptr + 2

    mov_addr = p.read_u32(sig_arg_ptr)
    mti_addr = sig_arg_ptr + mov_addr + 4

    mt_addr = mti_addr - 4*MT_SIZE

    logging.debug("Scanning for MTI addresses, signature at: %x, "
                  "offset: %x, mti_addr: %x, mt_addr: %x ",
                  sig_ptr, mov_addr, mti_addr, mt_addr)
    return Mt19937Addresses(mti_addr=mti_addr, mt_addr=mt_addr)


def get_mt_and_mti(p: memory.ProcessMemory, mt_addr: int) -> MtData:
    if mt_addr is None:
        _, mt_addr = find_mt_addresses(p)

    mt_bytes = p.read_memory(mt_addr, MT_NUM_BYTES)

    mt_elems = struct.unpack(MT_UNPACK_STR, mt_bytes[:-4])
    mti = struct.unpack('I', mt_bytes[-4:])[0] % N_MT

    return MtData(mt_els=mt_elems, mti=mti)


def memory_worker(bus: Queue, stop_event: Event):
    """
    This thread will periodically probe the FFXII memory to
    monitor the RNG state.
    """
    WORKER_INTERVAL = 100/1000
    NO_PROCESS_INTERVAL = 1000/1000
    emit = functools.partial(emit_message, bus)

    while not stop_event.is_set():
        try:
            pinfo = get_tza_process()
            if pinfo is None:
                emit(message.TYPE_ONLINE_STATUS, False)
                time.sleep(NO_PROCESS_INTERVAL)
                continue

            with memory.ProcessMemory(pinfo.pid) as pmem:
                rng = MT19937()
                mt_addr = None

                while not stop_event.is_set():
                    if mt_addr is None:
                        mt_addrs = find_mt_addresses(pmem)
                        if mt_addrs is None:
                            time.sleep(WORKER_INTERVAL)
                            continue

                    _, mt_addr = mt_addrs

                    mt_data = get_mt_and_mti(pmem, mt_addr)
                    if mt_data.is_valid():
                        emit(message.TYPE_MTI_VALUE, mt_data.mti)
                        rng.reset_from_state(mt_data.mt_els, mt_data.mti)
                        if rng.has_data():
                            emit(message.TYPE_ONLINE_STATUS, True)
                            next_pcs = rng.next_percentages(1000)  # noqa: F841
                            emit(message.TYPE_NEXT_PERCENTAGES, next_pcs)
                        else:
                            emit(message.TYPE_ONLINE_STATUS, False)
                    else:
                        emit(message.TYPE_ONLINE_STATUS, False)

                    time.sleep(WORKER_INTERVAL)

                logging.debug("memory thread: exited loop")
        except Exception as e:
            # todo: more specific catches for conditions that shouldn't
            # make the program end.
            logging.error("Error in memory thread: %s", e)
            emit(message.TYPE_ONLINE_STATUS, False)
