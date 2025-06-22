import sys
import os
import os.path
import uuid
from glob import glob
from datetime import datetime
import socket
import threading
import multiprocessing
import concurrent.futures # Untuk ThreadPoolExecutor dan ProcessPoolExecutor

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.jpeg'] = 'image/jpeg' # Tambahkan untuk ekstensi umum
        self.types['.png'] = 'image/png'   # Tambahkan ekstensi gambar lain
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.types['.css'] = 'text/css'    # Tambahkan CSS
        self.types['.js'] = 'application/javascript' # Tambahkan JavaScript
        self.types['.json'] = 'application/json' # Tambahkan JSON

    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT') # Format RFC 1123
        resp = []
        resp.append(f"HTTP/1.1 {kode} {message}\r\n") # Gunakan HTTP/1.1 untuk Connection: keep-alive (meskipun kita pakai close)
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n") # Tetap close untuk kesederhanaan
        resp.append("Server: myserver/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        for kk in headers:
            resp.append(f"{kk}:{headers[kk]}\r\n")
        resp.append("\r\n")

        response_headers = ''.join(resp) # Lebih efisien
        
        if not isinstance(messagebody, bytes): # Gunakan isinstance untuk tipe yang benar
            messagebody = messagebody.encode('utf-8') # Default ke UTF-8

        response = response_headers.encode('utf-8') + messagebody
        return response

    def proses(self, data):
        requests = data.split(b"\r\n") # Pecah byte stream, bukan string
        if not requests:
            return self.response(400, 'Bad Request', b'')

        baris_request = requests[0].decode('utf-8', errors='ignore') # Decode baris pertama saja
        all_headers_raw = requests[1:]
        
        headers_dict = {}
        for h in all_headers_raw:
            if not h: continue # Skip empty lines
            try:
                h_decoded = h.decode('utf-8', errors='ignore')
                key, value = h_decoded.split(':', 1)
                headers_dict[key.strip().lower()] = value.strip()
            except ValueError:
                # Handle malformed headers if necessary
                pass

        try:
            j = baris_request.split(" ")
            method = j[0].upper().strip()
            object_address = j[1].strip()

            if method == 'GET':
                return self.http_get(object_address, headers_dict)
            elif method == 'POST':
                # POST data might be in the body, so pass the raw data
                body_start = data.find(b'\r\n\r\n') + 4
                request_body = data[body_start:]
                return self.http_post(object_address, headers_dict, request_body)
            elif method == 'DELETE': # Menambahkan method DELETE
                return self.http_delete(object_address, headers_dict)
            else:
                return self.response(400, 'Bad Request', b'Unknown Method')
        except IndexError:
            return self.response(400, 'Bad Request', b'Malformed Request Line')
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e).encode())

    def http_get(self, object_address, headers):
        thedir = './'
        
        # Oprasi "LIST" untuk melihat daftar file
        if object_address == '/list_files':
            try:
                files_in_dir = [f for f in os.listdir(thedir) if os.path.isfile(os.path.join(thedir, f))]
                
                # Ubah bagian ini untuk membuat respons teks biasa
                dir_list_plain_text = "Daftar File di Server:\r\n" # Judul
                for f in files_in_dir:
                    dir_list_plain_text += f"- {f}\r\n" # Setiap file di baris baru dengan bullet
                
                # Ubah Content-type menjadi 'text/plain'
                return self.response(200, 'OK', dir_list_plain_text.encode('utf-8'), {'Content-type': 'text/plain'})
            except Exception as e:
                return self.response(500, 'Internal Server Error', str(e).encode())


        if object_address == '/':
            return self.response(200, 'OK', b'Ini Adalah web Server percobaan', {})

        if object_address == '/video':
            return self.response(302, 'Found', b'', {'Location': 'https://youtu.be/katoxpnTf04'})
        
        if object_address == '/santai':
            return self.response(200, 'OK', b'santai saja', {})

        object_address = object_address[1:] # Hapus '/' di awal
        filepath = os.path.join(thedir, object_address)

        if not os.path.isfile(filepath): # Pastikan itu file, bukan direktori
            return self.response(404, 'Not Found', b'File not found')
        
        try:
            with open(filepath, 'rb') as fp:
                isi = fp.read()
            
            fext = os.path.splitext(filepath)[1].lower() # Pastikan ekstensi kecil
            content_type = self.types.get(fext, 'application/octet-stream') # Default jika tipe tidak dikenal
            
            headers = {'Content-type': content_type}
            
            return self.response(200, 'OK', isi, headers)
        except IOError:
            return self.response(500, 'Internal Server Error', b'Could not read file')
        except Exception as e:
            return self.response(500, 'Internal Server Error', str(e).encode())


    def http_post(self, object_address, headers, request_body): # Tambah request_body
        thedir = './'
        object_address = object_address[1:] # Hapus '/' di awal

        if object_address == 'upload': # Contoh path untuk upload
            filename = headers.get('filename', None) # Asumsikan client mengirim 'filename' header
            if not filename:
                # Alternatif: Generate nama file unik atau ambil dari path
                filename = f"uploaded_{uuid.uuid4().hex}" # Nama file unik
            
            filepath = os.path.join(thedir, filename)
            try:
                with open(filepath, 'wb') as f:
                    f.write(request_body)
                return self.response(200, 'OK', f'File {filename} uploaded successfully'.encode(), {})
            except Exception as e:
                return self.response(500, 'Internal Server Error', f'Failed to upload file: {e}'.encode())
        else:
            return self.response(405, 'Method Not Allowed', b'POST method only for /upload')

    def http_delete(self, object_address, headers): # Menambahkan method DELETE
        thedir = './'
        object_address = object_address[1:] # Hapus '/' di awal

        filepath = os.path.join(thedir, object_address)

        if not os.path.isfile(filepath):
            return self.response(404, 'Not Found', b'File to delete not found')
        
        try:
            os.remove(filepath)
            return self.response(200, 'OK', f'File {object_address} deleted successfully'.encode(), {})
        except Exception as e:
            return self.response(500, 'Internal Server Error', f'Failed to delete file: {e}'.encode())


# --- Implementasi Server Utama dengan Pool ---

class ThreadedHTTPServer:
    def __init__(self, host='0.0.0.0', port=8000, max_workers=10, server_type='thread'):
        self.host = host
        self.port = port
        self.server_type = server_type
        self.max_workers = max_workers
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.httpserver_handler = HttpServer()

    def _handle_client(self, conn, addr):
        try:
            # Ganti logging.info dengan print
            if self.server_type == 'thread':
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Handling connection from {addr} on Thread ID: {threading.get_ident()}")
            elif self.server_type == 'process':
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Handling connection from {addr} on Process ID: {os.getpid()}")
            
            all_data = b''
            # Baca header dulu untuk Content-Length
            while True:
                chunk = conn.recv(1024)
                all_data += chunk
                if b'\r\n\r\n' in all_data:
                    break
            
            headers_raw = all_data.split(b'\r\n\r\n')[0]
            headers_dict = {}
            for h in headers_raw.split(b'\r\n')[1:]:
                if not h: continue
                try:
                    h_decoded = h.decode('utf-8', errors='ignore')
                    key, value = h_decoded.split(':', 1)
                    headers_dict[key.strip().lower()] = value.strip()
                except ValueError:
                    pass
            
            content_length = int(headers_dict.get('content-length', 0))
            
            # Jika ada body (POST request), baca sisa body
            if content_length > 0:
                body_read = len(all_data) - (all_data.find(b'\r\n\r\n') + 4)
                while body_read < content_length:
                    remaining_data = conn.recv(1024)
                    if not remaining_data: break
                    all_data += remaining_data
                    body_read += len(remaining_data)

            response = self.httpserver_handler.proses(all_data)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] SERVER DEBUG: Response prepared for {addr}, length: {len(response)} bytes.")
            conn.sendall(response)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] SERVER DEBUG: Response sent to {addr}.")
            conn.shutdown(socket.SHUT_WR) # Coba ini
        except ConnectionResetError:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Client {addr} disconnected unexpectedly.")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error handling client {addr}: {e}")
        finally:
            conn.close()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Connection from {addr} closed.")

    def run(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"HTTP Server ({self.server_type} pool) listening on {self.host}:{self.port}...")

        if self.server_type == 'thread':
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        elif self.server_type == 'process':
            executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)
        else:
            raise ValueError("Invalid server_type. Must be 'thread' or 'process'.")

        try:
            while True:
                conn, addr = self.sock.accept()
                executor.submit(self._handle_client, conn, addr)
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            executor.shutdown(wait=True)
            self.sock.close()


if __name__ == "__main__":
    # Untuk menjalankan Thread Pool Server:
    server = ThreadedHTTPServer(port=8000, server_type='thread', max_workers=10)
    server.run()