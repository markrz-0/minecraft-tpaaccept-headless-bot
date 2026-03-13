
from util.types.varint import pack_to_varint, unpack_from_varint

def pack_to_string(s: str):
    encoded = s.encode('utf-8')
    encoded_len = pack_to_varint(len(encoded))
    return encoded_len + encoded

def unpack_from_string(s: bytes):
    encoded_len, read_bytes = unpack_from_varint(s)

