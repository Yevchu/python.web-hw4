from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from datetime import datetime
import socket
import urllib.parse
import mimetypes
import pathlib
import json


UDP_IP = "127.0.0.1"
UDP_PORT = 5000
storage = 'storage/data.json'
client_info = {}


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
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
        data_parse = urllib.parse.unquote_plus(data.decode())
        data_dict = {datetime.now(): {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}}
        client_info.update(data_dict)
        print(client_info)
        self.send_response(302)
        self.send_header('Location', '../html/message.html')
        self.end_headers()

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

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
        http.server_close()


def send_data_to_server(data):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        bite_data = json.dumps(data).encode('utf-8')
        udp_socket.sendto(bite_data, (UDP_IP, UDP_PORT))

def save_data_to_json(data):
    with open(storage, "w") as file:
        json.dump(data, file)

def socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((UDP_IP, UDP_PORT))
        try:
            while True:
                data_bytes, _ = udp_socket.recvfrom(1024)
                data_str = data_bytes.decode('utf-8')
                data_dict = json.loads(data_str)
                save_data_to_json(data_dict)
        except KeyboardInterrupt:
            print("Server stopped by the user.")

if __name__ == '__main__':
    http_thread = Thread(target=http_server)
    server_thread = Thread(target=socket_server)
    client_thread = Thread(target=send_data_to_server, args=(client_info,))

    http_thread.start()
    server_thread.start()
    client_thread.start()

    http_thread.join()
    server_thread.join()
    client_thread.join()
