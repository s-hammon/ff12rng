import click

try:
    import curses
except ImportError:
    print("Warning: curses not supported, UI will not work.")

import logging
import time

from linuxff12rnghelper import (
    ffxii,
    memory,
    mt19937,
    setup_logging,
    tui)


@click.group()
def cli():
    pass


@cli.command(name='testinfo')
@click.option('--mt', default=None, type=str, help='MT address (hex)')
@click.option('--mti', default=None, type=str, help='MTI address (hex)')
def cli_testinfo(pid: int, addr_mt, addr_mti):
    proc = ffxii.get_tza_process()

    if proc is None:
        print("Couldn't find a process, exiting.")
        return

    with memory.ProcessMemory(proc.pid) as pmem:
        if addr_mt is not None and addr_mti is not None:
            addr_mt = int(addr_mt, base=16)
            addr_mti = int(addr_mti, base=16)
        else:
            addrs = ffxii.find_mt_addresses(pmem)
            if addrs is None:
                print("Can't find addresses")
                return

            addr_mt, addr_mti = addrs

        mt, mti = ffxii.get_mt_and_mti(pmem, addr_mt)

        print("MT address: 0x%x" % addr_mt)
        print("MTI address: 0x%x" % addr_mti)
        print("MTI value: ", mti)


@cli.command(name='ui')
def ui():
    tui.run_tui()


@cli.command(name='random')
def cli_random():
    pass


def run():
    setup_logging()
    cli()


# ------------------------- TUMBA ----------------------
@cli.command(name='watchpc')
@click.option('--rows', default=20, type=int, help='How many rows to display')
def watch_percentages(rows: int):
    from curses import wrapper

    proc = ffxii.get_tza_process()
    if proc is None:
        print("No FF12 process found, exiting.")
        return

    scr = curses.initscr()

    def watch_percentages_internal(screen):
        screen.clear()
        with memory.ProcessMemory(proc.pid) as pmem:
            addrs = ffxii.find_mt_addresses(pmem)

            if not addrs:
                print("Can't find MT19937 addresses, exiting")
                return

            _, addr_mt = addrs
            mt, mti = ffxii.get_mt_and_mti(pmem, addr_mt)
            rng = mt19937.MT19937(mt=mt, mti=mti)

            i = 0
            while True:
                # sync the RNG
                mt, mti = ffxii.get_mt_and_mti(pmem, addr_mt)
                mt_elem = mt19937.safe_get_mt_elem(mt, mti)
                if mt_elem is None or not rng.sync(mt[mti], mti):
                    logging.info("bad loop, mt_elem: %s", mt_elem)
                    rng.reset_from_state(mt, mti)

                # get the next N numbers and display them
                next_pcs = rng.next_percentages()
                screen.addstr(2, 2, "Next %d percentages:" % len(next_pcs))
                for i in range(len(next_pcs)):
                    pc = next_pcs[i]
                    s = "%-4s: %d   " % (i, next_pcs[i]) \
                        if pc > 5 else "%-4s: %d * " % (i, next_pcs[i])
                    scr.addstr(i + 4, 2, s)

                i += 1
                screen.refresh()

                time.sleep(0.1)

    wrapper(watch_percentages_internal)


if __name__ == '__main__':
    run()
