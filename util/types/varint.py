def pack_to_varint(number: int):
    CONTINUE_BYTE = (1 << 7)
    byte_arr = b''
    while number >= 128:
        byte_arr += int.to_bytes(number % 128 | CONTINUE_BYTE, 1, 'little')
        number >>= 7
    byte_arr += int.to_bytes(number, 1, 'little')
    return byte_arr

def unpack_from_varint(buffer: bytes):
    """
    :param buffer: bytes
    :return: (decodec_number, number_of_bytes_read)
    """
    CONTINUE_BYTE = (1<<7)

    decoded_number = 0
    offset = 0
    read_bytes = 0
    for b in buffer:
        read_bytes += 1
        if b & CONTINUE_BYTE > 0:
            to_add = b - 128
            decoded_number += (to_add << offset)
            offset += 7
        else:
            decoded_number += (b << offset)
            break
    else:
        # executed only if no "break"
        return None
    return decoded_number, read_bytes
