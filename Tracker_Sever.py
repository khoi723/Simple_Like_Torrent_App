# tracker_server.py

from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse
import threading
import json

# Global dictionary to store peer information
peers_info = {}

class TrackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global peers_info

        # Parse the query parameters
        parsed_path = urlparse.urlparse(self.path)
        params = urlparse.parse_qs(parsed_path.query)

        # Extract necessary parameters
        event = params.get('event', [None])[0]
        peer_id = params.get('peer_id', [None])[0]
        ip = self.client_address[0]
        port = params.get('port', [None])[0]
        info_hash = params.get('info_hash', [None])[0]

        response = {}

        if not peer_id or not port or not info_hash:
            response['failure reason'] = 'Missing required parameters.'
            self.send_response(400)
        else:
            port = int(port)
            # Handle different events
            if event == 'started':
                # Register the peer
                peers_info[peer_id] = {
                    'ip': ip,
                    'port': port,
                    'info_hash': info_hash
                }
                response['tracker id'] = 'tracker123'
                response['peers'] = [
                    {
                        'peer_id': peer_id,
                        'ip': peer['ip'],
                        'port': peer['port'],
                        'info_hash': peer['info_hash']
                    }
                    for peer_id, peer in peers_info.items()
                ]
                self.send_response(200)
            elif event == 'stopped':
                # Remove the peer
                peers_info.pop(peer_id, None)
                self.send_response(200)
            elif event == 'completed':
                # Peer has completed downloading
                # For simplicity, we'll just acknowledge
                self.send_response(200)
            else:
                # Regular announce
                response['peers'] = list(peers_info.values())
                self.send_response(200)

        # Send headers
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        # Send response
        self.wfile.write(json.dumps(response).encode())

def run_tracker(server_class=HTTPServer, handler_class=TrackerHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Tracker server running on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run_tracker()
