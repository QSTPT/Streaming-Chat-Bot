from sqlalchemy import literal_column, union_all
from app.database.engine import Session
from app.database.models import UserMessage, AssistantMessage

def get_chat_history_db(db:Session, chat_id: int):
    # Select user messages with a fixed 'role' column
    q_user = db.query(
        UserMessage.id.label("id"),
        literal_column("'user'").label("role"),
        UserMessage.content.label("content"),
        UserMessage.created_at.label("created_at")
    ).filter(UserMessage.chat_id == chat_id)

    # Select assistant messages with a fixed 'role' column
    q_assistant = db.query(
        AssistantMessage.id.label("id"),
        literal_column("'assistant'").label("role"),
        AssistantMessage.content.label("content"),
        AssistantMessage.created_at.label("created_at")
    ).filter(AssistantMessage.chat_id == chat_id)

    # Union the queries and order by time
    combined_query = union_all(q_user, q_assistant).alias("chat_feed")
    
    results = (
        db.query(combined_query)
        .order_by(combined_query.c.created_at.asc())
        .all()
    )

    return results