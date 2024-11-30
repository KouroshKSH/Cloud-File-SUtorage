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
        self.log_box = tk.Listbox(self.root, width=80, height=20)
        self.log_box.pack()
        self.start_button = tk.Button(self.root, text="Start Server", command=self.start_server)
        self.start_button.pack()
        self.select_dir_button = tk.Button(self.root, text="Select Directory", command=self.select_directory)
        self.select_dir_button.pack()

        self.server_socket = None  # Server's socket for listening to clients
        self.client_threads = []  # List to manage client threads
        self.files_dir = None  # Directory for storing files
        self.clients = {}  # Active clients: {client_name: socket}
        self.file_owners = {}  # File ownership: {filename: client_name}

        self.running = True  # Server status

    def log(self, message):
        """Log messages to the server GUI."""
        self.log_box.insert(tk.END, message)
        self.log_box.yview(tk.END)

    def select_directory(self):
        """Allow the user to select a directory for file storage."""
        self.files_dir = filedialog.askdirectory()
        if self.files_dir:
            self.log(f"Files directory set to: {self.files_dir}")

    def start_server(self):
        """Start the server on a specified port."""
        if not self.files_dir:
            messagebox.showerror("Error", "Select a directory first!")
            return

        self.port = tk.simpledialog.askinteger("Input", "Enter server port:")
        if not self.port:
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('', self.port))
        self.server_socket.listen(5)
        self.log(f"Server started on port {self.port}")

        # Thread for accepting clients
        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        """Accept and handle multiple client connections."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.log(f"Connection attempt from {addr}")
                # Create a new thread for each client
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
                self.client_threads.append(client_thread)
                client_thread.start()
            except Exception as e:
                self.log(f"Error accepting client: {e}")
                break

    def handle_client(self, client_socket):
        """Handle interactions with a connected client."""
        try:
            client_name = client_socket.recv(1024).decode()
            if client_name in self.clients:
                client_socket.sendall(b"ERROR: Name already in use.")
                client_socket.close()
                return

            # Register client
            self.clients[client_name] = client_socket
            self.log(f"Client connected: {client_name}")
            client_socket.sendall(b"CONNECTED")

            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                command = pickle.loads(data)
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
            # Cleanup on client disconnect
            if client_name in self.clients:
                del self.clients[client_name]
            client_socket.close()
            self.log(f"Client disconnected: {client_name}")

    def handle_upload(self, client_name, command, client_socket):
        """Handle file uploads from clients."""
        try:
            filename = f"{client_name}_{command['filename']}"
            filepath = os.path.join(self.files_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(command['content'])  # Add chunked writing if file size exceeds memory
            self.file_owners[filename] = client_name
            self.log(f"File uploaded: {filename} by {client_name}")
            client_socket.sendall(b"UPLOAD_SUCCESS")
        except Exception as e:
            self.log(f"Error handling file upload: {e}")
            client_socket.sendall(b"UPLOAD_FAILED")

    def handle_list(self, client_socket):
        """Send the list of files and their owners to a client."""
        file_list = [{"filename": f, "owner": o} for f, o in self.file_owners.items()]
        client_socket.sendall(pickle.dumps(file_list))

    def handle_delete(self, client_name, command, client_socket):
        """Delete a file uploaded by the client."""
        filename = f"{client_name}_{command['filename']}"
        filepath = os.path.join(self.files_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            del self.file_owners[filename]
            self.log(f"File deleted: {filename}")
            client_socket.sendall(b"DELETE_SUCCESS")
        else:
            client_socket.sendall(b"ERROR: File not found.")

    def handle_download(self, command, client_socket):
        """Handle file download requests from clients."""
        filename = f"{command['owner']}_{command['filename']}"
        filepath = os.path.join(self.files_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                file_content = f.read()
            client_socket.sendall(pickle.dumps({"status": "SUCCESS", "content": file_content}))
        else:
            client_socket.sendall(b"ERROR: File not found.")

    def shutdown(self):
        """Shutdown the server and clean up resources."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for thread in self.client_threads:
            thread.join()
        self.log("Server shut down.")

    def run(self):
        """Run the server GUI."""
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.mainloop()

if __name__ == "__main__":
    server = ServerGUI()
    server.run()