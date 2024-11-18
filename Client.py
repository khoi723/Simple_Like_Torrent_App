# client.py

import socket
import threading
import urllib.parse as urlparse
import requests
import json
import hashlib
import os

TRACKER_URL = 'http://localhost:8000'
PEER_PORT = 5000  # Port for incoming peer connections
FILE_NAME = 'sample_file.txt'
INFO_HASH = hashlib.sha1(FILE_NAME.encode()).hexdigest()
PEER_ID = hashlib.md5(str(os.getpid()).encode()).hexdigest()

# Keep track of file pieces (for simplicity, we'll assume the file is split into 4 pieces)
total_pieces = 4
have_pieces = [0] * total_pieces  # 0: don't have, 1: have

def announce_to_tracker(event):
    params = {
        'info_hash': INFO_HASH,
        'peer_id': PEER_ID,
        'port': PEER_PORT,
        'event': event
    }
    response = requests.get(TRACKER_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        peers = data.get('peers', [])
        return peers
    else:
        print('Failed to announce to tracker:', response.text)
        return []

def handle_peer_connection(conn, addr):
    """
    Handle incoming connections from peers.
    """
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            # Expecting requests in the format: REQUEST_PIECE:<piece_index>
            if data.startswith('REQUEST_PIECE'):
                _, piece_index = data.strip().split(':')
                piece_index = int(piece_index)
                if have_pieces[piece_index]:
                    # Send the piece (for simplicity, sending piece index as data)
                    conn.sendall(f'PIECE_DATA:{piece_index}'.encode())
                else:
                    conn.sendall('PIECE_NOT_AVAILABLE'.encode())
            elif data.startswith('HAVE_PIECE'):
                # Peer informs us about a piece they have
                pass  # For simplicity, we won't track peer's pieces
    except Exception as e:
        print(f'Error handling peer {addr}: {e}')
    finally:
        conn.close()

def start_peer_server():
    """
    Start a server to accept incoming connections from peers.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('', PEER_PORT))
    server_sock.listen(5)
    print(f'Listening for peers on port {PEER_PORT}...')
    while True:
        conn, addr = server_sock.accept()
        threading.Thread(target=handle_peer_connection, args=(conn, addr)).start()

def download_pieces(peers):
    """
    Connect to peers and request pieces.
    """
    for peer in peers:
        peer_ip = peer['ip']
        peer_port = peer['port']
        if peer['peer_id'] == PEER_ID:
            continue  # Skip self

        threading.Thread(target=connect_to_peer, args=(peer_ip, peer_port)).start()

def connect_to_peer(ip, port):
    global have_pieces
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        print(f'Connected to peer {ip}:{port}')

        # Request pieces we don't have
        for i in range(total_pieces):
            if not have_pieces[i]:
                request = f'REQUEST_PIECE:{i}'
                sock.sendall(request.encode())
                data = sock.recv(1024).decode()
                if data.startswith('PIECE_DATA'):
                    # Receive piece data
                    _, piece_index = data.strip().split(':')
                    piece_index = int(piece_index)
                    have_pieces[piece_index] = 1
                    print(f'Downloaded piece {piece_index} from {ip}:{port}')
                    # Inform other peers about the new piece
                    # For simplicity, we won't implement 'have' messages here
                else:
                    print(f'Piece {i} not available from {ip}:{port}')
        sock.close()
    except Exception as e:
        print(f'Could not connect to peer {ip}:{port}: {e}')

def main():
    # Start peer server in a separate thread
    threading.Thread(target=start_peer_server, daemon=True).start()

    # Announce to tracker
    peers = announce_to_tracker('started')

    # Download pieces from peers
    download_pieces(peers)

    # Wait until all pieces are downloaded
    while not all(have_pieces):
        pass  # In a real application, you would use proper synchronization

    print('All pieces downloaded. File assembled.')

    # Announce completion to tracker
    announce_to_tracker('completed')

if __name__ == '__main__':
    main()
