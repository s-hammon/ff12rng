from linuxff12rnghelper import memory
import os


curpid = os.getpid()


def try_find_signature(pid: int, pattern: str):
    maps = memory.memory_maps(pid)
    with memory.ProcessMemory(pid) as pm:
        pos = memory.find_signature(
            pm.mem,
            maps=maps,
            signature=pattern)
        return pos


def test_finds_signature_in_process():
    SIG = '\x93\xba\x00\xfb\x90\x90'  # noqa: F841
    PAT = "93 BA ?? FB ?? 90"
    try_find_signature(curpid, PAT)


def test_finds_signature_no_wildcards():
    SIG = '\xb3\xa0\xb3\xa0\xb3\xa0\xb3'  # noqa: F841
    PAT = 'B3 A0 B3 A0 B3 A0 B3'
    try_find_signature(curpid, PAT)


def test_finds_signature_wildcard_end():
    SIG = '\xb3\xa0\xb3\xca\xfc\x97'  # noqa: F841
    PAT = 'B3 A0 B3 CA FC ??'
    assert try_find_signature(curpid, PAT) > 0


def test_finds_signature_2wildcard_end():
    SIG = '\xfa\x76\xbc\xfd\x99\x01'  # noqa: F841
    PAT = 'FA 76 BC FD ?? ??'
    assert try_find_signature(curpid, PAT) > 0


def test_cant_find_memory():
    PAT = '00 00 D3 AD BE EF 99 59 00'
    assert try_find_signature(curpid, PAT) is None
