from pathlib import Path
from typing import Generator, NamedTuple, Optional


class ProcessInfo(NamedTuple):
    pid: int
    name: str


def find_process(name: str) -> Optional[ProcessInfo]:
    """
    Find the first process that matches "name".
    """
    return next(list_processes(name), None)


def list_processes(name: str = "") -> Generator[ProcessInfo, None, None]:
    # look into all pids in procfs and return the pid
    # and name for those that contain "name" in their name
    procpath = Path('/proc')

    def is_pidpath(path: Path):
        return path.is_dir() and path.name.isnumeric()

    for pidpath in procpath.iterdir():
        if not is_pidpath(pidpath):
            continue

        pid = int(pidpath.name)
        status_path = pidpath.joinpath('status')

        try:
            process_name = ""
            with open(status_path, 'r') as f:
                for line in f:
                    if line.startswith('Name:'):
                        process_name = line[6:].rstrip('\n')
            if name in process_name:
                yield ProcessInfo(pid, process_name)
        except FileNotFoundError:
            # process has vanished, don't include it
            continue
