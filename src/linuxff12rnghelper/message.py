from queue import Queue


TYPE_ONLINE_STATUS = 'STATUS'  # values: ONLINE, OFFLINE
TYPE_NEXT_PERCENTAGES = 'NEXT_PERCENTAGES'  # value=list of percentages
TYPE_MTI_VALUE = 'MTI'  # value=mti
TYPE_UI_RESIZED = 'RESIZE'  # no value
TYPE_TOGGLE_MESSAGE_COUNT = 'TOGGLE_MESSAGE_COUNT'  # no value
TYPE_BEGIN_UPDATE_QUERY = 'BEGIN_UPDATE_QUERY'  # no value
TYPE_END_UPDATE_QUERY = 'END_UPDATE_QUERY'  # values: DISCARD, CONFIRM
TYPE_QUERY_CHR = 'UPDATE_QUERY_CHR'  # value: the (valid) key pressed
TYPE_QUERY_BACKSPACE = 'UPDATE_QUERY_BACKSPACE'  # no value
TYPE_QUERY_DEL = 'UPDATE_QUERY_DEL'  # no value


def emit_message(bus: Queue, typ: str, value):
    bus.put({"type": typ, "value": value})
