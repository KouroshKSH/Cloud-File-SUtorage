"""
Local Host: 127.0.0.1
"""

import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import pickle
import os

class ClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Client")
        self.log_box = tk.Listbox(self.root, width=80, height=20)
        self.log_box.pack()
        self.connect_button = tk.Button(self.root, text="Connect to Server", command=self.connect_to_server)
        self.connect_button.pack()
        self.upload_button = tk.Button(self.root, text="Upload File", command=self.upload_file, state=tk.DISABLED)
        self.upload_button.pack()
        self.list_button = tk.Button(self.root, text="List Files", command=self.list_files, state=tk.DISABLED)
        self.list_button.pack()
        self.download_button = tk.Button(self.root, text="Download File", command=self.download_file, state=tk.DISABLED)
        self.download_button.pack()
        self.delete_button = tk.Button(self.root, text="Delete File", command=self.delete_file, state=tk.DISABLED)
        self.delete_button.pack()

        self.client_socket = None
        self.username = None

    def log(self, message):
        """Log messages to the client GUI."""
        self.log_box.insert(tk.END, message)
        self.log_box.yview(tk.END)

    def connect_to_server(self):
        """Connect to the server."""
        server_ip = tk.simpledialog.askstring("Input", "Enter server IP:")
        server_port = tk.simpledialog.askinteger("Input", "Enter server port:")
        self.username = tk.simpledialog.askstring("Input", "Enter your username:")

        if not server_ip or not server_port or not self.username:
            messagebox.showerror("Error", "All fields are required!")
            return

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((server_ip, server_port))
            self.client_socket.sendall(self.username.encode())
            response = self.client_socket.recv(1024).decode()
            if "ERROR" in response:
                self.log(response)
                self.client_socket.close()
                self.client_socket = None
            else:
                self.log(f"Connected to server as {self.username}")
                self.enable_buttons()
                threading.Thread(target=self.listen_for_notifications, daemon=True).start()
        except Exception as e:
            self.log(f"Error connecting to server: {e}")
            self.client_socket = None

    def listen_for_notifications(self):
        """Listen for server notifications."""
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                self.log(data.decode())
            except Exception as e:
                self.log(f"Error: {e}")
                break

    def enable_buttons(self):
        """Enable buttons after successful connection."""
        self.upload_button.config(state=tk.NORMAL)
        self.list_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def upload_file(self):
        """Upload a file to the server."""
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            command = {"type": "upload", "filename": filename, "content": content}
            self.client_socket.sendall(pickle.dumps(command))
            self.log(f"Uploaded file: {filename}")
        except Exception as e:
            self.log(f"Error uploading file: {e}")

    # new code

    def list_files(self):
        """Request the list of files from the server in a separate thread."""
        threading.Thread(target=self._list_files_thread, daemon=True).start()

    def _list_files_thread(self):
        """Threaded function to request and display the list of files."""
        try:
            command = {"type": "list"}
            self.client_socket.sendall(pickle.dumps(command))  # Send the request
            data = self.client_socket.recv(4096)  # Receive the response
            file_list = pickle.loads(data)  # Deserialize the response
            self.log("Files on server:")
            for file in file_list:
                self.log(f"{file['filename']} (Owner: {file['owner']})")
        except Exception as e:
            self.log(f"Error retrieving file list: {e}")




    # previous code caused freezing
    # reason: The freezing issue likely stems from the client GUI's "list files" functionality not being handled in a separate thread. 
    # ... When a client sends the "list files" request to the server, it waits for the response, 
    # ... but this operation blocks the GUI event loop, causing the window to freeze.
    
    # def list_files(self):
    #     """Request the list of files from the server."""
    #     command = {"type": "list"}
    #     self.client_socket.sendall(pickle.dumps(command))
    #     data = self.client_socket.recv(4096)
    #     file_list = pickle.loads(data)
    #     self.log("Files on server:")
    #     for file in file_list:
    #         self.log(f"{file['filename']} (Owner: {file['owner']})")

    def delete_file(self):
        """Delete a file on the server."""
        filename = tk.simpledialog.askstring("Input", "Enter the filename to delete:")
        if not filename:
            return

        command = {"type": "delete", "filename": filename}
        self.client_socket.sendall(pickle.dumps(command))
        self.log(f"Requested to delete file: {filename}")

    def download_file(self):
        """Download a file from the server."""
        filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
        owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
        if not filename or not owner:
            return

        command = {"type": "download", "filename": filename, "owner": owner}
        self.client_socket.sendall(pickle.dumps(command))
        data = self.client_socket.recv(4096)
        response = pickle.loads(data)
        if response["status"] == "SUCCESS":
            save_path = filedialog.asksaveasfilename()
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(response["content"])
                self.log(f"File downloaded: {filename}")
        else:
            self.log("Error: File not found.")

    def run(self):
        """Run the client GUI."""
        self.root.mainloop()

if __name__ == "__main__":
    client = ClientGUI()
    client.run()
