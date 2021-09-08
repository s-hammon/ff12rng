# see: https://numpy.org/doc/stable/reference/random/bit_generators/mt19937.html # noqa: E501

import array
from collections import deque
from functools import reduce
import logging
import typing


N_MT = 624


class MT19937:
    NUM_NEXT_MTS = 10

    def __init__(self, *, mt: array.array = None, mti: int = None):
        """
        Construct an MT19937 from an existing state given it's mt and index.
        """
        self._mti: int = mti if mti is not None else 0
        self._mts: typing.Deque = deque(
            [mt] if mt is not None else [],
            MT19937.NUM_NEXT_MTS)

    def reset_from_state(self, mt: typing.Iterable[int], mti: int):
        """
        Reset the RNG status, useful if we can't sync.
        """
        assert mt is not None
        assert mti >= 0

        if mti == N_MT:
            logging.warning("resetting a mti of %d to 0", mti)
            mti = 0
        # assert mti < N_MT

        self._mts = deque([mt])
        self._mti = mti

    def next_elements(self, n=20):
        els = []

        for i in range(n):
            mti = (self._mti + i) % N_MT
            mts_ahead = (self._mti + i) // N_MT

            if len(self._mts) < mts_ahead + 1:
                num_mts = mts_ahead - len(self._mts)
                next_mts = self.generate_mts(self._mts[-1], num_mts)
                self._mts = deque([*self._mts, *next_mts])

            mt = self._mts[mts_ahead]
            mt_elem = mt[mti]
            els.append(temper(mt_elem))

        return els

    def next_percentages(self, n=20):
        return [el % 100 for el in self.next_elements(n)]

    def advance_mt(self):
        last_mt = self._mts.popleft()
        self._mti = 0

        if len(self._mts) == 0:
            # generate the next N mts
            mts = self.generate_mts(last_mt, MT19937.NUM_NEXT_MTS)
            self._mts = deque([last_mt, *mts])

    def generate_mts(self, seed_mt, num_mts):
        def reducer(acc, _):
            acc.append(next_mt(acc[-1]))
            return acc

        mts = deque(reduce(
            reducer, range(MT19937.NUM_NEXT_MTS), [seed_mt]))
        mts.popleft()  # remove the used MT
        return mts

    def has_data(self):
        return self._mti is not None\
            and self._mts is not None\
            and len(self._mts) > 0

    def sync(self, current_mt_element: int, current_mti: int) -> bool:
        """
        Try to sync the current state of the RNG to match the observed
        current mt element and mti. If the element is found among the
        computed next mt elements cached, matching the mti (possibly
        wrapping the current mt), then update the RNG to that position
        (mt and mti) and return True. If sync is not possible, return
        False.
        """
        if current_mti < 0 or current_mti >= N_MT:
            logging.warning("Trying to sync a bad mti: %s", current_mti)
            return False

        next_elements = [mt[current_mti] for mt in self._mts]

        try:
            table_index = next_elements.index(current_mt_element)

            # found: pop "table_index" elements out of the deque and set mti
            # we should never empty the deque like this
            for _ in range(table_index):
                self._mts.popleft()
            self._mti = current_mti
            return True

        except ValueError:
            # not found
            logging.warning(
                "Can't find element %d with mti %s, need to reset",
                current_mt_element,
                current_mti)
            return False


def temper(mt_elem: int) -> int:
    """
    Produces the next pseudorandom number from the supplied
    entry in the MT array. This is typically mt[mti].
    """
    y = mt_elem
    y ^= y >> 11
    y ^= (y << 7) & 0x9d2c5680
    y ^= (y << 15) & 0xefc60000
    y ^= y >> 18

    return y


def next_mt(mt: array.array) -> array.array:
    return twist(mt)


def twist(mt: array.array) -> array.array:
    LMASK = 0x7fffffff
    UMASK = 0x80000000
    N = N_MT
    M = 397
    LEN = len(mt)

    assert len(mt) == N

    rv = array.array('I')

    # temporary: U & mt[i], or with next & L
    # assign mt[i] = f(mt, i_mirror), temporary
    for i, val in enumerate(mt):
        or_val = mt[i + 1] & LMASK if i < LEN - 1 else mt[0] & LMASK
        if i < N - M:
            xor_val = mt[i + M]
        elif i < N - 1:
            xor_val = mt[i + (M - N)]
        else:
            # last element
            xor_val = mt[M - 1]

        y = (val & UMASK) | or_val
        mag = 0 if y & 0x1 == 0 else 0x9908b0df
        newval = xor_val ^ (y >> 1) ^ mag
        rv.append(newval)

    assert len(rv) == len(mt)

    return rv


def safe_get_mt_elem(mt, mti):
    if mti < 0 or mti >= N_MT:
        return None

    try:
        return mt[mti]
    except IndexError:
        return None

# private static void Twist(uint[] state)
# {
#     uint y;
#     int kk;
#     for (kk = 0; kk < N - M; kk++)
#     {
#         y = (state[kk] & UPPER_MASK) | (state[kk + 1] & LOWER_MASK);
#         state[kk] = state[kk + M] ^ (y >> 1) ^ mag01[y & 0x1UL];
#     }
#
#     for (; kk < N - 1; kk++)
#     {
#         y = (state[kk] & UPPER_MASK) | (state[kk + 1] & LOWER_MASK);
#         state[kk] = state[kk + (M - N)] ^ (y >> 1) ^ mag01[y & 0x1U];
#     }
#
#     y = (state[N - 1] & UPPER_MASK) | (state[0] & LOWER_MASK);
#     state[N - 1] = state[M - 1] ^ (y >> 1) ^ mag01[y & 0x1U];
# }
