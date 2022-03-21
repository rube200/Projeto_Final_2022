import socket
 
s = socket.socket()         
 
s.bind(('0.0.0.0', 45000))
s.listen(5)

print("waiting clients")
while True:
    print("accepting...")
    client, addr = s.accept()
    print("accepted")
    print(client)
    print(addr)

    while True:
        content = client.recv(32)
 
        if content:
            print(content)
        else:
            break
 
    print("Closing connection")
    client.close()