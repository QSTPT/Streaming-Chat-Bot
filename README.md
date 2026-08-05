<img width="600" height="321" alt="output" src="https://github.com/user-attachments/assets/054699ff-2f73-4f4e-82d6-6e2e2546cdd7" />

#

### What is this project?

**Streaming Chat Bot** made with fast-api and <ins>Websocket</ins>.

**This project is a demo version, there are many bugs inside it. based on each phase my skills will grow and i will become better.**

> ☑️ Demo Mode Completed.

#

### What are the fundamentals?
- You can <ins>choose</ins> a model based on your preference.
- the LLM has been called in streaming mode
- **Websocket** has been used for this chat-bot; so you can send events
- each chat session is **stored** inside <ins>postgresql</ins>, including **messages**.
- temperature, max_token, stop_sequence has been set.
- Token Usage per conversation is **tracked**. 
- Websocket manager **Handles** Multiple users <ins>streaming at once</ins>.
- Built-in logic to handle `max Token hits`.
- a responsive Frontend.

#

### Want to read Architecture of the app?
- Install **Excalidraw extension** via <ins>your IDE</ins>
- Open `excalidraw` folder and read the files.

#

### How to install dependencies?
- clone the repo
- pip install -e .

### How to run the frontend UI?
- Start the FastAPI backend: `uvicorn app.main:app --reload`
- In a second terminal, launch the Flet app: `python -m app.ui.flet_app`

### Why not SSE instead of Websocket?
SSE is made for one line communication, user **can't** send events when Ai is mid response; which means no `Stop Generating` which is **bad**.
