# What is this project?

**Streaming Chat Bot** made with fast-api and <ins>Websocket</ins>.

> ⚠️ Under Active development

#

### What are the fundamentals?
- You can choose a model based on your preference.
- the LLM has been called in streaming mode
- Websocket has been used for this chat-bot; so you can send events
- each chat session is stored inside postgresql, including messages.
- temperature, max_token, stop_sequence has been set.

#

### Later on:
- Token Usage per conversation will be tracked.
- Redis will be added for using chats and postgres for older chats.
- handle production concerns.
- add a responsive Frontend.
- use fixed-sized seed to debug

#

### What are the Productivity Concerns?
- What happens if the connection drops mid-stream?
- What happens when max_token is hit?
- Concurrency: Multiple users streaming at once?

#

### Want to read Architecture of the app?
- Install **Excalidraw extension** via <ins>your IDE</ins>
- Open `excalidraw` folder and read the files.

#

### Why not SSE instead of Websocket?
SSE is made for one line communication, user **can't** send events when Ai is mid response; which means no `Stop Generating` which is **bad**.
