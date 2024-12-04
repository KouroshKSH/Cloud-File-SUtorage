import tkinter as tk
import socket
import threading

connected = False
terminating = False
client_socket = None  # Initialize client_socket

def insert_to_logs(message):
    logs.config(state=tk.NORMAL)
    logs.insert(tk.END, f"{message}\n")
    logs.config(state=tk.DISABLED)

def connect():
    global client_socket, connected, receive_thread
    ip = ip_entry.get()
    port_num = int(port_entry.get())

    username = username_entry.get()
    if username == "":
        insert_to_logs("Please enter a username")
        return
    
    if port_entry == "" or not port_entry.get().isdigit():
        insert_to_logs("Please enter a valid port number")
        return
    
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, port_num))

        connected = True
        insert_to_logs(f"Connected to the server at {ip}:{port_num}\n")

        identify()
        insert_to_logs(f"Identifiying the username as {username}")

        # set buttons' states
        connect_button["text"] = "Disconnect"
        connect_button["command"] = disconnect
        
        for channel in channels:
            channel["subscribe_button"]["state"] = "normal"

        server_status_info.config(state=tk.NORMAL)
        server_status_info.delete(0, "end") 
        server_status_info.insert(0, "connected ✅") 
        server_status_info.config(state=tk.DISABLED)

        ip_entry.config(state=tk.DISABLED)
        port_entry.config(state=tk.DISABLED)
        username_entry.config(state=tk.DISABLED)


        

        # Start a thread to listen for incoming messages
        receive_thread = threading.Thread(target=receive_messages, daemon=True)
        receive_thread.start()

    except socket.error as e:
        connected = False
        server_status_info.config(state=tk.NORMAL)
        server_status_info.delete(0, "end")  
        server_status_info.insert(0, "Could not connect ❌")  
        server_status_info.config(state=tk.DISABLED)
        insert_to_logs(f"Could not connect to the server; Error: {e}")

def disconnect():
    global client_socket, connected, receive_thread
    if connected:
        connected = False
        client_socket.send(f"disconnect".encode())
        # receive_thread.join()   
        client_socket.close()
        insert_to_logs("Disconnected from the server\n")
        

    connect_button["text"] = "Connect"
    connect_button["command"] = connect

    ip_entry.config(state=tk.NORMAL)
    port_entry.config(state=tk.NORMAL)
    username_entry.config(state=tk.NORMAL)


    
    server_status_info.config(state=tk.NORMAL)
    server_status_info.delete(0, "end") 
    server_status_info.insert(0, "not connected") 
    server_status_info.config(state=tk.DISABLED)
    for channel_index in range(number_of_channels):
        channels[channel_index]["subscribe_button"]["text"] = "Subscribe"
        channels[channel_index]["subscribe_button"]["command"] = lambda channel_index=channel_index: subscribe(channel_index)
        channels[channel_index]["subscribe_button"].config(state=tk.DISABLED)

        channels[channel_index]["subscription_status"]["text"] = channels[channel_index]["subscription_status"]["text"].replace("(subscribed)", "(not subscribed)")

        channels[channel_index]["send_button"].config(state=tk.DISABLED)
        channels[channel_index]["message_entry"].config(state=tk.DISABLED)
        channels[channel_index]["messages"].config(state=tk.NORMAL)
        channels[channel_index]["messages"].delete("1.0", "end")
        channels[channel_index]["messages"].config(state=tk.DISABLED)

        
        

def identify():
    global client_socket, connected
    username = username_entry.get()
    if connected:
        try:
            client_socket.send(f"identify {username}".encode())
        except:
            connected = False
            insert_to_logs("Failed to identify\n")
            raise Exception("Failed to identify")
    else:
        insert_to_logs("Not connected to the server\n")

def subscribe(channel_id):
    global client_socket, connected

    if connected:
        try:
            channels[channel_id]["subscribe_button"]["text"] = "Unsubscribe"
            channels[channel_id]["subscribe_button"]["command"] = lambda channel_id=channel_id: unsubscribe(channel_id)

            channels[channel_id]["subscription_status"]["text"] = channels[channel_id]["subscription_status"]["text"].replace("(not subscribed)", "(subscribed)")
            
            channels[channel_id]["send_button"].config(state=tk.NORMAL)
            channels[channel_id]["message_entry"].config(state=tk.NORMAL)
            
            channels[channel_id]["messages"].config(state=tk.DISABLED)

            client_socket.send(f"subscribe {channel_id}".encode())
            insert_to_logs(f"Subscribed to channel {channel_names[channel_id]}")
        except socket.error as e:
            insert_to_logs(f"Failed to subscribe to channel {channel_names[channel_id]}\n")
    else:
        insert_to_logs("Not connected to the server\n")

def unsubscribe(channel_id):
    global client_socket, connected

    if connected:
        try:

            channels[channel_id]["subscribe_button"]["text"] = "Subscribe"
            channels[channel_id]["subscribe_button"]["command"] = lambda channel_id=channel_id: subscribe(channel_id)

            channels[channel_id]["subscription_status"]["text"] = channels[channel_id]["subscription_status"]["text"].replace("(subscribed)", "(not subscribed)")

            channels[channel_id]["send_button"].config(state=tk.DISABLED)
            channels[channel_id]["message_entry"].config(state=tk.DISABLED)

            # if the previous messages in the channel are to be deleted uncomment the following line
            # channels[channel_id]["messages"].config(state=tk.NORMAL)
            # channels[channel_id]["messages"].delete("1.0", "end")
            channels[channel_id]["messages"].config(state=tk.DISABLED)

            

            client_socket.send(f"unsubscribe {channel_id}".encode())
            insert_to_logs(f"Unsubscribed from channel {channel_names[channel_id]}")
        except socket.error as e:
            insert_to_logs(f"Failed to unsubscribe from channel {channel_names[channel_id]}\n")
    else:
        insert_to_logs("Not connected to the server\n")

def send_message(channel_index):
    global client_socket, connected
    message = channels[channel_index]["message_entry"].get()
    if connected:
        try:
            client_socket.send(f"message {channel_index} {message}".encode())
            insert_to_logs(f"Sent '{message}' to channel {channel_names[channel_index]}")
            channels[channel_index]["message_entry"].delete(0, "end")  # Clear the message_entry after sending
        except socket.error as e:
            insert_to_logs(f"Could not send message to the server; Error: {e}")
    else:
        insert_to_logs("Not connected to the server\n")

def receive_messages():
    global client_socket, connected
    while connected:
        try:
            data = client_socket.recv(1024)
            if not data:
                insert_to_logs("Connection closed by the server")
                # connected = False
                disconnect()
                break
            
            message = data.decode()
            insert_to_logs(f"\nReceived: {message}")
            handle_message(message)

        except socket.error as e:
            print(f"Connection closed")
            # connected = False
            disconnect()
            break


def handle_message(message):
    global connected
    words = message.split()
    command = words[0]
    
    if command == "message":
        username = words[1]
        channel_index = int(words[2])

        message_text = " ".join(words[3:])
        
        channels[channel_index]["messages"].config(state=tk.NORMAL)
        channels[channel_index]["messages"].insert("end", f"{username}: {message_text}\n")
        channels[channel_index]["messages"].config(state=tk.DISABLED)

    elif command == "failed":
        message_text = " ".join(words[1:])
        insert_to_logs(f"Could not connect to the server; {message_text}\n")
        connected = False
        disconnect()

    elif command == "closed":
        insert_to_logs("Connection closed by the server")
        # connected = False
        disconnect()


def on_exit():
    global connected
    if connected:
        disconnect()
    root.quit()

channel_names = ["IF 100", "SPS 101"]
number_of_channels = len(channel_names)

root = tk.Tk()
root.title("Chat Application")


for i in range(number_of_channels):
    root.grid_columnconfigure(i, weight=1)

server_connection_frame = tk.LabelFrame(root, text="Connect to Server", padx=10, pady=10)
server_connection_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10, columnspan=number_of_channels)

for i in range(4):
    server_connection_frame.grid_columnconfigure(i, weight=1)

# server_connection_frame.grid_columnconfigure(1, weight=1)
# server_connection_frame.grid_columnconfigure(3, weight=1)

ip_label = tk.Label(server_connection_frame, text="IP:")
ip_label.grid(row=0, column=0, sticky="w")
ip_entry = tk.Entry(server_connection_frame)
ip_entry.grid(row=0, column=1)

port_label = tk.Label(server_connection_frame, text="Port:")
port_label.grid(row=1, column=0, sticky="w")
port_entry = tk.Entry(server_connection_frame)
port_entry.grid(row=1, column=1)

server_status_label = tk.Label(server_connection_frame, text="Server Status:")
server_status_label.grid(row=1, column=2, sticky="w")
server_status_info = tk.Entry(server_connection_frame, state=tk.DISABLED)
server_status_info.grid(row=1, column=3)
server_status_info.insert(0, "not connected")
# server_status_info["state"] = "disabled"

username_label = tk.Label(server_connection_frame, text="Username:")
username_label.grid(row=0, column=2, sticky="w")
username_entry = tk.Entry(server_connection_frame)
username_entry.grid(row=0, column=3, sticky="ew")

# status_label = tk.Label(root, text=" Not Connected")
# status_label.grid(row=0, column=2, columnspan=2)

connect_button = tk.Button(server_connection_frame, text="Connect", command=connect)
connect_button.grid(row=2, column=0, columnspan=4, sticky="ew")



channels = [{} for _ in range(number_of_channels)]
# channels = [ tk.LabelFrame(root, text=channel_name, padx=10, pady=10) for channel_name in channel_names]
for index, channel_name in enumerate(channel_names):
    channels[index]["frame"] = tk.LabelFrame(root, text=channel_name, padx=10, pady=10)
    channels[index]["frame"].grid(row=2, column=index, sticky="ew", padx=10, pady=10)
    channels[index]["frame"].columnconfigure(0, weight=1)
    channel_frame = channels[index]["frame"]

    channels[index]["subscription_status"] = tk.Label(channel_frame, text=f"Status: (not subscribed)")
    channels[index]["subscription_status"].grid(row=0, column=0, sticky="w")

    channels[index]["subscribe_button"] = tk.Button(channel_frame, text="Subscribe", state=tk.DISABLED)
    channels[index]["subscribe_button"].grid(row=0, column=1, sticky="e")
    channels[index]["subscribe_button"]["command"] = lambda index=index: subscribe(index)
    # channels[index]["subscribe_button"]["state"] = "disabled"

    channels[index]["messages"] = tk.Text(channel_frame, width=40, state=tk.DISABLED)
    channels[index]["messages"].grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
    # channels[index]["messages"]["state"] = "disabled"

    channels[index]["message_label"] = tk.Label(channel_frame, text="Message:")
    channels[index]["message_label"].grid(row=2, column=0, sticky="w")
    channels[index]["message_entry"] = tk.Entry(channel_frame, state=tk.DISABLED)
    channels[index]["message_entry"].grid(row=3, column=0, sticky="ew", columnspan=3)
    # channels[index]["message_entry"]["state"] = "disabled"

    channels[index]["send_button"] = tk.Button(channel_frame, text="Send", command=lambda index=index: send_message(index), state=tk.DISABLED)
    channels[index]["send_button"].grid(row=4, column=1, sticky="e")
    # channels[index]["send_button"]["state"] = "disabled"
    

logs_frame = tk.LabelFrame(root, text="Logs", padx=10, pady=10)
logs_frame.grid(row=0, column=number_of_channels + 1, rowspan=3, sticky="nsew", padx=10, pady=10)
logs_frame.grid_rowconfigure(0, weight=1)


logs = tk.Text(logs_frame, width=40, state=tk.DISABLED)
logs.grid(row=0, column=0, sticky="ns", padx=0, pady=0)



ip_entry.insert(0, "127.0.0.1") 
port_entry.insert(0, "1234") 

root.protocol("WM_DELETE_WINDOW", on_exit)

root.mainloop()

# # V3

# # port: 127.0.0.1

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

#         self.client_socket = None
#         self.username = None

#     def log(self, message):
#         self.log_box.insert(tk.END, message)
#         self.log_box.yview(tk.END)

#     def connect_to_server(self):
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

#     def listen_for_notifications(self):
#         while True:
#             try:
#                 data = self.client_socket.recv(4096)
#                 if not data:
#                     break
#                 self.log(data.decode())
#             except Exception as e:
#                 self.log(f"Error: {e}")
#                 break

#     def enable_buttons(self):
#         self.upload_button.config(state=tk.NORMAL)
#         self.list_button.config(state=tk.NORMAL)
#         self.download_button.config(state=tk.NORMAL)
#         self.delete_button.config(state=tk.NORMAL)

#     def upload_file(self):
#         file_path = filedialog.askopenfilename()
#         if not file_path:
#             return

#         filename = os.path.basename(file_path)
#         try:
#             with open(file_path, 'rb') as f:
#                 content = f.read()

#             command = {"type": "upload", "filename": filename, "content": content}
#             self.send_with_size(self.client_socket, command)
#             self.log(f"Uploaded file: {filename}")
#         except Exception as e:
#             self.log(f"Error uploading file: {e}")


#     # BUG: the client is receiving the wrong response from the server. 
#     # This likely occurs because the handle_list() function isn't handling the response properly, 
#     # or the server is mistakenly sending a status message intended for another command.
   
#     def list_files(self):
#         # only expect correct responses
#         try:
#             command = {"type": "list"}
#             self.send_with_size(self.client_socket, command)

#             raw_response = self.recv_all(self.client_socket)

#             # Debug: Check raw response from the server
#             print(f"DEBUG - Raw server response for 'list_files': {raw_response}")

#             if isinstance(raw_response, dict) and "files" in raw_response:
#                 file_list = raw_response["files"]
#                 self.log(f"Files on server: {', '.join([f['filename'] for f in file_list])}")
#             else:
#                 raise ValueError(f"Unexpected response format: {raw_response}")

#         except Exception as e:
#             self.log(f"Error listing files: {e}")

#     # def list_files(self):
#     #     try:
#     #         command = {"type": "list"}
#     #         self.send_with_size(self.client_socket, command)
            
#     #         # Debug: Check raw response from the server
#     #         raw_response = self.recv_all(self.client_socket)
#     #         print(f"DEBUG - Raw server response for 'list_files': {raw_response}")
            
#     #         # Expecting a dictionary with a 'files' key
#     #         if not isinstance(raw_response, dict) or "files" not in raw_response:
#     #             raise ValueError(f"Unexpected response format: {raw_response}")
            
#     #         file_list = raw_response["files"]
            
#     #         # Ensure file_list is a list of dictionaries
#     #         if not isinstance(file_list, list) or not all(isinstance(f, dict) for f in file_list):
#     #             raise ValueError(f"Invalid 'files' data structure: {file_list}")
            
#     #         self.log("Files on server:")
#     #         for file in file_list:
#     #             self.log(f"{file['filename']} (Owner: {file['owner']})")
#     #     except Exception as e:
#     #         self.log(f"Error listing files: {e}")
#     #         print(f"DEBUG - Exception in 'list_files': {e}")

#     def delete_file(self):
#         filename = tk.simpledialog.askstring("Input", "Enter the filename to delete:")
#         if not filename:
#             return

#         try:
#             command = {"type": "delete", "filename": filename}
#             self.send_with_size(self.client_socket, command)
#             response = self.recv_all(self.client_socket)
#             self.log(response.get("message", "File deleted successfully."))
#         except Exception as e:
#             self.log(f"Error deleting file: {e}")


#     def download_file(self):
#         filename = tk.simpledialog.askstring("Input", "Enter the filename to download:")
#         owner = tk.simpledialog.askstring("Input", "Enter the file owner's username:")
#         if not filename or not owner:
#             return

#         try:
#             command = {"type": "download", "filename": filename, "owner": owner}
#             self.send_with_size(self.client_socket, command)
            
#             # Debug: Check raw response from the server
#             raw_response = self.recv_all(self.client_socket)
#             print(f"DEBUG - Raw server response for 'download_file': {raw_response}")
            
#             # Expecting a dictionary with 'status' and optionally 'content'
#             if not isinstance(raw_response, dict) or "status" not in raw_response:
#                 raise ValueError(f"Unexpected response format: {raw_response}")
            
#             if raw_response["status"] == "SUCCESS":
#                 if "content" not in raw_response:
#                     raise ValueError("Missing 'content' in SUCCESS response")
                
#                 save_path = filedialog.asksaveasfilename()
#                 if save_path:
#                     with open(save_path, 'wb') as f:
#                         f.write(raw_response["content"])
#                     self.log(f"File downloaded: {filename}")
#             else:
#                 self.log(f"Error: {raw_response.get('message', 'Unknown error')}")
#         except Exception as e:
#             self.log(f"Error downloading file: {e}")
#             print(f"DEBUG - Exception in 'download_file': {e}")

#     def run(self):
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
#     client = ClientGUI()
#     client.run()
