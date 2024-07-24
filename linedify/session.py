from datetime import datetime, timezone
from typing import List
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker


class ConversationSession:
    def __init__(self, user_id: str, conversation_id: str = None, updated_at: datetime = None) -> None:
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "updated_at": self.updated_at.isoformat()
        }

    @staticmethod
    def from_dict(data):
        return ConversationSession(
            user_id=data["user_id"],
            conversation_id=data.get("conversation_id"),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


Base = declarative_base()


class ConversationSessionModel(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    conversation_id = Column(String)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    is_expired = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("user_id", "conversation_id", name="uix_user_conversation"),)


class ConversationSessionStore:
    def __init__(self, db_url: str = "sqlite:///sessions.db", timeout: float = 3600.0) -> None:
        self.timeout = timeout
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    async def get_session(self, user_id: str) -> ConversationSession:
        if not user_id:
            raise Exception("user_id is required")

        with self.Session() as session:
            db_session = session.query(ConversationSessionModel).filter_by(user_id=user_id).order_by(ConversationSessionModel.updated_at.desc()).first()

            now = datetime.now(timezone.utc)

            if db_session is None:
                return ConversationSession(user_id)

            if db_session.is_expired:
                return ConversationSession(user_id)

            if self.timeout > 0 and (now - db_session.updated_at.replace(tzinfo=timezone.utc)).total_seconds() > self.timeout:
                return ConversationSession(user_id)

            return ConversationSession(
                user_id=db_session.user_id,
                conversation_id=db_session.conversation_id,
                updated_at=db_session.updated_at.replace(tzinfo=timezone.utc)
            )

    async def set_session(self, session: ConversationSession) -> None:
        if not session.user_id:
            raise Exception("user_id is required")

        session.updated_at = datetime.now(timezone.utc)

        with self.Session() as db_session:
            db_session_model = ConversationSessionModel(
                id=f"{session.user_id}_{session.conversation_id}",
                user_id=session.user_id,
                conversation_id=session.conversation_id,
                updated_at=session.updated_at
            )
            db_session.merge(db_session_model)
            db_session.commit()

    async def expire_session(self, user_id: str) -> None:
        if not user_id:
            raise Exception("user_id is required")

        with self.Session() as session:
            latest_session = session.query(ConversationSessionModel).filter_by(user_id=user_id).order_by(ConversationSessionModel.updated_at.desc()).first()

            if latest_session:
                latest_session.is_expired = True
                session.commit()

    async def get_user_conversations(self, user_id: str, count: int = 20) -> List[ConversationSession]:
        with self.Session() as session:
            db_sessions = session.query(ConversationSessionModel).filter_by(user_id=user_id).order_by(ConversationSessionModel.updated_at.desc()).limit(count)
            user_conversations = [ConversationSession(
                user_id=db_session.user_id,
                conversation_id=db_session.conversation_id,
                updated_at=db_session.updated_at.replace(tzinfo=timezone.utc)
            ) for db_session in db_sessions]
            user_conversations.reverse()
            return user_conversations
