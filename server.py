import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import pickle

class ServerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Server")
        
        # for responsiveness
        self.root.geometry("500x700")  

        # Log box with scrollbars
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_box = tk.Text(self.log_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scroll = tk.Scrollbar(self.log_frame, command=self.log_box.yview)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box.config(yscrollcommand=self.log_scroll.set)

        # a hint message for the first-timer who might not know what to do
        self.hint_label = tk.Label(
            self.root, 
            text="Hint: Select a directory first, then start the server.",
            fg="blue",
            anchor="w"
        )
        self.hint_label.pack(fill=tk.X, padx=10)

        # Buttons
        self.select_dir_button = tk.Button(self.root, text="Select Directory", command=self.select_directory, width=20)
        self.select_dir_button.pack(pady=(10, 0))  # Slight padding for neatness
        self.start_button = tk.Button(self.root, text="Start Server", command=self.start_server, width=20)
        self.start_button.pack(pady=(5, 10))

        self.server_socket = None
        self.client_threads = []
        self.files_dir = None
        self.clients = {}
        self.file_owners = {}
        self.running = True

        # Persist file metadata
        self.metadata_file = "file_metadata.pkl"
        self.load_metadata()

    def log(self, message):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def select_directory(self):
        self.files_dir = filedialog.askdirectory()
        if self.files_dir:
            self.log(f"1]-> Files directory set to:\t\n{self.files_dir}\n")

    def start_server(self):
        if not self.files_dir:
            messagebox.showerror("Error", "Select a directory first!")
            return

        self.port = tk.simpledialog.askinteger("Input", "Enter server port:")
        if not self.port:
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('', self.port))
        self.server_socket.listen(5)
        self.log(f"2]-> Server started on port {self.port}\n")

        # Hide the hint label
        self.hint_label.pack_forget()

        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.log(f"Connection attempt from {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
                self.client_threads.append(client_thread)
                client_thread.start()
            except Exception as e:
                self.log(f"Error accepting client: {e}")
                break

    def handle_client(self, client_socket):
        try:
            client_name = client_socket.recv(1024).decode()
            if client_name in self.clients:
                client_socket.sendall(b"ERROR: Name already in use.")
                client_socket.close()
                return

            self.clients[client_name] = client_socket
            self.log(f"Client connected: {client_name}")
            client_socket.sendall(b"CONNECTED")

            while self.running:
                command = self.recv_all(client_socket)
                if not command:
                    break

                if command["type"] == "upload":
                    self.handle_upload(client_name, command, client_socket)
                elif command["type"] == "list":
                    self.handle_list(client_socket)
                elif command["type"] == "delete":
                    self.handle_delete(client_name, command, client_socket)
                elif command["type"] == "download":
                    self.handle_download(command, client_socket)
        except Exception as e:
            self.log(f"Error handling client: {e}")
        finally:
            if client_name in self.clients:
                del self.clients[client_name]
            client_socket.close()
            self.log(f"Client disconnected: {client_name}")

    def handle_upload(self, client_name, command, client_socket):
        try:
            filename = f"{client_name}_{command['filename']}"
            filepath = os.path.join(self.files_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(command['content'])
            self.file_owners[filename] = client_name
            self.log(f"File uploaded: {filename} by {client_name}")
            self.save_metadata()
            self.send_with_size(client_socket, {"status": "UPLOAD_SUCCESS"})
        except Exception as e:
            self.log(f"Error handling file upload: {e}")
            self.send_with_size(client_socket, {"status": "UPLOAD_FAILED"})

    def handle_list(self, client_socket):
        file_list = [{"filename": f, "owner": o} for f, o in self.file_owners.items()]
        self.send_with_size(client_socket, file_list)

    def handle_delete(self, client_name, command, client_socket):
        filename = f"{client_name}_{command['filename']}"
        filepath = os.path.join(self.files_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            del self.file_owners[filename]
            self.save_metadata()
            self.log(f"File deleted: {filename}")
            self.send_with_size(client_socket, {"status": "DELETE_SUCCESS"})
        else:
            self.send_with_size(client_socket, {"status": "ERROR", "message": "File not found."})

    def handle_download(self, command, client_socket):
        filename = f"{command['owner']}_{command['filename']}"
        filepath = os.path.join(self.files_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                file_content = f.read()
            self.send_with_size(client_socket, {"status": "SUCCESS", "content": file_content})
        else:
            self.send_with_size(client_socket, {"status": "ERROR", "message": "File not found."})

    def load_metadata(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'rb') as f:
                self.file_owners = pickle.load(f)

    def save_metadata(self):
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.file_owners, f)

    def shutdown(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for thread in self.client_threads:
            thread.join()
        self.save_metadata()
        self.log("Server shut down.")
        self.root.quit() # to gracefully exit the GUI window

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.mainloop()

    def send_with_size(self, sock, data):
        """Send data with its size prepended."""
        serialized_data = pickle.dumps(data)
        data_length = len(serialized_data)
        sock.sendall(f"{data_length:<10}".encode())  # Send length as a fixed-width 10-character string
        sock.sendall(serialized_data)

    def recv_all(self, sock):
        """Receive all data from the socket."""
        data_length = int(sock.recv(10).decode().strip())  # Read the size of the incoming data
        data = b""
        while len(data) < data_length:
            packet = sock.recv(4096)
            if not packet:
                break
            data += packet
        return pickle.loads(data)

if __name__ == "__main__":
    server = ServerGUI()
    server.run()
