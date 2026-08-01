# What is this project?

**Streaming Chat Bot** made with fast-api and <ins>Websocket</ins>.

All **Chats** and Messages are saved. Including *Token Usage* in **each chat**.

**Token Usage Limit** is also set.

> ⚠️ Under Active development

#

### Want to read Architecture of the app?
- Install **Excalidraw extension** via <ins>your IDE</ins>
- Open `excalidraw` folder and read the files.

#

### Why not SSE instead of Websocket?
SSE is made for one line communication, user can't send events when Ai is mid response; which means no `Stop Generating` which is **bad**.
