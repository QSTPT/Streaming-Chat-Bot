1) await = "Pause this function, but unblock the server".
- Current Function: It pauses execution of the current function right at that line. The next lines in this same function will not run until the awaited task completes.

2) Server (Event Loop): While this line is waiting on slow I/O (like Groq's API or a network response), it releases control back to the server.
- Python says: "I'm waiting on data here. Go handle other users or other WebSocket connections in the meantime!"

3) async def = "This function is capable of pausing"
- Simply putting async def on a function does not automatically run it in the background. It just marks the function so Python knows it contains non-blocking operations and can yield control when awaited.

4) asyncio.create_task() = "Run in background and move to the next line immediately"
