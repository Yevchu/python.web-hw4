from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Lock
from datetime import datetime
from urllib.parse import urlparse, unquote_plus
import socket
import mimetypes
import pathlib
import json


UDP_IP = "127.0.0.1"
UDP_PORT = 5000
storage = 'storage/data.json'
client_info = {}
client_info_lock = Lock()

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('html/index.html')
        elif pr_url.path == '/message':
            self.send_html_file('html/message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('html/error.html', 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        data_parse = unquote_plus(data.decode())
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        with client_info_lock:
            client_info.update(data_dict)
        send_data_to_server(client_info)
        self.send_response(302)
        self.send_header('Location', '../html/message.html')
        self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.writel(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping the HTTP server.")
        http.server_close()

def send_data_to_server(data):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        bite_data = json.dumps(data).encode('utf-8')
        udp_socket.sendto(bite_data, (UDP_IP, UDP_PORT))

def save_data_to_json(data):
    try:
        with open(storage, "w") as file:
            json.dump(data, file)
    except Exception as e:
        print(f"An error occurred while writing to data.json: {e}")

def socket_server():
    data_dict_for_write = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((UDP_IP, UDP_PORT))
        try:
            while True:
                data_bytes, _ = udp_socket.recvfrom(1024)
                data_str = data_bytes.decode('utf-8')
                data_dict = json.loads(data_str)
                data_dict_for_write.update({str(datetime.now()): data_dict})
                save_data_to_json(data_dict_for_write)
        except KeyboardInterrupt:
            print("Server stopped by the user.")

if __name__ == '__main__':
    http_thread = Thread(target=http_server)
    server_thread = Thread(target=socket_server)

    http_thread.start()
    server_thread.start()

    http_thread.join()
    server_thread.join()