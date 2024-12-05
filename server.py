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
            text="Hint > Select a directory first, then start the server.",
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

        # Thread lock for shared resources
        self.lock = Lock()

        # Persist file metadata
        self.metadata_file = "file_metadata.pkl"
        self.load_metadata()

    def log(self, message):
        # TODO: include time stamp in logs
        # write HERE
        
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    def select_directory(self):
        self.files_dir = filedialog.askdirectory()
        if self.files_dir:
            self.log(f"s]-> Files directory set to:\n> {self.files_dir}\n")

    # given the directory and the port, the server will be up and running
    def start_server(self):

        # to add placeholder functionality for better UI/UX
        def add_placeholder(entry, placeholder_text):
            def on_focus_in(event):
                if entry.get() == placeholder_text:
                    entry.delete(0, tk.END)
                    entry.config(fg="black")

            def on_focus_out(event):
                if not entry.get():
                    entry.insert(0, placeholder_text)
                    entry.config(fg="gray")

            entry.insert(0, placeholder_text)
            entry.config(fg="gray")
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

        # can't start the server if there's no directory to work with
        if not self.files_dir:
            messagebox.showerror("Error", "Select a directory first!")
            return

        # Custom pop-up window for port input
        port_window = tk.Toplevel(self.root)
        port_window.title("Set Server Port")
        port_window.geometry("400x250")
        port_window.resizable(False, False)

        tk.Label(port_window, text="Enter server's port number:").pack(pady=10)
        port_entry = tk.Entry(port_window)
        port_entry.pack(padx=20, pady=5)
        add_placeholder(port_entry, "e.g., 8080")  # Add placeholder to port entry

        # custom function for handling the pop-up for setting the port
        def submit_port():
            port = port_entry.get().strip()
            if not port.isdigit():
                messagebox.showerror("Error", "Port must be a positive integer number!")
                return
            self.port = int(port)
            port_window.destroy()

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)
            self.log(f"s]-> Server started on port {self.port}\n")

        # the new hint must inform the client about how they can close the GUI
        self.update_hint(
            "NOTE > In order to close this GUI, press the 'close' button of the app's window.",
            "gray"
        )

        # Add Submit button
        submit_button = tk.Button(port_window, text="Start Server", command=submit_port)
        submit_button.pack(pady=(10, 20))

        # Handle pressing Enter key
        port_window.bind("<Return>", lambda event: submit_port())

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
            self.log(f"s]-> Client connected: {client_name}\n")
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
        # in some rare cases, upload would fail with no apparent reason
        # hence, I used the try-catch block to determine the issue 
        try:
            filename = f"{client_name}_{command['filename']}"
            filepath = os.path.join(self.files_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(command['content'])
            self.file_owners[filename] = client_name
            self.log(f"File uploaded: {filename} by {client_name}")

            # to use the content later
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
            
            # this is a list, where each item is a dictionary
            # and each dictionary has the file's name as the key,
            # and the file's owner as its value because filenames are unique but not owner names
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
            # the desired file actually exists in the server
            os.remove(filepath)
            del self.file_owners[filename]

            # update the server's cache
            self.save_metadata()
            self.log(f"s]-> File deleted: {filename}\n")
            self.send_with_size(client_socket, {"status": "DELETE_SUCCESS"})
        else:
            # can't delete file that doesn't exist in our server obviously
            self.send_with_size(client_socket, {"status": "ERROR", "message": "File not found."})


    def handle_download(self, command, client_socket):
        filename = f"{command['owner']}_{command['filename']}"
        filepath = os.path.join(self.files_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                file_content = f.read()
            self.send_with_size(client_socket, {"status": "SUCCESS", "content": file_content})
        else:
            # download almost never fails, however, there are some weird edge cases
            # such as if you try to download cached files that actually don't exist
            # but somehow appear in the files' list for no valid reason
            self.send_with_size(client_socket, {"status": "ERROR", "message": "e]-> File not found.\n"})


    # we use this metadata for handling large files (download/upload)
    def load_metadata(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'rb') as f:
                self.file_owners = pickle.load(f)

    def save_metadata(self):
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.file_owners, f)

    def send_with_size(self, sock, data):
        """
        - Send data with its size prepended.
        - Can change the fixed-width manually.
        """
        serialized_data = pickle.dumps(data)
        data_length = len(serialized_data)
        
        # to send length as a fixed-width 10-character string
        sock.sendall(f"{data_length:<10}".encode())  
        sock.sendall(serialized_data)

    def recv_all(self, sock):
        """
        - Receive all data from the socket.
        - Note that they're encoded as binary earlier.
        """
        # to read the size of the incoming data
        data_length = int(sock.recv(10).decode().strip())  
        data = b"" # for binary format
        while len(data) < data_length:
            packet = sock.recv(4096)
            if not packet:
                break
            data += packet
        return pickle.loads(data)


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
                self.log(f"e]-> Error closing client socket for {client_name}: {e}\n")

        # Wait for client threads to finish
        for thread in self.client_threads:
            thread.join(timeout=2)  # Set a timeout to avoid indefinite blocking

        # Save metadata and gracefully exit
        self.save_metadata()
        self.log("Server shut down successfully.")
        self.root.quit() # this works better than other techniques! do NOT change


    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.mainloop()


if __name__ == "__main__":
    server = ServerGUI()
    server.run()
