import tkinter as tk
import socket
import threading

server_thread = None
server_socket = None
clients = [] # {"socket": socket, "address": address, "thread": thread, "username": username}
channel_names = ["IF 100", "SPS 101"]
channels_subscribers = [set() for i in range(len(channel_names))]
number_of_channels = len(channel_names)

def find_client_index(client_socket):
    for index, c in enumerate(clients):
        if c["socket"] == client_socket:
            return index

def is_username_taken(username):
    for c in clients:
        if("username" not in c):
            continue
        if c["username"] == username:
            return True
    return False

def log_server_action(message):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, f"{message}\n")
    log_text.config(state=tk.DISABLED)


def update_connected_clients_box():
    connected_clients_text.config(state=tk.NORMAL)
    connected_clients_text.delete(1.0, tk.END)
    for c in clients:
        if "username" in c:
            connected_clients_text.insert(tk.END, f"{c['username']}\n")
    connected_clients_text.config(state=tk.DISABLED)

def update_channel_subscribers_boxes():
    for i in range(len(channel_names)):
        channel_texts[i].config(state=tk.NORMAL)
        channel_texts[i].delete(1.0, tk.END)
        for username in channels_subscribers[i]:
            channel_texts[i].insert(tk.END, f"{username}\n")
        channel_texts[i].config(state=tk.DISABLED)

def start_server():
    global server_socket
    global server_thread

    if port_entry == "" or not port_entry.get().isdigit():
        log_server_action("Please enter a valid port number")
        return
    
    try:
        port = int(port_entry.get())
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(5)

        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, f"Server started on port {port}\n")
        log_text.config(state=tk.DISABLED)

        port_entry.config(state=tk.DISABLED)

        server_thread = threading.Thread(target=accept_connections, daemon=True)
        server_thread.start()

        start_stop_button["text"] = "Close Server"
        start_stop_button["command"] = close_server

    except socket.error as e:
        log_server_action(f"Could not start the server on port {port}; Error: {e}")

def close_server():
    global server_socket, clients, channels_subscribers, server_thread
    log_server_action("Server closed")

    port_entry.config(state=tk.NORMAL)

    # send "close" message to all clients that the server is closing
    for client in clients:
        try:
            client["socket"].send("closed".encode())
        except socket.error as e:
            log_server_action(f"Could not send <closed> message to {client['address']}; Error: {e}")

    for client in clients:
        client["socket"].close()

    clients = []
    channels_subscribers = [set() for i in range(len(channel_names))]
    update_connected_clients_box()
    update_channel_subscribers_boxes()


    if server_socket:
        server_socket.close()


    start_stop_button["text"] = "Start Server"
    start_stop_button["command"] = start_server

def accept_connections():
    global server_socket, clients
    while True:
        try:
            client_socket, client_address = server_socket.accept()

            log_server_action(f"Connection from {client_address}")

            new_client = {"socket": client_socket, "address": client_address}
            clients.append(new_client)

            receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
            receive_thread.start()

            clients[-1]["thread"] = receive_thread
        except socket.error as e:
            print(f"Connection closed")
            break

        

def receive_messages(client_socket):
    global clients
    while client_socket in [c["socket"] for c in clients]:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            log_text.config(state=tk.NORMAL)
            log_text.insert(tk.END, f"\nReceived: {message}\n")
            log_text.config(state=tk.DISABLED)

            handle_message(client_socket, message)
        except socket.error as e:
            print(f"Connection Closed")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

def handle_message(client_socket, message):
    global connected_clients, channels_subscribers
    words = message.split()
    command = words[0]
    client_index = find_client_index(client_socket)
    the_client = clients[client_index]
    
    if command == "identify":
        try:
            username = words[1]
            if is_username_taken(username):
                connected = False
                client_socket.send("failed username taken".encode())
                clients[client_index]["socket"].close() 
                del clients[client_index]
                # raise an error to tell the client that the username is taken
                log_server_action(f"Could not identify the username; Error: Username is taken")
                raise Exception("Username is taken")
            
            clients[client_index]["username"] = username
            log_server_action(f"{username} identified")
            update_connected_clients_box()
        except socket.error as e:
            log_server_action(f"Could not identify the username; Error: {e}")

    elif command == "subscribe":
        try:
            channel_index = int(words[1])
            username = the_client["username"]
            channels_subscribers[channel_index].add(username)
            log_server_action(f"{username} subscribed to {channel_names[channel_index]}")
            update_channel_subscribers_boxes()
        except server_socket as e:
            log_server_action(f"Could not subscribe to the channel {channel_index}; Error: {e}")

    elif command == "unsubscribe":
        try:
            channel_index = int(words[1])
            username = the_client["username"]
            channels_subscribers[channel_index].remove(username)
            log_server_action(f"{username} unsubscribed from {channel_names[channel_index]}")
            update_channel_subscribers_boxes()
        except Exception as e:
            log_server_action(f"Could not unsubscribe from the channel {channel_index}; Error: {e}")

    elif command == "message":
        try:
            channel_index = int(words[1])
            username = the_client["username"]
            message_text = " ".join(words[2:])
            if username in channels_subscribers[channel_index]:
                send_message_to_channel(username, channel_index, message_text)

            log_server_action(f"{username} sent '{message_text}' to {channel_names[channel_index]}")
                
        except socket.error as e:
            print(f"Could not send the message to the channel {channel_index}; Error: {e}")
    
    elif command == "disconnect":
        try:
            if("username" in the_client):
                username = the_client["username"]
                
                for i in range(len(channel_names)):
                    if(username in channels_subscribers[i]):
                        channels_subscribers[i].remove(username)
                        log_server_action(f"unsubscribed {username} from {channel_names[i]}")
                    
                # clients[client_index]["socket"].close()
                # clients[client_index]["thread"].join()
                del clients[client_index]

                log_server_action(f"{username} disconnected")
            update_channel_subscribers_boxes()
            update_connected_clients_box()

        except socket.error as e:
            print(f"Could not disconnect the client; Error: {e}")

def send_message_to_channel(username, channel_index, message):
    global clients
    for client in clients:
        try:
            if "username" not in client:
                continue
            if client["username"] in channels_subscribers[channel_index]:
                client["socket"].send(f"message {username} {channel_index} {message}".encode())
        except socket.error as e:
            print(f"Error sending {username} message to channel {channel_index}: {e}")

def on_exit():
    close_server()
    root.quit()


connected_clients = []

# Create the main window
root = tk.Tk()
root.title("Chat Server")


server_frame = tk.LabelFrame(root, text="Start/Stop Server", padx=10, pady=10)
server_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
server_frame.grid_columnconfigure(1, weight=1)

port_label = tk.Label(server_frame, text="Port:")
port_label.grid(row=0, column=0)
port_entry = tk.Entry(server_frame)
port_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
port_entry.insert(0, "1234")

start_stop_button = tk.Button(server_frame, text="Start Server", command=start_server)
start_stop_button.grid(row=0, column=2, sticky="e")

# Server Actions
logs_frame = tk.LabelFrame(root, text="Logs", padx=10, pady=10)
logs_frame.grid(row=1, column=0, rowspan=3, sticky="nsew", padx=10, pady=10)
log_text = tk.Text(logs_frame, state=tk.DISABLED, wrap=tk.WORD, width=40, height=10 * (number_of_channels + 1))
log_text.pack(fill=tk.BOTH, expand=True)

# Connected Clients
connected_clients_frame = tk.LabelFrame(root, text="Connected Clients", padx=10, pady=10)
connected_clients_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
connected_clients_text = tk.Text(connected_clients_frame, state=tk.DISABLED, wrap=tk.WORD, width=20, height=10)
connected_clients_text.pack()

channel_frames = []
channel_texts = []
for i, channel in enumerate(channel_names):
    # Create a frame for the channel
    channel_frame = tk.LabelFrame(root, text=channel, padx=10, pady=10)
    channel_frame.grid(row=i + 2, column=1, sticky="nsew", padx=10, pady=10)
    channel_frames.append(channel_frame)

    # Create a text box for the channel
    channel_text = tk.Text(channel_frame, state=tk.DISABLED, wrap=tk.WORD, width=20, height=10)
    channel_text.pack()
    channel_texts.append(channel_text)


# close_button = tk.Button(root, text="Close Server", command=close_server)
# close_button.pack()


root.protocol("WM_DELETE_WINDOW", on_exit)
root.mainloop()

# # V3

# # port: 127.0.0.1

# import socket
# import threading
# import tkinter as tk
# from tkinter import filedialog, messagebox
# import os
# import pickle

# class ServerGUI:
#     def __init__(self):
#         self.root = tk.Tk()
#         self.root.title("Server")
#         self.log_box = tk.Listbox(self.root, width=80, height=20)
#         self.log_box.pack()

#         self.start_button = tk.Button(self.root, text="Start Server", command=self.start_server)
#         self.start_button.pack()
#         self.select_dir_button = tk.Button(self.root, text="Select Directory", command=self.select_directory)
#         self.select_dir_button.pack()

#         self.server_socket = None
#         self.client_threads = []
#         self.files_dir = None
#         self.clients = {}
#         self.file_owners = {}
#         self.running = True

#         # Persist file metadata
#         self.metadata_file = "file_metadata.pkl"
#         # self.load_metadata()

#     def log(self, message):
#         self.log_box.insert(tk.END, message)
#         self.log_box.yview(tk.END)

#     def select_directory(self):
#         self.files_dir = filedialog.askdirectory()
#         if self.files_dir:
#             self.log(f"Files directory set to: {self.files_dir}")

#     def start_server(self):
#         if not self.files_dir:
#             messagebox.showerror("Error", "Select a directory first!")
#             return

#         self.port = tk.simpledialog.askinteger("Input", "Enter server port:")
#         if not self.port:
#             return

#         self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.server_socket.bind(('', self.port))
#         self.server_socket.listen(5)
#         self.log(f"Server started on port {self.port}")

#         threading.Thread(target=self.accept_clients, daemon=True).start()

#     def accept_clients(self):
#         while self.running:
#             try:
#                 client_socket, addr = self.server_socket.accept()
#                 self.log(f"Connection attempt from {addr}")
#                 client_thread = threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True)
#                 self.client_threads.append(client_thread)
#                 client_thread.start()
#             except Exception as e:
#                 self.log(f"Error accepting client: {e}")
#                 break

#     def handle_client(self, client_socket):
#         try:
#             client_name = client_socket.recv(1024).decode()
#             if client_name in self.clients:
#                 client_socket.sendall(b"ERROR: Name already in use.")
#                 client_socket.close()
#                 return

#             self.clients[client_name] = client_socket
#             self.log(f"Client connected: {client_name}")
#             client_socket.sendall(b"CONNECTED")

#             while self.running:
#                 command = self.recv_all(client_socket)
#                 if not command:
#                     break

#                 if command["type"] == "upload":
#                     self.handle_upload(client_name, command, client_socket)
#                 elif command["type"] == "list":
#                     self.handle_list(client_socket)
#                 elif command["type"] == "delete":
#                     self.handle_delete(client_name, command, client_socket)
#                 elif command["type"] == "download":
#                     self.handle_download(command, client_socket)
#         except Exception as e:
#             self.log(f"Error handling client: {e}")
#         finally:
#             if client_name in self.clients:
#                 del self.clients[client_name]
#             client_socket.close()
#             self.log(f"Client disconnected: {client_name}")

#     def handle_upload(self, client_name, command, client_socket):
#         try:
#             filename = f"{client_name}_{command['filename']}"
#             filepath = os.path.join(self.files_dir, filename)
#             with open(filepath, 'wb') as f:
#                 f.write(command['content'])
#             self.file_owners[filename] = client_name
#             self.log(f"File uploaded: {filename} by {client_name}")
#             # self.save_metadata()
#             self.send_with_size(client_socket, {"status": "UPLOAD_SUCCESS"})
#         except Exception as e:
#             self.log(f"Error handling file upload: {e}")
#             self.send_with_size(client_socket, {"status": "UPLOAD_FAILED"})


#     # BUG: The problem where certain actions (like listing or downloading) fail the first time but 
#     # succeed the second time could be due to race conditions or 
#     # the order in which data is processed or cached.
#     def handle_list(self, client_socket):
#         # ensure that the file metadata is correctly updated and sent
#         try:
#             # Ensure the metadata is up-to-date
#             # self.load_metadata()  # Re-load metadata to avoid stale data
#             file_list = [{"filename": f, "owner": o} for f, o in self.file_owners.items()]
#             self.send_with_size(client_socket, {"files": file_list})
#         except Exception as e:
#             self.send_with_size(client_socket, {"status": "ERROR", "message": f"Error listing files: {e}"})
#             self.log(f"Error listing files: {e}")

#     def handle_delete(self, client_name, command, client_socket):
#         filename = f"{client_name}_{command['filename']}"
#         filepath = os.path.join(self.files_dir, filename)
#         if os.path.exists(filepath):
#             os.remove(filepath)
#             del self.file_owners[filename]
#             # self.save_metadata()
#             self.log(f"File deleted: {filename}")
#             self.send_with_size(client_socket, {"status": "DELETE_SUCCESS"})
#         else:
#             self.send_with_size(client_socket, {"status": "ERROR", "message": "File not found."})

#     def handle_download(self, command, client_socket):
#         filename = f"{command['owner']}_{command['filename']}"
#         filepath = os.path.join(self.files_dir, filename)
#         if os.path.exists(filepath):
#             with open(filepath, 'rb') as f:
#                 file_content = f.read()
#             # self.send_with_size(client_socket, {"status": "SUCCESS", "content": file_content})
#             self.send_with_size(client_socket, {"status": "SUCCESS", "content": file_content})
#         else:
#             self.send_with_size(client_socket, {"status": "ERROR", "message": "File not found."})

#     # def load_metadata(self):
#     #     # to handle an empty or stale file metadata file
#     #     if os.path.exists(self.metadata_file):
#     #         try:
#     #             with open(self.metadata_file, 'rb') as f:
#     #                 self.file_owners = pickle.load(f)
#     #         except Exception as e:
#     #             self.log(f"Error loading metadata: {e}")
#     #             self.file_owners = {}
#     #     else:
#     #         self.file_owners = {}

#     # def save_metadata(self):
#     #     with open(self.metadata_file, 'wb') as f:
#     #         pickle.dump(self.file_owners, f)

#     def shutdown(self):
#         self.running = False
#         if self.server_socket:
#             self.server_socket.close()
#         for thread in self.client_threads:
#             thread.join()
#         # self.save_metadata()
#         self.log("Server shut down.")

#     def run(self):
#         self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
#         self.root.mainloop()

#     def send_with_size(self, sock, data):
#         """Send data with its size prepended."""
#         serialized_data = pickle.dumps(data)
#         data_length = len(serialized_data)
#         sock.sendall(f"{data_length:<10}".encode())  # Send length as a fixed-width 10-character string
#         sock.sendall(serialized_data)

#     def recv_all(self, sock):
#         """Receive all data from the socket."""
#         data_length = int(sock.recv(10).decode().strip())  # Read the size of the incoming data
#         data = b""
#         while len(data) < data_length:
#             packet = sock.recv(4096)
#             if not packet:
#                 break
#             data += packet
#         return pickle.loads(data)

# if __name__ == "__main__":
#     server = ServerGUI()
#     server.run()
