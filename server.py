import socket
import threading
from threading import Lock
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import pickle

"""
Convention:
1. 's]-> ...' means success of an operation
2. 'e]-> ...' means error for an attempt
"""

class ServerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Server")
        
        # for responsiveness
        self.root.geometry("700x500")  

        # Log box with scrollbars
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_box = tk.Text(self.log_frame, wrap=tk.WORD, state=tk.DISABLED, height=15)
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

        # ??? should it be here ???
        self.lock = Lock()  # Thread lock for shared resources

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
            self.log(f"s]-> Files directory set to:\n|__ {self.files_dir}\n")

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
        self.log(f"s]-> Server started on port {self.port}\n")

        # the new hint must inform the client about how they can close the GUI
        self.update_hint(
            "NOTE: In order to close this GUI, press the 'close' button of the app's window.",
            "gray"
        )

        threading.Thread(target=self.accept_clients, daemon=True).start()

    # to update the hint label's content and color
    def update_hint(self, new_text, new_color):
        self.hint_label.config(text=new_text, fg=new_color)
    
    def accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.log(f"Connection attempt from {addr}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
                self.client_threads.append(client_thread)
                client_thread.start()
            except Exception as e:
                self.log(f"e]-> Error accepting client: {e}\n")
                break

    def handle_client(self, client_socket):
        client_name = None  # Ensure client_name is always defined
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
                try:
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
                    self.log(f"Error handling client command: {e}")
                    break
        except Exception as e:
            self.log(f"Error handling client: {e}")
        finally:
            if client_name in self.clients:
                del self.clients[client_name]
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except Exception as e:
                self.log(f"Error closing socket for {client_name}: {e}")
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
            self.log(f"e]-> Error handling file upload: {e}!\n")
            self.send_with_size(client_socket, {"status": "UPLOAD_FAILED"})


    def handle_list(self, client_socket):
        """
        - Use a threading lock to ensure `file_owners` is not being modified while it is being read for the `handle_list` function
        - Validate `file_list` to ensure it's correctly formatted and non-empty before sending
        """
        with self.lock:  # Ensure thread-safe access
            file_list = [{
                "filename": f,
                 "owner": o} 
                for f, o in self.file_owners.items()
            ]
        
        # Validate and send the response
        if file_list:  # Ensure the list is not empty
            self.send_with_size(client_socket, file_list)
        else:
            self.send_with_size(client_socket, [])


    def handle_delete(self, client_name, command, client_socket):
        filename = f"{client_name}_{command['filename']}"
        filepath = os.path.join(self.files_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            del self.file_owners[filename]
            self.save_metadata()
            self.log(f"s]-> File deleted: {filename}\n")
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
        self.log("Shutting down the server...")
        self.running = False

        # Close the server socket
        if self.server_socket:
            self.server_socket.close()

        # Disconnect clients and close their sockets
        for client_name, client_socket in self.clients.items():
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except Exception as e:
                self.log(f"Error closing client socket for {client_name}: {e}")

        # Wait for client threads to finish
        for thread in self.client_threads:
            thread.join(timeout=2)  # Set a timeout to avoid indefinite blocking

        # Save metadata and gracefully exit
        self.save_metadata()
        self.log("Server shut down successfully.")
        self.root.quit()


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
