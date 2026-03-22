import secrets
import string
import uuid
from datetime import date
from typing import Optional
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.db.models import (
    User,
    UserRole,
    Class,
    Enrollment,
    TeacherProfile,
    ClassTeacher,
)
from src.services.db_services.auth_service import hash_password
from src.services.email_service import (
    send_student_welcome_email,
    send_teacher_welcome_email,
)
from src.utils.db_utils import (
    get_school_or_404,
    get_user_or_404,
    check_email_unique,
    get_class_or_404,
)


def generate_random_password(length: int = 12) -> str:
    """
    Generates a secure random password.
    Guarantees at least one uppercase, lowercase, digit, special char.
    Example: "Kx7#mP2@nQ9!"
    """
    alphabet = (
        string.ascii_uppercase + string.ascii_lowercase + string.digits + "!@#$%^&*"
    )
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


class AdminService:
    # -----------------------------------------------------------------------
    # REGISTER TEACHER
    # -----------------------------------------------------------------------
    def register_teacher(
        self,
        db: Session,
        admin: User,
        email: str,
        first_name: str,
        last_name: Optional[str],
        date_of_birth: date,
        phone_number: Optional[str],
        designation: str,
        salary: Decimal,
        join_date: date,
    ) -> dict:
        check_email_unique(db, email)

        school = get_school_or_404(db, admin.school_id)
        raw_password = generate_random_password()

        teacher = User(
            school_id=admin.school_id,
            email=email.lower().strip(),
            password_hash=hash_password(raw_password),
            first_name=first_name.strip(),
            last_name=last_name.strip() if last_name else None,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
            role=UserRole.teacher,
            is_active=True,
            is_password_changed=False,
        )
        db.add(teacher)
        db.flush()

        profile = TeacherProfile(
            teacher_id=teacher.user_id,
            school_id=admin.school_id,
            designation=designation.strip(),
            salary=salary,
            join_date=join_date,
        )
        db.add(profile)
        db.commit()
        db.refresh(teacher)
        db.refresh(profile)

        send_teacher_welcome_email(
            to_email=email,
            first_name=first_name,
            school_name=school.school_name,
            password=raw_password,
        )

        return {
            "message": "Teacher registered. Login details sent to their email.",
            "teacher_id": str(teacher.user_id),
            "email": teacher.email,
            "designation": profile.designation,
            "salary": str(profile.salary),
            "join_date": str(profile.join_date),
        }

    def register_student(
        self,
        db: Session,
        admin: User,
        email: str,
        first_name: str,
        last_name: Optional[str],
        date_of_birth: date,
        class_grade: int,
        section: str,
        admission_number: int,
        parent_name: str,
        parent_phone: str,
    ) -> dict:
        check_email_unique(db, email)

        # lookup class by grade + section within admin's school
        class_ = (
            db.query(Class)
            .filter(
                Class.school_id == admin.school_id,
                Class.grade_level == class_grade,
                Class.section == section.upper().strip(),
            )
            .first()
        )
        if not class_:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Class {class_grade} Section {section.upper()} not found in your school. Create it first.",
            )

        # check admission_number unique within this school
        existing_admission = (
            db.query(Enrollment)
            .join(User, Enrollment.student_id == User.user_id)
            .filter(
                User.school_id == admin.school_id,
                Enrollment.admission_number == admission_number,
                Enrollment.is_active == True,
            )
            .first()
        )
        if existing_admission:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Admission number {admission_number} already exists in your school",
            )

        school = get_school_or_404(db, admin.school_id)
        raw_password = generate_random_password()

        student = User(
            school_id=admin.school_id,
            email=email.lower().strip(),
            password_hash=hash_password(raw_password),
            first_name=first_name.strip(),
            last_name=last_name.strip() if last_name else None,
            date_of_birth=date_of_birth,
            phone_number=parent_phone,
            role=UserRole.student,
            is_active=True,
            is_password_changed=False,
        )
        db.add(student)
        db.flush()

        enrollment = Enrollment(
            school_id=admin.school_id,
            class_id=class_.class_id,
            student_id=student.user_id,
            current_class_grade=class_.grade_level,
            current_class_section=class_.section,
            is_active=True,
            admission_number=admission_number,
            parent_name=parent_name.strip() if parent_name else None,
            parent_phone=parent_phone.strip() if parent_phone else None,
            fee_status="pending",
        )
        db.add(enrollment)
        db.commit()
        db.refresh(student)

        send_student_welcome_email(
            to_email=email,
            first_name=first_name,
            school_name=school.school_name,
            password=raw_password,
            grade_level=class_.grade_level,
            section=class_.section or "",
        )

        return {
            "message": "Student registered and enrolled. Login details sent to their email.",
            "student_id": str(student.user_id),
            "email": student.email,
            "class_grade": class_grade,
            "section": section,
            "admission_number": admission_number,
        }

    def create_class(
        self,
        db: Session,
        admin: User,
        grade_level: int,
        section: Optional[str] = None,
    ) -> Class:
        existing = (
            db.query(Class)
            .filter(
                Class.school_id == admin.school_id,
                Class.grade_level == grade_level,
                Class.section == (section.strip() if section else None),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Class '{grade_level} {section or ''}' already exists in your school",
            )

        new_class = Class(
            school_id=admin.school_id,
            grade_level=grade_level,
            section=section.strip() if section else None,
        )
        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        return new_class

    # -----------------------------------------------------------------------
    # ASSIGN TEACHER TO CLASS
    # -----------------------------------------------------------------------
    def assign_teacher_to_class(
        self,
        db: Session,
        admin: User,
        class_id: uuid.UUID,
        teacher_id: uuid.UUID,
        subject: Optional[str] = None,
        is_classroom_teacher: bool = False,
    ) -> ClassTeacher:
        teacher = get_user_or_404(db, teacher_id)
        if teacher.role != UserRole.teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a teacher"
            )
        if teacher.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher does not belong to your school",
            )

        class_ = get_class_or_404(db, class_id)
        if class_.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Class does not belong to your school",
            )

        existing = (
            db.query(ClassTeacher)
            .filter(
                ClassTeacher.class_id == class_id,
                ClassTeacher.teacher_id == teacher_id,
                ClassTeacher.subject == subject,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Teacher is already assigned to this class for this subject",
            )

        assignment = ClassTeacher(
            school_id=admin.school_id,
            class_id=class_id,
            teacher_id=teacher_id,
            subject=subject,
            is_classroom_teacher=is_classroom_teacher,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment

    # -----------------------------------------------------------------------
    # LIST operations
    # -----------------------------------------------------------------------
    def list_teachers(self, db: Session, admin: User) -> list[dict]:
        teachers = (
            db.query(User)
            .filter(
                User.school_id == admin.school_id,
                User.role == UserRole.teacher,
                User.is_active == True,
            )
            .order_by(User.first_name)
            .all()
        )
        return [
            {
                "teacher_id": str(t.user_id),
                "first_name": t.first_name,
                "last_name": t.last_name,
                "email": t.email,
                "phone_number": t.phone_number,
                "date_of_birth": t.date_of_birth,
                "is_active": t.is_active,
                "is_password_changed": t.is_password_changed,
                "created_at": t.created_at,
            }
            for t in teachers
        ]

    def list_students(self, db: Session, admin: User) -> list[dict]:
        students = (
            db.query(User)
            .filter(
                User.school_id == admin.school_id,
                User.role == UserRole.student,
                User.is_active == True,
            )
            .order_by(User.first_name)
            .all()
        )
        return [
            {
                "student_id": str(s.user_id),
                "first_name": s.first_name,
                "last_name": s.last_name,
                "email": s.email,
                "phone_number": s.phone_number,
                "date_of_birth": s.date_of_birth,
                "is_active": s.is_active,
                "is_password_changed": s.is_password_changed,
                "created_at": s.created_at,
            }
            for s in students
        ]

    def list_classes(self, db: Session, admin: User) -> list[Class]:
        return (
            db.query(Class)
            .filter(Class.school_id == admin.school_id)
            .order_by(Class.grade_level, Class.section)
            .all()
        )

    def list_students_in_class(
        self, db: Session, admin: User, class_id: uuid.UUID
    ) -> list[dict]:
        class_ = get_class_or_404(db, class_id)
        if class_.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Class does not belong to your school",
            )

        enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.class_id == class_id,
                Enrollment.is_active == True,
            )
            .all()
        )

        result = []
        for e in enrollments:
            student = db.query(User).filter(User.user_id == e.student_id).first()
            if student:
                result.append(
                    {
                        "student_id": str(student.user_id),
                        "first_name": student.first_name,
                        "last_name": student.last_name,
                        "email": student.email,
                        "enrollment_date": e.enrollment_date,
                        "is_active": e.is_active,
                    }
                )
        return result

    # -----------------------------------------------------------------------
    # DEACTIVATE USER
    # -----------------------------------------------------------------------
    def deactivate_user(self, db: Session, admin: User, user_id: uuid.UUID) -> dict:
        user = get_user_or_404(db, user_id)
        if user.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to your school",
            )
        user.is_active = False
        db.commit()
        return {"message": f"User {user.email} has been deactivated"}

    # -----------------------------------------------------------------------
    # RESEND PASSWORD
    # -----------------------------------------------------------------------
    def resend_password(self, db: Session, admin: User, user_id: uuid.UUID) -> dict:
        user = get_user_or_404(db, user_id)
        if user.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to your school",
            )

        school = get_school_or_404(db, admin.school_id)
        raw_password = generate_random_password()

        user.password_hash = hash_password(raw_password)
        user.is_password_changed = False
        db.commit()

        if user.role == UserRole.teacher:
            send_teacher_welcome_email(
                to_email=user.email,
                first_name=user.first_name,
                school_name=school.school_name,
                password=raw_password,
            )
        else:
            send_student_welcome_email(
                to_email=user.email,
                first_name=user.first_name,
                school_name=school.school_name,
                password=raw_password,
                class_name="your class",
            )

        return {"message": f"New password generated and sent to {user.email}"}

    def get_student_by_id(
        self, db: Session, admin: User, student_id: uuid.UUID
    ) -> dict:
        student = get_user_or_404(db, student_id)

        if student.role != UserRole.student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )
        if student.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This student does not belong to your school",
            )

        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id == student_id,
                Enrollment.is_active == True,
            )
            .first()
        )

        return {
            "student_id": str(student.user_id),
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email,
            "phone_number": student.phone_number,
            "date_of_birth": student.date_of_birth,
            "admission_number": student.admission_number,
            "is_active": student.is_active,
            "is_password_changed": student.is_password_changed,
            "created_at": student.created_at,
            "enrollment": {
                "class_id": str(enrollment.class_id),
                "current_class": enrollment.current_class,
                "enrollment_date": enrollment.enrollment_date,
                "is_active": enrollment.is_active,
            }
            if enrollment
            else None,
        }

    # -----------------------------------------------------------------------
    # GET SINGLE TEACHER BY ID
    # -----------------------------------------------------------------------
    def get_teacher_by_id(
        self, db: Session, admin: User, teacher_id: uuid.UUID
    ) -> dict:
        teacher = get_user_or_404(db, teacher_id)

        if teacher.role != UserRole.teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher not found",
            )
        if teacher.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This teacher does not belong to your school",
            )

        # get all classes this teacher is assigned to
        assignments = (
            db.query(ClassTeacher).filter(ClassTeacher.teacher_id == teacher_id).all()
        )

        classes = []
        for ct in assignments:
            class_ = db.query(Class).filter(Class.class_id == ct.class_id).first()
            if class_:
                classes.append(
                    {
                        "class_id": str(class_.class_id),
                        "class_name": class_.class_name,
                        "section": class_.section,
                        "grade_level": class_.grade_level,
                        "subject": ct.subject,
                        "is_classroom_teacher": ct.is_classroom_teacher,
                        "assigned_date": ct.assigned_date,
                    }
                )

        return {
            "teacher_id": str(teacher.user_id),
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "email": teacher.email,
            "phone_number": teacher.phone_number,
            "date_of_birth": teacher.date_of_birth,
            "is_active": teacher.is_active,
            "is_password_changed": teacher.is_password_changed,
            "created_at": teacher.created_at,
            "assigned_classes": classes,
            "total_classes": len(classes),
        }
