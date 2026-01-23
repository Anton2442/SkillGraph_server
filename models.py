from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base
import enum
import uuid


# Enums
class AuthProvider(str, enum.Enum):
    local = "local"
    google = "google"


class SkillStatus(str, enum.Enum):
    locked = "locked"
    available = "available"
    completed = "completed"
    mastered = "mastered"


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String, unique=True, nullable=False)
    username = Column(String)

    password_hash = Column(String, nullable=False)

    auth_provider = Column(
        ENUM(AuthProvider, name="auth_provider", create_type=False),
        default=AuthProvider.local
    )
    provider_id = Column(String)

    email_verified = Column(Boolean, default=False)

    avatar_url = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)

    title = Column(String)
    description = Column(Text)

    xp_reward = Column(Integer)
    icon_url = Column(String)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), primary_key=True)

    earned_at = Column(DateTime(timezone=True), server_default=func.now())


class Direction(Base):
    __tablename__ = "directions"

    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True)

    title = Column(String)
    description = Column(Text)
    icon_url = Column(String)

    root_graph_id = Column(Integer, ForeignKey("graphs.id"))


class Graph(Base):
    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True)

    title = Column(String)
    description = Column(Text)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    slug = Column(String)

    title = Column(String, nullable=False)
    description = Column(Text)

    resources = relationship("SkillResource", back_populates="skill")


class SkillResource(Base):
    __tablename__ = "skill_resources"

    id = Column(Integer, primary_key=True)

    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    skill = relationship("Skill", back_populates="resources")

    url = Column(String, nullable=False)

    type = Column(String, nullable=False)


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(Integer, primary_key=True)

    graph_id = Column(Integer, ForeignKey("graphs.id"))

    node_type = Column(String)

    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=True)
    subgraph_id = Column(Integer, ForeignKey("graphs.id"), nullable=True)

    position_x = Column(Integer)
    position_y = Column(Integer)

    skill = relationship("Skill", foreign_keys=[skill_id])
    subgraph = relationship("Graph", foreign_keys=[subgraph_id])


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True)

    graph_id = Column(Integer, ForeignKey("graphs.id"))

    from_node_id = Column(Integer, ForeignKey("graph_nodes.id"))
    to_node_id = Column(Integer, ForeignKey("graph_nodes.id"))

    relation_type = Column(String)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)

    skill_id = Column(Integer, ForeignKey("skills.id"))

    type = Column(String, default="quiz")

    text = Column(Text)
    code_snippet = Column(Text)
    explanation = Column(Text)

    answers = relationship("Answer", back_populates="question")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True)

    question_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("Question", back_populates="answers")

    text = Column(Text)
    is_correct = Column(Boolean, default=False)



class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), primary_key=True)

    status = Column(
        ENUM(SkillStatus, name="skill_status", create_type=False),
        default=SkillStatus.locked
    )

    unlocked_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    skill_id = Column(Integer, ForeignKey("skills.id"))

    score = Column(Integer)
    is_passed = Column(Boolean)

    finished_at = Column(DateTime(timezone=True), server_default=func.now())