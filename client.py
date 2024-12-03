# V3

# port: 127.0.0.1

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
        self.log_box.insert(tk.END, message)
        self.log_box.yview(tk.END)

    def connect_to_server(self):
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
            self.log(f"Error uploading file: {e}")



    def list_files(self):
        try:
            command = {"type": "list"}
            self.send_with_size(self.client_socket, command)
            
            # Debug: Check raw response from the server
            raw_response = self.recv_all(self.client_socket)
            print(f"DEBUG - Raw server response for 'list_files': {raw_response}")
            
            # Expecting a dictionary with a 'files' key
            if not isinstance(raw_response, dict) or "files" not in raw_response:
                raise ValueError(f"Unexpected response format: {raw_response}")
            
            file_list = raw_response["files"]
            
            # Ensure file_list is a list of dictionaries
            if not isinstance(file_list, list) or not all(isinstance(f, dict) for f in file_list):
                raise ValueError(f"Invalid 'files' data structure: {file_list}")
            
            self.log("Files on server:")
            for file in file_list:
                self.log(f"{file['filename']} (Owner: {file['owner']})")
        except Exception as e:
            self.log(f"Error listing files: {e}")
            print(f"DEBUG - Exception in 'list_files': {e}")

    # old method
    # def list_files(self):
    #     try:
    #         command = {"type": "list"}
    #         self.send_with_size(self.client_socket, command)
    #         file_list = self.recv_all(self.client_socket)

    #         self.log("Files on server:")
    #         for file in file_list:
    #             self.log(f"{file['filename']} (Owner: {file['owner']})")
    #     except Exception as e:
    #         self.log(f"Error listing files: {e}")

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
            
            # Debug: Check raw response from the server
            raw_response = self.recv_all(self.client_socket)
            print(f"DEBUG - Raw server response for 'download_file': {raw_response}")
            
            # Expecting a dictionary with 'status' and optionally 'content'
            if not isinstance(raw_response, dict) or "status" not in raw_response:
                raise ValueError(f"Unexpected response format: {raw_response}")
            
            if raw_response["status"] == "SUCCESS":
                if "content" not in raw_response:
                    raise ValueError("Missing 'content' in SUCCESS response")
                
                save_path = filedialog.asksaveasfilename()
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(raw_response["content"])
                    self.log(f"File downloaded: {filename}")
            else:
                self.log(f"Error: {raw_response.get('message', 'Unknown error')}")
        except Exception as e:
            self.log(f"Error downloading file: {e}")
            print(f"DEBUG - Exception in 'download_file': {e}")

    # def download_file(self):
    #     filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
    #     owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
    #     if not filename or not owner:
    #         return

    #     try:
    #         command = {"type": "download", "filename": filename, "owner": owner}
    #         self.send_with_size(self.client_socket, command)
    #         response = self.recv_all(self.client_socket)

    #         if response["status"] == "SUCCESS":
    #             save_path = filedialog.asksaveasfilename()
    #             if save_path:
    #                 with open(save_path, 'wb') as f:
    #                     f.write(response["content"])
    #                 self.log(f"File downloaded: {filename}")
    #         else:
    #             self.log(f"Error: {response['message']}")
    #     except Exception as e:
    #         self.log(f"Error downloading file: {e}")

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


# """
# Local Host: 127.0.0.1
# """

# import chardet
# import socket
# import threading
# import tkinter as tk
# from tkinter import filedialog, messagebox
# import pickle
# import os

# class ClientGUI:
#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title("Client")
#         self.log_box = tk.Listbox(self.root, width=80, height=20)
#         self.log_box.pack()
#         self.connect_button = tk.Button(self.root, text="Connect to Server", command=self.connect_to_server)
#         self.connect_button.pack()
#         self.upload_button = tk.Button(self.root, text="Upload File", command=self.upload_file, state=tk.DISABLED)
#         self.upload_button.pack()
#         self.list_button = tk.Button(self.root, text="List Files", command=self.list_files, state=tk.DISABLED)
#         self.list_button.pack()
#         self.download_button = tk.Button(self.root, text="Download File", command=self.download_file, state=tk.DISABLED)
#         self.download_button.pack()
#         self.delete_button = tk.Button(self.root, text="Delete File", command=self.delete_file, state=tk.DISABLED)
#         self.delete_button.pack()
#         self.disconnect_button = tk.Button(self.root, text="Disconnect", command=self.disconnect_from_server, state=tk.DISABLED)
#         self.disconnect_button.pack()

#         self.client_socket = None
#         self.username = None

#     def log(self, message):
#         """Log messages to the client GUI."""
#         self.log_box.insert(tk.END, message)
#         self.log_box.yview(tk.END)

#     def connect_to_server(self):
#         """Connect to the server."""
#         server_ip = tk.simpledialog.askstring("Input", "Enter server IP:")
#         server_port = tk.simpledialog.askinteger("Input", "Enter server port:")
#         self.username = tk.simpledialog.askstring("Input", "Enter your username:")

#         if not server_ip or not server_port or not self.username:
#             messagebox.showerror("Error", "All fields are required!")
#             return

#         self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         try:
#             self.client_socket.connect((server_ip, server_port))
#             self.client_socket.sendall(self.username.encode())
#             response = self.client_socket.recv(1024).decode()
#             if "ERROR" in response:
#                 self.log(response)
#                 self.client_socket.close()
#                 self.client_socket = None
#             else:
#                 self.log(f"Connected to server as {self.username}")
#                 self.enable_buttons()
#                 threading.Thread(target=self.listen_for_notifications, daemon=True).start()
#         except Exception as e:
#             self.log(f"Error connecting to server: {e}")
#             self.client_socket = None

#     # new code
#     def listen_for_notifications(self):
#         """Listen for server notifications."""
#         while True:
#             try:
#                 data = self.client_socket.recv(4096)
#                 if not data:
#                     break
#                 try:
#                     message = data.decode('utf-8')  # Attempt to decode as UTF-8
#                     self.log(message)
#                 except UnicodeDecodeError:
#                     self.log("Received non-UTF-8 data from the server.")
#             except Exception as e:
#                 self.log(f"Error: {e}")
#                 break


#     # error: maybe it fails to decode server messages because of error handling
#     # def listen_for_notifications(self):
#     #     """Listen for server notifications."""
#     #     while True:
#     #         try:
#     #             data = self.client_socket.recv(4096)
#     #             if not data:
#     #                 break
#     #             self.log(data.decode())
#     #         except Exception as e:
#     #             self.log(f"Error: {e}")
#     #             break

#     def enable_buttons(self):
#         """Enable buttons after successful connection."""
#         self.upload_button.config(state=tk.NORMAL)
#         self.list_button.config(state=tk.NORMAL)
#         self.download_button.config(state=tk.NORMAL)
#         self.delete_button.config(state=tk.NORMAL)
#         self.disconnect_button.config(state=tk.NORMAL)

#     def disconnect_from_server(self):
#         """Disconnect from the server and close the GUI."""
#         if self.client_socket:
#             try:
#                 self.client_socket.sendall(b"DISCONNECT")  # Send a disconnect signal to the server
#                 self.client_socket.close()
#                 self.log("Disconnected from server.")
#             except Exception as e:
#                 self.log(f"Error during disconnection: {e}")
#             finally:
#                 self.client_socket = None

#         self.root.destroy()  # Close the Tkinter GUI window

#     # new code
#     def upload_file(self):
#         """Upload a file to the server."""
#         file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
#         if not file_path:
#             return

#         filename = os.path.basename(file_path)
#         try:
#             with open(file_path, 'rb') as f:
#                 file_size = os.path.getsize(file_path)
#                 command = {"type": "upload", "filename": filename, "size": file_size}
#                 self.client_socket.sendall(pickle.dumps(command))  # Send metadata

#                 # Send file in chunks
#                 while chunk := f.read(4096):
#                     self.client_socket.sendall(chunk)
            
#             self.log(f"Uploaded file: {filename}")
#         except Exception as e:
#             self.log(f"Error uploading file: {e}")



#     # def upload_file(self):
#     #     """Upload a file to the server."""
#     #     file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
#     #     if not file_path:
#     #         return

#     #     filename = os.path.basename(file_path)
#     #     try:
#     #         with open(file_path, 'r', encoding='utf-8') as f:
#     #             content = f.read()  # Read the file as text

#     #         command = {"type": "upload", "filename": filename, "content": content.encode('utf-8')}
#     #         self.client_socket.sendall(pickle.dumps(command))
#     #         self.log(f"Uploaded file: {filename}")
#     #     except UnicodeDecodeError as e:
#     #         self.log(f"Error: Could not read the file. Ensure it is UTF-8 encoded: {e}")
#     #     except Exception as e:
#     #         self.log(f"Error uploading file: {e}")


#     # error: perhaps it screws up encoding
#     # def upload_file(self):
#     #     """Upload a file to the server."""
#     #     file_path = filedialog.askopenfilename()
#     #     if not file_path:
#     #         return

#     #     filename = os.path.basename(file_path)
#     #     try:
#     #         with open(file_path, 'rb') as f:
#     #             content = f.read()

#     #         command = {"type": "upload", "filename": filename, "content": content}
#     #         self.client_socket.sendall(pickle.dumps(command))
#     #         self.log(f"Uploaded file: {filename}")
#     #     except Exception as e:
#     #         self.log(f"Error uploading file: {e}")

#     # new code

#     def list_files(self):
#         """Request the list of files from the server in a separate thread."""
#         threading.Thread(target=self._list_files_thread, daemon=True).start()

#     def _list_files_thread(self):
#         """Threaded function to request and display the list of files."""
#         try:
#             command = {"type": "list"}
#             self.client_socket.sendall(pickle.dumps(command))  # Send the request
#             data = self.client_socket.recv(4096)  # Receive the response
#             file_list = pickle.loads(data)  # Deserialize the response
#             self.log("Files on server:")
#             for file in file_list:
#                 self.log(f"{file['filename']} (Owner: {file['owner']})")
#         except Exception as e:
#             self.log(f"Error retrieving file list: {e}")




#     # previous code caused freezing
#     # reason: The freezing issue likely stems from the client GUI's "list files" functionality not being handled in a separate thread. 
#     # ... When a client sends the "list files" request to the server, it waits for the response, 
#     # ... but this operation blocks the GUI event loop, causing the window to freeze.
    
#     # def list_files(self):
#     #     """Request the list of files from the server."""
#     #     command = {"type": "list"}
#     #     self.client_socket.sendall(pickle.dumps(command))
#     #     data = self.client_socket.recv(4096)
#     #     file_list = pickle.loads(data)
#     #     self.log("Files on server:")
#     #     for file in file_list:
#     #         self.log(f"{file['filename']} (Owner: {file['owner']})")

#     def delete_file(self):
#         """Delete a file on the server."""
#         filename = tk.simpledialog.askstring("Input", "Enter the filename to delete:")
#         if not filename:
#             return

#         command = {"type": "delete", "filename": filename}
#         self.client_socket.sendall(pickle.dumps(command))
#         self.log(f"Requested to delete file: {filename}")


#     # new code
#     def download_file(self):
#         """Download a file from the server."""
#         filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
#         owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
#         if not filename or not owner:
#             return

#         command = {"type": "download", "filename": filename, "owner": owner}
#         self.client_socket.sendall(pickle.dumps(command))

#         # Receive metadata first
#         metadata = self.client_socket.recv(4096)
#         response = pickle.loads(metadata)
#         if response["status"] == "SUCCESS":
#             save_path = filedialog.asksaveasfilename(filetypes=[("Text files", "*.txt")])
#             if save_path:
#                 file_size = response["size"]
#                 received_size = 0
#                 with open(save_path, 'wb') as f:
#                     while received_size < file_size:
#                         chunk = self.client_socket.recv(4096)
#                         if not chunk:
#                             break
#                         f.write(chunk)
#                         received_size += len(chunk)
#                 self.log(f"File downloaded: {filename}")
#         else:
#             self.log("Error: File not found.")

#     # def download_file(self):
#     #     """Download a file from the server."""
#     #     filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
#     #     owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
#     #     if not filename or not owner:
#     #         return

#     #     command = {"type": "download", "filename": filename, "owner": owner}
#     #     self.client_socket.sendall(pickle.dumps(command))
#     #     data = self.client_socket.recv(4096)
#     #     response = pickle.loads(data)
#     #     if response["status"] == "SUCCESS":
#     #         save_path = filedialog.asksaveasfilename(filetypes=[("Text files", "*.txt")])
#     #         if save_path:
#     #             try:
#     #                 with open(save_path, 'w', encoding='utf-8') as f:
#     #                     f.write(response["content"].decode('utf-8'))  # Save the file as UTF-8
#     #                 self.log(f"File downloaded: {filename}")
#     #             except UnicodeDecodeError as e:
#     #                 self.log(f"Error: Could not save the file. Invalid encoding: {e}")
#     #     else:
#     #         self.log("Error: File not found.")

#     # error: maybe when a file is downloaded, it's not decoded properly
#     # def download_file(self):
#     #     """Download a file from the server."""
#     #     filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
#     #     owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
#     #     if not filename or not owner:
#     #         return

#     #     command = {"type": "download", "filename": filename, "owner": owner}
#     #     self.client_socket.sendall(pickle.dumps(command))
#     #     data = self.client_socket.recv(4096)
#     #     response = pickle.loads(data)
#     #     if response["status"] == "SUCCESS":
#     #         save_path = filedialog.asksaveasfilename()
#     #         if save_path:
#     #             with open(save_path, 'wb') as f:
#     #                 f.write(response["content"])
#     #             self.log(f"File downloaded: {filename}")
#     #     else:
#     #         self.log("Error: File not found.")

#     def run(self):
#         """Run the client GUI."""
#         self.root.mainloop()

# if __name__ == "__main__":
#     client = ClientGUI()
#     client.run()
