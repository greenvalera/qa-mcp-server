"""QA-specific data models for checklists and testcases."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, ForeignKey, 
    CHAR, Enum, func, Index, Table, JSON
)
from sqlalchemy.orm import relationship, Mapped, declarative_base
from enum import Enum as PyEnum

Base = declarative_base()


class Priority(PyEnum):
    """Test case priority levels."""
    LOWEST = "LOWEST"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    HIGHEST = "HIGHEST"
    CRITICAL = "CRITICAL"


class TestGroup(PyEnum):
    """Test case groups (GENERAL or CUSTOM)."""
    GENERAL = "GENERAL"
    CUSTOM = "CUSTOM"


# Association table for many-to-many relationship between checklists and configs
checklist_configs = Table(
    'checklist_configs',
    Base.metadata,
    Column('checklist_id', String(64), ForeignKey('checklists.id', ondelete="CASCADE"), primary_key=True),
    Column('config_id', Integer, ForeignKey('configs.id', ondelete="CASCADE"), primary_key=True),
    Column('created_at', TIMESTAMP, default=func.current_timestamp())
)


class QASection(Base):
    """QA Section model representing root sections like 'Checklist WEB', 'Checklist MOB'."""
    
    __tablename__ = "qa_sections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    confluence_page_id = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(1024), nullable=False)
    space_key = Column(String(64), nullable=False, index=True)
    parent_section_id = Column(Integer, ForeignKey('qa_sections.id', ondelete="CASCADE"), nullable=True)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, 
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    
    # Relationships
    checklists: Mapped[List["Checklist"]] = relationship(
        "Checklist", 
        back_populates="section",
        cascade="all, delete-orphan"
    )
    
    # Self-referential relationship for hierarchical structure
    parent_section: Mapped[Optional["QASection"]] = relationship(
        "QASection", 
        remote_side=[id],
        back_populates="child_sections"
    )
    child_sections: Mapped[List["QASection"]] = relationship(
        "QASection",
        back_populates="parent_section",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<QASection(id={self.id}, title='{self.title}')>"


class Config(Base):
    """Configuration model for storing config references."""
    
    __tablename__ = "configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    url = Column(String(1024), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, 
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    
    # Relationships
    testcases: Mapped[List["TestCase"]] = relationship(
        "TestCase", 
        back_populates="config"
    )
    
    checklists: Mapped[List["Checklist"]] = relationship(
        "Checklist",
        secondary=checklist_configs,
        back_populates="configs"
    )
    
    def __repr__(self) -> str:
        return f"<Config(id={self.id}, name='{self.name}')>"


class Checklist(Base):
    """Checklist model representing pages with testcases like 'WEB: Billing History'."""
    
    __tablename__ = "checklists"
    
    id = Column(String(64), primary_key=True)  # Використовуємо confluence_page_id як primary key
    confluence_page_id = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    additional_content = Column(Text, nullable=True)  # Additional information before testcases table
    url = Column(String(1024), nullable=False)
    space_key = Column(String(64), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey('qa_sections.id', ondelete="CASCADE"), nullable=False)
    subcategory = Column(String(255), nullable=True, index=True)  # Subcategory from parent page hierarchy
    content_hash = Column(CHAR(64), nullable=False, index=True)
    version = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, 
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    
    # Relationships
    section: Mapped["QASection"] = relationship(
        "QASection", 
        back_populates="checklists"
    )
    
    testcases: Mapped[List["TestCase"]] = relationship(
        "TestCase", 
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="TestCase.order_index"
    )
    
    configs: Mapped[List["Config"]] = relationship(
        "Config",
        secondary=checklist_configs,
        back_populates="checklists"
    )
    
    def __repr__(self) -> str:
        return f"<Checklist(id={self.id}, title='{self.title}')>"


class TestCase(Base):
    """TestCase model representing individual test cases."""
    
    __tablename__ = "testcases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    checklist_id = Column(String(64), ForeignKey('checklists.id', ondelete="CASCADE"), nullable=False)
    step = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=False)
    screenshot = Column(String(1024), nullable=True)
    priority = Column(Enum(Priority), nullable=True, index=True)
    test_group = Column(Enum(TestGroup), nullable=True, index=True)  # GENERAL or CUSTOM
    functionality = Column(String(255), nullable=True, index=True)  # Functionality group within test_group
    order_index = Column(Integer, nullable=False, default=0)
    config_id = Column(Integer, ForeignKey('configs.id', ondelete="SET NULL"), nullable=True)
    qa_auto_coverage = Column(String(255), nullable=True)
    # Embedding для семантичного пошуку (JSON масив з float значеннями)
    embedding = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, 
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    
    # Relationships
    checklist: Mapped["Checklist"] = relationship(
        "Checklist", 
        back_populates="testcases"
    )
    
    config: Mapped[Optional["Config"]] = relationship(
        "Config", 
        back_populates="testcases"
    )
    
    def __repr__(self) -> str:
        return f"<TestCase(id={self.id}, checklist_id={self.checklist_id}, step='{self.step[:50]}...')>"


# Keep the existing IngestionJob model for compatibility
class IngestionJob(Base):
    """Ingestion job tracking."""
    
    __tablename__ = "ingestion_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(TIMESTAMP, default=func.current_timestamp())
    finished_at = Column(TIMESTAMP, nullable=True)
    status = Column(
        String(20), 
        nullable=False, 
        default="running"
    )  # running, success, failed
    details = Column(Text, nullable=True)
    documents_processed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)
    features_created = Column(Integer, default=0)
    
    def __repr__(self) -> str:
        return f"<IngestionJob(id={self.id}, status='{self.status}')>"


# Indexes for better performance
Index("idx_testcases_checklist_order", TestCase.checklist_id, TestCase.order_index)
# Note: Full-text index on TEXT columns requires different approach in MySQL
Index("idx_checklists_section", Checklist.section_id)
Index("idx_qa_sections_space", QASection.space_key)
Index("idx_qa_sections_parent", QASection.parent_section_id)
Index("idx_ingestion_jobs_status", IngestionJob.status)
Index("idx_ingestion_jobs_started", IngestionJob.started_at)
