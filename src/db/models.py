import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.main import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    sudo_admin = "sudo_admin"
    admin = "admin"
    teacher = "teacher"
    student = "student"


class School(Base):
    __tablename__ = "schools"

    school_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_name = Column(String, nullable=False)
    school_address = Column(String, nullable=True)
    school_phone = Column(String, nullable=True)
    admin_email = Column(String, unique=True, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    board = Column(String, nullable=False)
    affiliation_number = Column(String, nullable=False)
    registration_certificate_url = Column(String, nullable=True)
    noc_affiliation_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    plan = Column(String, nullable=False)

    users = relationship("User", back_populates="school")
    classes = relationship("Class", back_populates="school")
    class_teachers = relationship("ClassTeacher", back_populates="school")
    enrollments = relationship("Enrollment", back_populates="school")
    class_chapters = relationship("ClassChapter", back_populates="school")
    quizzes = relationship("Quiz", back_populates="school")


class User(Base):
    __tablename__ = "users"

    user_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="SET NULL"),
        nullable=True,
    )
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    phone_number = Column(String, nullable=True)

    # join_date = Column(String, nullable=True)
    # designation = Column(String, nullable=True)

    role = Column(
        SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.student
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_password_changed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school = relationship("School", back_populates="users")
    teaching = relationship(
        "ClassTeacher", back_populates="teacher", foreign_keys="ClassTeacher.teacher_id"
    )
    enrollments = relationship(
        "Enrollment", back_populates="student", foreign_keys="Enrollment.student_id"
    )
    quiz_attempts = relationship(
        "Quiz", back_populates="student", foreign_keys="Quiz.student_id"
    )
    chapters_taught = relationship(
        "ClassChapter", back_populates="teacher", foreign_keys="ClassChapter.teacher_id"
    )
    teacher_profile = relationship(
        "TeacherProfile", back_populates="teacher", uselist=False
    )


class Class(Base):
    __tablename__ = "classes"

    class_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
    )
    # class_name = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=False)
    section = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "school_id", "grade_level", "section", name="uq_class_school_section"
        ),
    )

    school = relationship("School", back_populates="classes")
    class_teachers = relationship(
        "ClassTeacher", back_populates="class_", cascade="all, delete-orphan"
    )
    enrollments = relationship(
        "Enrollment", back_populates="class_", cascade="all, delete-orphan"
    )
    class_chapters = relationship(
        "ClassChapter", back_populates="class_", cascade="all, delete-orphan"
    )


class ClassTeacher(Base):
    __tablename__ = "class_teachers"

    class_teacher_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
    )
    class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    subject = Column(String, nullable=True)
    is_classroom_teacher = Column(Boolean, default=False, nullable=False)
    assigned_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "class_id", "teacher_id", "subject", name="uq_class_teacher_subject"
        ),
    )

    school = relationship("School", back_populates="class_teachers")
    class_ = relationship("Class", back_populates="class_teachers")
    teacher = relationship("User", back_populates="teaching", foreign_keys=[teacher_id])


class Enrollment(Base):
    __tablename__ = "enrollments"

    enrollment_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
    )
    class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    current_class_grade = Column(Integer, nullable=True)
    current_class_section = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    enrollment_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    admission_number = Column(Integer, nullable=True, index=True)
    parent_name = Column(String, nullable=True)
    parent_phone = Column(String, nullable=True)
    # parent_email = Column(String, nullable=True)
    # guardian_name = Column(String, nullable=True)  # if different from parent
    # guardian_phone = Column(String, nullable=True)
    fee_status = Column(String, nullable=False, default="pending")

    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_enrollment_class_student"),
    )

    school = relationship("School", back_populates="enrollments")
    class_ = relationship("Class", back_populates="enrollments")
    student = relationship(
        "User", back_populates="enrollments", foreign_keys=[student_id]
    )


class Book(Base):
    __tablename__ = "books"

    book_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    book_name = Column(String, nullable=False)
    class_grade = Column(Integer, nullable=False)
    subject = Column(String, nullable=False)
    chapter_number = Column(Integer, nullable=False)
    chapter_title = Column(String, nullable=False)
    isbn = Column(String, nullable=True, index=True)
    board = Column(String, nullable=True, index=True)
    # change this scraped_nullable to False
    scraped_chapter = Column(String, nullable=False)
    summary = Column(JSONB, nullable=True)
    qa_bank = Column(JSONB, nullable=True)
    quiz = Column(JSONB, nullable=True)
    ppt_structure = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "book_name",
            "class_grade",
            "subject",
            "chapter_number",
            name="uq_book_name_grade_subject_chapter",
        ),
    )

    class_chapters = relationship("ClassChapter", back_populates="book")


class ClassChapter(Base):
    __tablename__ = "class_chapters"

    class_chapter_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
    )
    class_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classes.class_id", ondelete="CASCADE"),
        nullable=False,
    )
    book_id = Column(
        UUID(as_uuid=True),
        ForeignKey("books.book_id", ondelete="SET NULL"),
        nullable=True,
    )
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    # chapter_title = Column(String, nullable=True)
    chapter_number = Column(Integer, nullable=False)

    subject = Column(String, nullable=False)

    custom_summary = Column(JSONB, nullable=True, default=None)
    custom_qa_bank = Column(JSONB, nullable=True, default=None)
    custom_quiz = Column(JSONB, nullable=True, default=None)
    custom_ppt_structure = Column(JSONB, nullable=True, default=None)

    is_summary_overridden = Column(Boolean, default=False, nullable=False)
    is_qa_bank_overridden = Column(Boolean, default=False, nullable=False)
    is_quiz_overridden = Column(Boolean, default=False, nullable=False)
    is_ppt_overridden = Column(Boolean, default=False, nullable=False)

    published_date = Column(DateTime(timezone=True), nullable=True)
    last_modified_date = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    school = relationship("School", back_populates="class_chapters")
    class_ = relationship("Class", back_populates="class_chapters")
    book = relationship("Book", back_populates="class_chapters")
    teacher = relationship(
        "User", back_populates="chapters_taught", foreign_keys=[teacher_id]
    )
    quizzes = relationship(
        "Quiz", back_populates="class_chapter", cascade="all, delete-orphan"
    )


class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_attempt_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
    )
    class_chapter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("class_chapters.class_chapter_id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    score = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False, default=0.0)
    # attempted_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    response = Column(JSONB, nullable=True, default=None)

    submitted_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="pending")

    school = relationship("School", back_populates="quizzes")
    class_chapter = relationship("ClassChapter", back_populates="quizzes")
    student = relationship(
        "User", back_populates="quiz_attempts", foreign_keys=[student_id]
    )


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    profile_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    school_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
    )

    designation = Column(String, nullable=True)
    join_date = Column(Date, nullable=True)
    salary = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    teacher = relationship(
        "User", back_populates="teacher_profile", foreign_keys=[teacher_id]
    )
    school = relationship("School", foreign_keys=[school_id])
