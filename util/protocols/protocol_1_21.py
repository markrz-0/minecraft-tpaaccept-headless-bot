import zlib
import socket
from uuid import uuid3
from util.types import *

TRUE = b'\x01'
FALSE = b'\x00'


class NULL_NAMESPACE:
    bytes = b''

class HandshakeNextState:
    STATUS = 1 # Ping
    LOGIN = 2
    TRANSFER = 3


class OutgoingPackets_1_21:
    HANDSHAKE = 0x00

    LOGIN_START = 0x00
    LOGIN_ACK = 0x03

    CONFIG_CLIENT_INFO = 0x00
    CONFIG_PLUGIN_MESSAGE = 0x02
    CONFIG_FINISH_ACK = 0x03
    CONFIG_KNOW_PACKS = 0x07

    PLAY_CONFIRM_TELEPORT = 0x00
    PLAY_CHAT_COMMAND = 0x04
    CLIENT_STATUS= 0x09
    PLAY_KEEPALIVE = 0x18
    PLAY_SET_PLAYER_POS = 0x1B

class IncomingPacketChecker:
    def __init__(self, name, packet_id: int, optional: bool):
        self.name = name
        self.packet_id =packet_id
        self.optional = optional

    def is_same_type(self, packet_id: int, data: bytes):
        if packet_id == self.packet_id:
            print('Recieved', self.name)
            return True
        elif self.optional:
            print(f"WARN: Didnt receive optional packet {self.name}")
            return False
        else:
            raise RuntimeError(f"Expected to receive {self.name} packet with id {self.packet_id}. Instead received packet ID {packet_id} with data\n{data}")

class ServerState:
    NONE = -1
    HANDSHAKE = 0
    LOGIN = 1
    CONFIG = 2
    PLAY = 3


class Protocol_1_21:
    def __init__(self, server_ip_address: str, server_domain: str, server_port: int):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.compression = False
        self.compression_threshold = 0
        self.server_ip_address = server_ip_address
        self.server_port = server_port
        self.server_domain = server_domain
        self.protocol_version = 767 # 1.21
        self.buff = b''

        self.state = ServerState.NONE

    def prepare_packet(self, packet_id, data):
        packet_id_varint = pack_to_varint(packet_id)
        content = packet_id_varint + data
        content_length = pack_to_varint(len(content))
        if self.compression:
            if len(content) >= self.compression_threshold:
                data = content_length + zlib.compress(content)
            else:
                data = b'\x00' + content

            packet_length = pack_to_varint(len(data))

            return packet_length + data

        else:
            return content_length + content

    def _parse_incoming_packet(self):
        buff_copy = self.buff
        to_cut = 0


        value = unpack_from_varint(buff_copy)
        if value is None:
            return

        content_length, read_bytes = value
        if content_length + read_bytes > len(self.buff):
            return

        print("PACKET!")

        to_cut += read_bytes
        buff_copy = buff_copy[read_bytes:]

        if not self.compression:
            value = unpack_from_varint(buff_copy)
            if value is None:
                return

            packet_id, read_bytes = value

            to_cut += read_bytes
            buff_copy = buff_copy[read_bytes:]

            data = buff_copy[:(content_length-read_bytes)]
            to_cut += len(data)

            self.buff = self.buff[to_cut:]

            return packet_id, data
        else:
            value = unpack_from_varint(buff_copy)
            if value is None:
                return

            data_length, read_bytes = value

            buff_copy = buff_copy[read_bytes:]
            to_cut += read_bytes

            content_length -= read_bytes

            compressed_buff = buff_copy[:content_length]

            to_cut += content_length
            self.buff = self.buff[to_cut:]

            if data_length != 0:
                compressed_buff = zlib.decompress(compressed_buff)

            value = unpack_from_varint(compressed_buff)
            if value is None:
                return

            packet_id, read_bytes = value

            data = compressed_buff[read_bytes:]

            return packet_id, data

    def _receive_packet(self):
        value = self._parse_incoming_packet()
        while value is None:
            self.buff += self.socket.recv(64)
            value = self._parse_incoming_packet()
        return value

    def _send_packet(self, data):
        print("SEND", data)
        remaining_bytes = len(data)
        actually_sent = self.socket.send(data)
        remaining_bytes -= actually_sent
        while remaining_bytes > 0:
            data = data[actually_sent:]
            actually_sent = self.socket.send(data)
            remaining_bytes -= actually_sent

    def connect(self):
        self.socket.connect((self.server_ip_address, self.server_port))

    def login(self, name: str):
        """
        Offline login
        :param name:
        :return:
        """

        self.state = ServerState.HANDSHAKE

        protocol_version_varint = pack_to_varint(self.protocol_version)
        server_address_bytes = pack_to_string(self.server_domain)
        server_port_u16 = int.to_bytes(self.server_port, length=2, byteorder='big', signed=False)
        next_state_varint = pack_to_varint(HandshakeNextState.LOGIN)
        data = protocol_version_varint + server_address_bytes + server_port_u16 + next_state_varint

        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.HANDSHAKE,
                data
            )
        )

        self.state = ServerState.LOGIN

        name_uuid = uuid3(NULL_NAMESPACE, f'OfflinePlayer:{name}')

        name_encoded = pack_to_string(name)
        uuid = name_uuid.bytes
        data = name_encoded + uuid
        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.LOGIN_START,
                data
            )
        )

        packet_id, data = self._receive_packet()
        if packet_id == 0x03: # Set Compression
            self.compression = True
            self.compression_threshold = unpack_from_varint(data)[0]
            print("Recieved set_compression")
        elif packet_id == 0x01: # Encryption Request
            raise RuntimeError("Server sent Encryption Request - Not Implemented yet")
        else:
            raise RuntimeError(f"Unexpected packet! Received packet id: {packet_id}. Data {data}")

        (IncomingPacketChecker('login_success', 0x02, False)
         .is_same_type(*self._receive_packet()))

        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.LOGIN_ACK,
                b''
            )
        )

        self.state = ServerState.CONFIG

    def config(self):
        locale_encoded = pack_to_string('en_us')
        view_distance_i8 = int.to_bytes(12, length=1, byteorder='big')
        chat_mode = pack_to_varint(0) # enabled
        chat_colors = TRUE
        display_skin_u8 = b'\x3f' # 0011 1111
        main_hand = pack_to_varint(1) # right
        enable_text_filtering = FALSE
        allow_server_listing = FALSE

        data = locale_encoded + view_distance_i8 + chat_mode + chat_colors + display_skin_u8 + main_hand + enable_text_filtering + allow_server_listing
        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.CONFIG_CLIENT_INFO,
                data
            )
        )

        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.CONFIG_PLUGIN_MESSAGE,
                b'\x0fminecraft:brand\x07vanilla'
            )
        )



        current_packet_index = 0
        next_packets_order = [
            IncomingPacketChecker('plugin_info', 0x01, True),
            IncomingPacketChecker('feature_flags', 0x0C, True),
            IncomingPacketChecker('known_packs', 0x0E, False)
        ]

        packet_id, data = self._receive_packet()
        while True:
            while not next_packets_order[current_packet_index].is_same_type(packet_id, data):
                current_packet_index += 1
                if len(next_packets_order) == current_packet_index:
                    packet_id, data = None, None
                    break

            current_packet_index += 1

            if len(next_packets_order) == current_packet_index:
                break

            packet_id, data = self._receive_packet()

        number_of_known_packs = pack_to_varint(1)
        namespace = pack_to_string('minecraft')
        namespace_id = pack_to_string('core')
        version = pack_to_string('1.21')

        data = number_of_known_packs + namespace + namespace_id + version

        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.CONFIG_KNOW_PACKS,
                data
            )
        )

        registry_data = IncomingPacketChecker('registry_data', 0x07, True)
        packet_id, data = self._receive_packet()
        while registry_data.is_same_type(packet_id, data):
            packet_id, data = self._receive_packet()

        update_tags_recieved = (IncomingPacketChecker('update_tags', 0x0D, True)
                                .is_same_type(packet_id, data))

        if update_tags_recieved:
            packet_id, data = self._receive_packet()

        IncomingPacketChecker('finish_configuration', 0x03, False).is_same_type(packet_id, data)

        self._send_packet(
            self.prepare_packet(
                OutgoingPackets_1_21.CONFIG_FINISH_ACK,
                b''
            )
        )

        self.state = ServerState.PLAY














