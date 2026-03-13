import struct
import threading
import time
import os
import queue

from util.protocols import Protocol_1_21, OutgoingPackets_1_21, TRUE
from util.types import pack_to_string, pack_to_varint


class TPAProtocol(Protocol_1_21):
    def __init__(self, server_ip_address: str, server_domain: str, server_port: int):
        super().__init__(server_ip_address, server_domain, server_port)

        self.play_packets_to_send_queue = queue.Queue()
        self.next_tpa_timeout = 0
        self.next_pos_packet = 0
        self.player_pos_and_look_bytes = b''

    def _play_incoming_handle(self):
        while True:
            packet_id, data = self._receive_packet()
            if len(data) > 100:
                print("Received", hex(packet_id), data[:100], '...')
            else:
                print("Received", hex(packet_id), data)

            if self.next_pos_packet != 0 and self.next_pos_packet < time.time():
                self.play_packets_to_send_queue.put(
                    self.prepare_packet(
                        OutgoingPackets_1_21.PLAY_SET_PLAYER_POS,
                        self.player_pos_and_look_bytes + TRUE
                    )
                )
                self.next_pos_packet = time.time() + 1

            if packet_id == 0x40: # Sync player position
                teleport_id = data[33:]
                self.player_pos_and_look_bytes = data[:32]
                self.play_packets_to_send_queue.put(
                    self.prepare_packet(
                        OutgoingPackets_1_21.PLAY_CONFIRM_TELEPORT,
                        teleport_id
                    )
                )
                if self.next_pos_packet == 0:
                    self.next_pos_packet = time.time() + 2
            elif packet_id == 0x39 and self.next_tpa_timeout < time.time(): # chat msg
                print("ADD TP", packet_id)
                self.play_packets_to_send_queue.put(
                    self.prepare_packet(
                        OutgoingPackets_1_21.PLAY_CHAT_COMMAND,
                        pack_to_string('tpaccept')
                    )
                )
                self.next_tpa_timeout = time.time() + 5
            elif packet_id == 0x26: # Keep alive
                self.play_packets_to_send_queue.put(
                    self.prepare_packet(
                        OutgoingPackets_1_21.PLAY_KEEPALIVE,
                        data
                    )
                )
            elif packet_id == 0x3C: # death event
                self.play_packets_to_send_queue.put(
                    self.prepare_packet(
                        OutgoingPackets_1_21.CLIENT_STATUS,
                        pack_to_varint(0) # respawn
                    )
                )
                self.play_packets_to_send_queue.put(
                    self.prepare_packet(
                        OutgoingPackets_1_21.PLAY_CHAT_COMMAND,
                        pack_to_string('home home')
                    )
                )
            elif packet_id == 0x5D: # health event
                health = struct.unpack('f', data[:4])[0]
                print("HEALTH", health)
                if health <= 0.1:
                    self.play_packets_to_send_queue.put(
                        self.prepare_packet(
                            OutgoingPackets_1_21.CLIENT_STATUS,
                            pack_to_varint(0)  # respawn
                        )
                    )
                    self.play_packets_to_send_queue.put(
                        self.prepare_packet(
                            OutgoingPackets_1_21.PLAY_CHAT_COMMAND,
                            pack_to_string('home home')
                        )
                    )


    def _play_outgoing_handle(self):
        while True:
            packet = self.play_packets_to_send_queue.get()

            self._send_packet(packet)

            self.play_packets_to_send_queue.task_done()


    def play(self):
        threading.Thread(target=self._play_incoming_handle).start()
        self._play_outgoing_handle()

if 'IP' not in os.environ.keys():
    print("IP environmental variable is required")
    exit(1)

if 'DOMAIN' not in os.environ.keys():
    os.environ['DOMAIN'] = os.environ['IP']
    print("DOMAIN environmental variable not defined; setting it to IP")

if 'PORT' not in os.environ.keys():
    print("PORT environmental variable is required")
    exit(1)

if 'MCNAME' not in os.environ.keys():
    print("MCNAME environmental variable is required")
    exit(1)



ip_addr = os.environ['IP']
domain = os.environ['DOMAIN']
port = int(os.environ['PORT'])
mcname = os.environ['MCNAME']

protocol = TPAProtocol(ip_addr, domain, port)

print("CONNECT")
protocol.connect()
print("Login")
protocol.login(mcname)
print("Config")
protocol.config()
print("Play")
protocol.play()