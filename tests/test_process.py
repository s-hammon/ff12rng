from linuxff12rnghelper.util import list_processes


def select_current_process():
    procs = list_processes()
    import os
    curpid = os.getpid()
    matches = [x for x in procs if x.pid == curpid]
    return matches[0]


def test_list_processes():
    processes = list(list_processes())
    assert len(processes) > 0


def test_finds_current_process():
    # if it can't find one with our pid, this will throw
    select_current_process()
