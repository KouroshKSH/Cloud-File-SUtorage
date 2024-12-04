"""
Local Host: 127.0.0.1
"""

import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import pickle
import os


# class ClientGUI:
#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title("Client")

#         # for responsiveness
#         self.root.geometry("600x500") 

#         # Configure grid layout
#         self.root.columnconfigure(0, weight=1)
#         self.root.rowconfigure(0, weight=1)
#         self.root.rowconfigure(1, weight=0)

#         # Create log box using Text widget
#         self.log_box = tk.Text(self.root, wrap="word", state="disabled", height=20)
#         self.log_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

#         # Add vertical scrollbar to the log box
#         self.scrollbar = tk.Scrollbar(self.root, command=self.log_box.yview)
#         self.scrollbar.grid(row=0, column=1, sticky="ns")
#         self.log_box.configure(yscrollcommand=self.scrollbar.set)

#         # Add buttons
#         self.button_frame = tk.Frame(self.root)
#         self.button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
#         self.button_frame.columnconfigure(0, weight=1)

#         self.connect_button = tk.Button(self.button_frame, text="Connect to Server", command=self.connect_to_server)
#         self.connect_button.grid(row=0, column=0, padx=5)

#         self.upload_button = tk.Button(self.button_frame, text="Upload File", command=self.upload_file, state=tk.DISABLED)
#         self.upload_button.grid(row=0, column=1, padx=5)

#         self.list_button = tk.Button(self.button_frame, text="List Files", command=self.list_files, state=tk.DISABLED)
#         self.list_button.grid(row=0, column=2, padx=5)

#         self.download_button = tk.Button(self.button_frame, text="Download File", command=self.download_file, state=tk.DISABLED)
#         self.download_button.grid(row=0, column=3, padx=5)

#         self.delete_button = tk.Button(self.button_frame, text="Delete File", command=self.delete_file, state=tk.DISABLED)
#         self.delete_button.grid(row=0, column=4, padx=5)

#         self.client_socket = None
#         self.username = None



class ClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Client")

        # for responsiveness
        self.root.geometry("700x500")

        # Configure grid layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        # Create log box using Text widget
        self.log_box = tk.Text(self.root, wrap="word", state="disabled", height=20)
        self.log_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Add vertical scrollbar to the log box
        self.scrollbar = tk.Scrollbar(self.root, command=self.log_box.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=self.scrollbar.set)

        # Add hint label
        self.hint_label = tk.Label(
            self.root,
            text="Hint: Connect to a server by providing IP, port, and username first. "
                 "Then you can upload, view, download, or delete files.",
            fg="red",
            wraplength=500,
            justify="left"
        )
        self.hint_label.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        # Add buttons
        self.button_frame = tk.Frame(self.root)
        self.button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        self.button_frame.columnconfigure(0, weight=1)

        self.connect_button = tk.Button(self.button_frame, text="Connect to Server", command=self.connect_to_server)
        self.connect_button.grid(row=0, column=0, padx=5)

        self.upload_button = tk.Button(self.button_frame, text="Upload File", command=self.upload_file, state=tk.DISABLED)
        self.upload_button.grid(row=0, column=1, padx=5)

        self.list_button = tk.Button(self.button_frame, text="List Files", command=self.list_files, state=tk.DISABLED)
        self.list_button.grid(row=0, column=2, padx=5)

        self.download_button = tk.Button(self.button_frame, text="Download File", command=self.download_file, state=tk.DISABLED)
        self.download_button.grid(row=0, column=3, padx=5)

        self.delete_button = tk.Button(self.button_frame, text="Delete File", command=self.delete_file, state=tk.DISABLED)
        self.delete_button.grid(row=0, column=4, padx=5)

        self.client_socket = None
        self.username = None


    # a log box that is responsive to size changes, 
    # has selectable text and 
    # wraps long messages
    def log(self, message):
        self.log_box.configure(state="normal")  # Enable editing temporarily
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)  # Scroll to the latest message
        self.log_box.configure(state="disabled")  # Make it read-only again

    # a single pop-up window for connection with 3 fields to complete
    def connect_to_server(self):
        def submit_details():
            server_ip = ip_entry.get().strip()
            server_port = port_entry.get().strip()
            username = username_entry.get().strip()

            # in case the user forgets to fill the mandatory fields
            if not server_ip or not server_port or not username:
                messagebox.showerror("Error", "All fields are required!")
                return

            try:
                server_port = int(server_port)
            except ValueError:
                messagebox.showerror("Error", "Port must be a number!")
                return

            connection_window.destroy()
            self.username = username

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
                    self.log(f"1]-> Connected to server as {self.username}!\n")
                    
                    # user should now be able to use the 4 main buttons
                    self.enable_buttons()

                    # the new hint must inform the client about how they can close the GUI
                    self.update_hint(
                        "NOTE: In order to close this GUI, press the 'close' button of the app's window.",
                        "gray"
                    )

                    # begin the thread to listen for incoming messages
                    threading.Thread(target=self.listen_for_notifications, daemon=True).start()
            except Exception as e:
                self.log(f"!!! Error connecting to server: {e} !!!\n")
                self.client_socket = None

        # Create a new window for connection details
        connection_window = tk.Toplevel(self.root)
        connection_window.title("Connect to Server")
        connection_window.geometry("350x250")
        connection_window.resizable(True, True)

        # Add input fields
        tk.Label(connection_window, text="Server IP:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ip_entry = tk.Entry(connection_window)
        ip_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(connection_window, text="Server Port:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        port_entry = tk.Entry(connection_window)
        port_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        tk.Label(connection_window, text="Username:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        username_entry = tk.Entry(connection_window)
        username_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Add a button to submit details
        submit_button = tk.Button(connection_window, text="Connect", command=submit_details)
        submit_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Adjust grid to be responsive
        connection_window.columnconfigure(1, weight=1)
        connection_window.bind("<Return>", lambda event: submit_details())


    # to update the hint label's content and color
    def update_hint(self, new_text, new_color):
        self.hint_label.config(text=new_text, fg=new_color)

    def listen_for_notifications(self):
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                self.log(data.decode())
            except Exception as e:
                self.log(f"\n !!! Error: {e} !!!")
                break

    def enable_buttons(self):
        self.upload_button.config(state=tk.NORMAL)
        self.list_button.config(state=tk.NORMAL)
        self.download_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            command = {"type": "upload", "filename": filename, "content": content}
            self.send_with_size(self.client_socket, command)
            self.log(f"Uploaded file: {filename}")
        except Exception as e:
            self.log(f"\n!!! Error uploading file: {e} !!!")

    def list_files(self):
        try:
            command = {"type": "list"}
            self.send_with_size(self.client_socket, command)
            file_list = self.recv_all(self.client_socket)
            self.log("\n") # for better visuals
            self.log("Files on server:")
            for file in file_list:
                # since we don't care about the server's naming convention,
                # remove the part before the first underscore
                self.log(f"> Name: {file['filename'].split('_', 1)[1]}  |  Owner: {file['owner']}")
        except Exception as e:
            self.log(f"Error listing files: {e}")

    def delete_file(self):
        filename = tk.simpledialog.askstring("Input", "Enter the filename to delete:")
        if not filename:
            return

        try:
            command = {"type": "delete", "filename": filename}
            self.send_with_size(self.client_socket, command)
            response = self.recv_all(self.client_socket)
            self.log(response.get("message", "File deleted successfully."))
        except Exception as e:
            self.log(f"Error deleting file: {e}")

    def download_file(self):
        filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
        owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
        if not filename or not owner:
            return

        try:
            command = {"type": "download", "filename": filename, "owner": owner}
            self.send_with_size(self.client_socket, command)
            response = self.recv_all(self.client_socket)

            if response["status"] == "SUCCESS":
                save_path = filedialog.asksaveasfilename()
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(response["content"])
                    self.log(f"File downloaded: {filename}")
            else:
                self.log(f"Error: {response['message']}")
        except Exception as e:
            self.log(f"Error downloading file: {e}")

    def run(self):
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
    client = ClientGUI()
    client.run()
