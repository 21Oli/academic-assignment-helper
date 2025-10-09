from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Float
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from backend.database import Base


# ---------- Student ----------
class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: 1 student -> many assignments
    assignments = relationship("Assignment", back_populates="student", cascade="all, delete-orphan")


# ---------- Assignment ----------
class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    filename = Column(String, nullable=True)
    file_path = Column(String, nullable=True)  # Local file storage path
    original_text = Column(Text, nullable=True)
    topic = Column(String, nullable=True)
    academic_level = Column(String, nullable=True)
    word_count = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="assignments")
    analysis_results = relationship("AnalysisResult", back_populates="assignment", cascade="all, delete-orphan")


# ---------- AnalysisResult ----------
class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    suggested_sources = Column(JSONB)
    plagiarism_score = Column(Float)
    flagged_sections = Column(JSONB)
    research_suggestions = Column(Text)
    citation_recommendations = Column(Text)
    confidence_score = Column(Float)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: many analysis results → one assignment
    assignment = relationship("Assignment", back_populates="analysis_results")


# ---------- AcademicSource ----------
class AcademicSource(Base):
    __tablename__ = "academic_sources"

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    authors = Column(Text)
    publication_year = Column(Integer)
    abstract = Column(Text)
    full_text = Column(Text)
    source_type = Column(String)  # e.g., 'paper', 'textbook', 'article'
    embedding = Column(Vector(1536))  # ✅ pgvector column for semantic search
