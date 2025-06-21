import socket
import sys
import os
from datetime import datetime

def send_request(host, port, method, path, headers=None, body=None):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # Stempel waktu dengan milidetik

    print(f"[{current_time}] DEBUG: Preparing {method} request to {host}:{port}{path}")

    request_line = f"{method} {path} HTTP/1.1"
    
    request_headers = f"Host: {host}\r\n"
    if headers:
        for key, value in headers.items():
            request_headers += f"{key}: {value}\r\n"
    
    if body:
        if isinstance(body, str):
            body = body.encode('utf-8')
        request_headers += f"Content-Length: {len(body)}\r\n"
    
    full_request = f"{request_line}\r\n{request_headers}\r\n".encode('utf-8')
    if body:
        full_request += body

    print(f"[{current_time}] DEBUG: Full request prepared (first 100 bytes): {full_request[:100]!r}...")

    try:
        print(f"[{current_time}] DEBUG: Creating new socket.")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Opsional: Set timeout untuk menghindari hang selamanya
            sock.settimeout(10) # Timeout 10 detik

            print(f"[{current_time}] DEBUG: Attempting to connect to {host}:{port}.")
            sock.connect((host, port))
            print(f"[{current_time}] DEBUG: Connected successfully to {host}:{port}.")
            
            print(f"[{current_time}] DEBUG: Sending {len(full_request)} bytes of request data.")
            sock.sendall(full_request)
            print(f"[{current_time}] DEBUG: Request data sent. Waiting for response.")
            
            response_data = b''
            while True:
                current_time_recv = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{current_time_recv}] DEBUG: Receiving chunk...")
                chunk = sock.recv(4096)
                if not chunk:
                    print(f"[{current_time_recv}] DEBUG: No more chunks received. Connection closed by peer or end of stream.")
                    break
                response_data += chunk
                print(f"[{current_time_recv}] DEBUG: Received {len(chunk)} bytes. Total received: {len(response_data)} bytes.")
            
            print(f"[{current_time_recv}] DEBUG: Finished receiving response. Total bytes: {len(response_data)}. Decoding response.")
            return response_data.decode('utf-8', errors='ignore')
    except socket.timeout:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ERROR: Socket timed out while connecting or receiving data.")
        return f"Error: Socket timed out. Server unresponsive or network issue."
    except ConnectionRefusedError:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ERROR: Connection refused to {host}:{port}. Server not running or firewall blocking.")
        return f"Error: Connection refused. Server not running on {host}:{port} or firewall blocking."
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ERROR: An unexpected error occurred: {e}")
        return f"Error: {e}"

def main():
    server_host = '127.0.0.1' # Atau IP Docker Mesin-1 jika di kontainer berbeda
    server_port = 8000

    print("=== HTTP Client CLI ===")
    print("Commands: LIST, GET <filename>, UPLOAD <local_filepath> [remote_filename], DELETE <filename>, QUIT")

    while True:
        cmd_input = input(">> ").strip().split(maxsplit=2)
        command = cmd_input[0].upper()

        if command == 'LIST':
            print("Requesting file list...")
            response = send_request(server_host, server_port, 'GET', '/list_files')
            print("\n--- Server Response ---")
            print(response)
            print("-----------------------\n")

        elif command == 'GET':
            if len(cmd_input) < 2:
                print("Usage: GET <filename>")
                continue
            filename = cmd_input[1]
            print(f"Requesting file: {filename}")
            response = send_request(server_host, server_port, 'GET', f'/{filename}')
            print("\n--- Server Response ---")
            print(response)
            print("-----------------------\n")

        elif command == 'UPLOAD':
            if len(cmd_input) < 2:
                print("Usage: UPLOAD <local_filepath> [remote_filename]")
                continue
            
            local_filepath = cmd_input[1]
            remote_filename = cmd_input[2] if len(cmd_input) > 2 else os.path.basename(local_filepath)

            if not os.path.exists(local_filepath):
                print(f"Error: Local file '{local_filepath}' not found.")
                continue
            
            try:
                with open(local_filepath, 'rb') as f:
                    file_content = f.read()
                
                headers = {'Filename': remote_filename} # Custom header untuk nama file
                print(f"Uploading '{local_filepath}' as '{remote_filename}'...")
                response = send_request(server_host, server_port, 'POST', '/upload', headers=headers, body=file_content)
                print("\n--- Server Response ---")
                print(response)
                print("-----------------------\n")
            except Exception as e:
                print(f"Error reading file: {e}")

        elif command == 'DELETE':
            if len(cmd_input) < 2:
                print("Usage: DELETE <filename>")
                continue
            filename_to_delete = cmd_input[1]
            print(f"Deleting file: {filename_to_delete}")
            response = send_request(server_host, server_port, 'DELETE', f'/{filename_to_delete}')
            print("\n--- Server Response ---")
            print(response)
            print("-----------------------\n")

        elif command == 'QUIT':
            print("Exiting client.")
            break

        else:
            print("Unknown command. Please use LIST, GET, UPLOAD, DELETE, or QUIT.")

if __name__ == '__main__':
    main()