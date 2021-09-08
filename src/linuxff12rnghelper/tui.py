import curses
from curses import color_pair
import functools

import logging
import queue
from threading import Event, Thread

from typing import Dict, Iterable, List, Optional, Tuple
from linuxff12rnghelper import ffxii, message


KEY_ESCAPE = -999


class TUIState:
    # the next pc values of the rng (val < 100, for all vals)
    # the current percentage is the first element ([0])
    next_percentages: Iterable[int] = []

    # whether we are reading a FFXII process and we've found the
    # rng structures
    online: bool = False

    # the search query entered by the user, to find patterns
    # examples: 99, 0, 90+ 80+, 9-
    # when using a postfix operator, the limit is included in the
    # range it defines
    query: str = ""

    # a buffer for changing the search pattern that can be confirmed
    # or discarded. The searches are not performed agains this buffer,
    # they are performed against the query variable
    query_buffer: str = ""

    search_matches: Iterable[Iterable[int]] = []

    # the current index into the MT
    mti: int = -1

    # the total count of messages actually processed
    msg_count: int = 0

    # whether to show the message count or not in the ui
    display_count: bool = False

    # whether to show the cursor to change the query
    editing_query: bool = False


class TUI:
    def __init__(self, screen):
        self._screen = screen

        self._height: int = curses.LINES
        self._width: int = curses.COLS
        self._windows = []

        self.state = TUIState()

        self._check_dimensions()
        self._build_layout()

        self._init_colors()

    _color_pairs = {
        'ONLINE': 3,
        'OFFLINE': 2,
        'QUERY_FOUND': 3,
        'QUERY_EDITING': 5,
        'QUERY_NOT_FOUND': 2,
        'ELEMENT_FOUND': 3,
        'NO_QUERY': 4,
    }

    def _build_layout(self):
        # [    SEARCH    ]
        # ----------------
        # [   LIST  OF
        # [  PERCENTAGES ]
        # ----------------
        # [    STATUS    ]

        self._search_window = \
            curses.newwin(5, self._width, 0, 0)
        self._status_window = \
            curses.newwin(5, self._width, self._height - 5, 0)
        self._data_window = \
            curses.newwin(self._height - 10, self._width, 5, 0)

        self._windows = \
            [self._search_window, self._status_window, self._data_window]

        for w in self._windows:
            w.border(0)
            w.noutrefresh()

        curses.doupdate()

    def _resize_layout(self):
        self._search_window.resize(5, self._width)
        self._search_window.mvwin(0, 0)
        self._status_window.resize(5, self._width)
        self._status_window.mvwin(self._height - 5, 0)
        self._data_window.resize(self._height - 10, self._width)
        self._data_window.mvwin(5, 0)

        for w in self._windows:
            w.erase()
            w.border(0)
            w.noutrefresh()

    def _configure_input(self):
        curses.halfdelay(1)

    def _getch(self):
        """
        Wrapper around curses.window.getch.
        It selects a suitable window to getch to (can't blindly
        use stdscr since it takes the whole screen and messes with
        the rest of the windows because of some side effects)

        Also handles the ESC key that can't be reliably detected
        with a single getch call.
        """

        ch = self._data_window.getch()
        if ch == 27:
            self._data_window.nodelay(True)
            ch2 = self._data_window.getch()
            self._data_window.nodelay(False)

            if ch2 == curses.ERR:
                return KEY_ESCAPE
            else:
                # ignore the ALT, put back the other character
                # A-key is not handled in this program
                curses.ungetch(ch2)

        return ch

    def _init_colors(self):
        self._use_color = curses.can_change_color()
        if not self._use_color:
            logging.info("color is not supported in this terminal")
            return

        curses.use_default_colors()

        # can't pass -1 for the fg
        curses.init_pair(self._color_pairs['ONLINE'], curses.COLOR_GREEN, -1)
        curses.init_pair(self._color_pairs['OFFLINE'], curses.COLOR_RED, -1)
        curses.init_pair(self._color_pairs['QUERY_EDITING'],
                         curses.COLOR_YELLOW, -1)
        curses.init_pair(self._color_pairs['QUERY_FOUND'],
                         curses.COLOR_GREEN, -1)
        curses.init_pair(self._color_pairs['QUERY_NOT_FOUND'],
                         curses.COLOR_RED, -1)
        curses.init_pair(self._color_pairs['NO_QUERY'], -1, -1)

    def _check_dimensions(self):
        if self._height < 20 or self._width < 60:
            raise SystemError("need a terminal at least 60x20 big")

    def on_resize(self):
        logging.info("resize detected, old lines/cols: %s %s",
                     curses.LINES, curses.COLS)
        curses.resize_term(*self._screen.getmaxyx())

        self._screen.clear()
        self._screen.noutrefresh()

        logging.info("resize detected, new lines/cols: %s %s, maxyx: %s %s",
                     curses.LINES, curses.COLS, *self._screen.getmaxyx())

        self._height: int = curses.LINES
        self._width: int = curses.COLS

        self._resize_layout()
        self.redraw()

    def redraw(self):
        self._draw_status()
        self._draw_data()
        self._draw_search()

        curses.doupdate()

    def _draw_search(self):
        query = self.state.query
        query_buffer = self.state.query_buffer

        query_pair = self._color_pairs['NO_QUERY']
        if self.state.query:
            query_pair = self._color_pairs['QUERY_FOUND'] \
                         if self.state.search_matches \
                         else self._color_pairs['QUERY_NOT_FOUND']

        if self.state.editing_query:
            search_text = "CURRENT SEARCH: %s" % query_buffer
            query_pair = self._color_pairs['QUERY_EDITING']
            current_query = query_buffer
        else:
            search_text = "CURRENT SEARCH: %s" % query
            current_query = self.state.query

        if not self._use_color:
            query_pair = -1

        search_pos = self._get_centered_pos(self._search_window, search_text)

        self._search_window.erase()
        self._search_window.border(0)

        self._search_window.addstr(*search_pos, "CURRENT SEARCH: ")
        self._search_window.addstr(
            current_query, color_pair(query_pair))

        self._search_window.noutrefresh()

    def _draw_status(self):
        online = "ONLINE" if self.state.online else "OFFLINE"
        online_pair = self._color_pairs.get(online, -1) \
            if self._use_color else -1

        msg_count = self.state.msg_count

        text = online + " "

        self._status_window.erase()
        self._status_window.border(0)

        self._status_window.addstr(
            *self._get_centered_pos(self._status_window, text),
            text,
            color_pair(online_pair) | curses.A_BOLD)

        msg_count_text = "(%d)" % msg_count
        if self.state.display_count:
            self._status_window.addstr(msg_count_text)
        else:
            self._status_window.addstr(" " * len(msg_count_text))

        self._status_window.noutrefresh()

    def _draw_data(self):
        if len(self.state.next_percentages) == 0:
            return

        matches = self.state.search_matches
        positions = set([x for y in matches for x in y])
        position_headers = set([y[0] for y in matches])

        H, W = self._data_window.getmaxyx()

        # available size: remove borders and 1chr padding
        H, W = H - 4, W - 4

        # H elements per column (one row each)
        # columns will have a fixed size and include blank space
        col_width = 12
        num_cols = W // col_width

        max_elements = H * num_cols

        num_percentages = min(len(self.state.next_percentages), max_elements)
        next_percentages = self.state.next_percentages[:num_percentages]

        for i, pc in enumerate(next_percentages):
            if i in position_headers:
                attr = color_pair(self._color_pairs['ELEMENT_FOUND']) \
                       | curses.A_STANDOUT
            elif i in positions:
                attr = color_pair(self._color_pairs['ELEMENT_FOUND'])
            else:
                attr = curses.A_NORMAL

            y = 2 + i % H
            col = i // H
            x = 2 + col * col_width
            self._data_window.addstr(y, x, "%3s: %2s" % (i, pc), attr)

        self._data_window.noutrefresh()

    def _get_centered_pos(self, window, text=""):
        H, W = window.getmaxyx()
        y = H // 2
        x = W // 2 - len(text) // 2
        return (y, x)

    def _get_centered_addstr_args(self, window, text):
        return (*self._get_centered_pos(window, text), text)


def run_in_curses(f):
    try:
        rv = curses.wrapper(f)
    except Exception as e:
        print("Error running curses application:", e)
        raise
    else:
        return rv


class TUIWorker(Thread):
    UI_INTERVAL_MS = 48
    UI_INTERVAL = UI_INTERVAL_MS/1000  # seconds
    BATCH_SIZE = 30

    def __init__(self, bus, stop_event, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._bus: queue.Queue = bus
        self._stop_event: Event = stop_event
        self._emit = functools.partial(message.emit_message, self._bus)
        self._tui: Optional[TUI] = None

        self._query_buffer_allowed_inputs = \
            [*(ord(str(x)) for x in range(0, 10)),
             ord('+'), ord('-'), ord(' ')]

    def _get_message_batch(self, maxsize):
        messages = []
        while len(messages) < maxsize:
            try:
                msg = self._bus.get(block=False)
            except queue.Empty:
                break
            else:
                messages.append(msg)

        return messages

    def _process_messages(self):
        messages = self._get_message_batch(TUIWorker.BATCH_SIZE)

        for msg in messages:
            self._process_message(msg)

        return len(messages)

    def _process_message(self, msg: Dict):
        typ, val = msg["type"], msg["value"]

        assert self._tui is not None

        if typ == message.TYPE_MTI_VALUE:
            self._tui.state.mti = val
        elif typ == message.TYPE_NEXT_PERCENTAGES:
            self._tui.state.next_percentages = list(val)
        elif typ == message.TYPE_ONLINE_STATUS:
            self._tui.state.online = val
        elif typ == message.TYPE_TOGGLE_MESSAGE_COUNT:
            self._tui.state.display_count = not self._tui.state.display_count
        elif typ == message.TYPE_UI_RESIZED:
            self._tui.on_resize()
        elif typ == message.TYPE_BEGIN_UPDATE_QUERY:
            self._begin_query_edit()
        elif typ == message.TYPE_END_UPDATE_QUERY:
            confirm = val == 'CONFIRM'
            self._end_query_edit(confirm=confirm)
        elif typ == message.TYPE_QUERY_CHR:
            self._update_query_buffer(val)
        elif typ == message.TYPE_QUERY_BACKSPACE:
            self._backspace_query_buffer()
        else:
            logging.warning("Unknown message: type=%s, val=%s", typ, val)

        self._tui.state.msg_count += 1

    def _process_input(self):
        # make sure we are not in blocking mode here

        emit = self._emit
        ch = self._tui._getch()

        # handle input when editing the search pattern
        state: Optional[TUIState] = self._tui.state\
            if self._tui is not None else None

        if state and state.editing_query:
            if ch == ord('q') or ch == KEY_ESCAPE:
                emit(message.TYPE_END_UPDATE_QUERY, 'DISCARD')
            elif ch == curses.KEY_ENTER or ch == 10:
                emit(message.TYPE_END_UPDATE_QUERY, 'CONFIRM')
            elif ch in self._query_buffer_allowed_inputs:
                emit(message.TYPE_QUERY_CHR, chr(ch))
            elif ch == 127:
                # backspace
                emit(message.TYPE_QUERY_BACKSPACE, None)
            else:
                pass
            return

        # handle input when not editing anything
        if ch == curses.ERR:
            # no key
            pass
        elif ch == curses.KEY_RESIZE:
            emit(message.TYPE_UI_RESIZED, None)
        elif ch == ord('m'):
            # hide/show message count
            emit(message.TYPE_TOGGLE_MESSAGE_COUNT, None)
        elif ch == ord('q'):
            logging.info("User pressed exit key, exiting.")
            self._stop_event.set()
        elif ch == ord('/') or ch == ord('s'):
            emit(message.TYPE_BEGIN_UPDATE_QUERY, None)

    def _process_search_query(self):
        if not self._tui:
            return

        state = self._tui.state
        query = state.query if state else None
        if not state.query or not query:
            return

        matches = self._scan_pattern()
        state.search_matches = matches

    def _draw(self):
        self._tui.redraw()

    def _begin_query_edit(self):
        assert self._tui

        logging.debug("Entering query update state")

        if self._tui.state.editing_query:
            logging.warning("Entering query update state more than once")

        self._tui.state.editing_query = True
        self._tui.state.query_buffer = self._tui.state.query
        curses.curs_set(1)

    def _end_query_edit(self, confirm: bool):
        assert self._tui

        logging.debug("Exiting query update state")

        if not self._tui.state.editing_query:
            logging.warning("Exiting query update state more than once")

        self._tui.state.editing_query = False
        curses.curs_set(0)

        if confirm:
            new_query = self._tui.state.query_buffer
            logging.info("Setting query to: %s", new_query)
            self._tui.state.query = new_query

        self._tui.state.query_buffer = ""

    def _update_query_buffer(self, ch: str):
        assert self._tui

        if self._can_add_to_query_buffer(ch):
            self._tui.state.query_buffer += ch

    def _backspace_query_buffer(self):
        assert self._tui

        self._tui.state.query_buffer = self._tui.state.query_buffer[:-1]

    def _can_add_to_query_buffer(self, ch: str):
        assert self._tui

        query_buffer = self._tui.state.query_buffer

        last_char = query_buffer[-1] if query_buffer else ""

        numbers = [chr(x) for x in range(ord('0'), ord('9') + 1)]
        modifiers = ['+', '-']

        if last_char:
            # if there's something in the query, what we accept
            # depends on what it is

            # if we're right after a space, only allow numbers
            if last_char == ' ':
                return ch in numbers
            elif last_char in numbers:
                ntl_char = query_buffer[-2] if len(query_buffer) > 1 else ""
                if ntl_char in numbers:
                    # percentages have at most two digits, don't allow a third
                    return ch in [*modifiers, ' ']
                else:
                    return ch in [*numbers, *modifiers, ' ']
            elif last_char in modifiers:
                return ch in ' '
        else:
            # if the query is empty, only numbers are allowed
            return ch in numbers

    def _scan_pattern(self):
        assert self._tui is not None

        return scan_percentages_pattern(
            self._tui.state.query,
            self._tui.state.next_percentages)

    def run(self):
        logging.debug("staring UI thread")

        def loop(screen):
            try:
                curses.start_color()
                curses.curs_set(0)
                curses.use_default_colors()

                self._screen = screen
                self._tui = TUI(screen)

                # in this loop, we are going to be retrieving keypresses and
                # doing work (paint the screen, searching for patterns...)
                # that also updates the scree. Can't use another thread if
                # it uses curses too, therefore keep everything here and
                # don't block.
                self._tui._configure_input()

                self._draw()  # don't wait for the first message
                while not self._stop_event.is_set():
                    self._process_input()
                    processed = self._process_messages()

                    if processed > 0:
                        self._process_search_query()
                        self._draw()

                    curses.napms(TUIWorker.UI_INTERVAL_MS)

                logging.debug("ui thread: exited loop")
            except Exception:
                logging.exception("ui thread: unhandled exception, exiting")
                self._stop_event.set()

        curses.wrapper(loop)

        logging.debug("ui thread: exiting")


def run_tui():
    bus = queue.Queue(100)
    stop_event = Event()

    ui_worker: Thread = TUIWorker(bus, stop_event)
    memory_worker = Thread(
        target=ffxii.memory_worker, args=(bus, stop_event,))

    workers = [ui_worker, memory_worker]

    for w in workers:
        w.start()

    def joinall():
        for w in workers:
            w.join()

    while True:
        try:
            joinall()
        except KeyboardInterrupt:
            stop_event.set()
        else:
            return


def matches_token(token: str, pc: int):
    """
    Whether a percentage value matches a token, which are the elements
    of the search patterns.

    e.g. for the pattern "80+ 95+", the pc value "82" matches the token
    "80+", but would not match the token "95+".
    """
    if not token:
        raise ValueError("need a token")

    or_more = token[-1] == "+"
    or_less = token[-1] == "-"

    val_token = int(token[:-1]) if or_more or or_less else int(token)

    if or_more:
        return pc >= val_token
    elif or_less:
        return pc <= val_token
    else:
        return pc == val_token


def scan_percentages_pattern(pattern: str, pcs: List[int]):
    if not pattern:
        return []

    tokens = pattern.split(' ')
    num_tokens = len(tokens)

    def reducer(acc: List, pc_tup: Tuple[int, int]) -> List[List[int]]:
        pc, pc_index = pc_tup

        tok_index = 0
        last_search = acc[-1] if acc else None

        if last_search and len(last_search) < num_tokens:
            tok_index = len(last_search)
        tok = tokens[tok_index]

        if matches_token(tok, pc):
            if last_search and len(last_search) < num_tokens:
                acc[-1].append(pc_index)
            else:
                acc.append([pc_index])
        else:
            if last_search and len(last_search) < num_tokens:
                # kill the partial, now failed run
                acc = acc[:-1]

                # however, this may also be the start of a new match, so repeat
                if matches_token(tokens[0], pc):
                    acc.append([pc_index])

        return acc

    matches: List[List[int]] = functools.reduce(
        reducer, zip(pcs, range(len(pcs))), [])
    matches = [mseq for mseq in matches if len(mseq) == num_tokens]

    return matches
