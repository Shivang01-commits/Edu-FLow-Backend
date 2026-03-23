import secrets
import string
import uuid
from datetime import date
from typing import Optional, List
from decimal import Decimal
import openpyxl
import csv
import io
from datetime import datetime
from fastapi import HTTPException, status, File, UploadFile
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
                "profile": {
                    "designation": t.teacher_profile.designation,
                    "salary": str(t.teacher_profile.salary),
                    "join_date": str(t.teacher_profile.join_date),
                }
                if t.teacher_profile
                else None,
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

        # fetch all active enrollments for these students in one query
        student_ids = [s.user_id for s in students]
        enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.student_id.in_(student_ids),
                Enrollment.is_active == True,
            )
            .all()
        )
        # build lookup dict: student_id → enrollment
        enrollment_map = {e.student_id: e for e in enrollments}

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
                "enrollment": {
                    "grade_level": enrollment_map[s.user_id].current_class_grade,
                    "section": enrollment_map[s.user_id].current_class_section,
                    "admission_number": enrollment_map[s.user_id].admission_number,
                    "parent_name": enrollment_map[s.user_id].parent_name,
                    "parent_phone": enrollment_map[s.user_id].parent_phone,
                    "fee_status": enrollment_map[s.user_id].fee_status,
                    "enrollment_date": enrollment_map[s.user_id].enrollment_date,
                }
                if s.user_id in enrollment_map
                else None,
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
            "is_active": student.is_active,
            "is_password_changed": student.is_password_changed,
            "created_at": student.created_at,
            "enrollment": {
                "grade_level": enrollment.current_class_grade,
                "section": enrollment.current_class_section,
                "admission_number": enrollment.admission_number,
                "parent_name": enrollment.parent_name,
                "parent_phone": enrollment.parent_phone,
                "fee_status": enrollment.fee_status,
                "enrollment_date": enrollment.enrollment_date,
                "is_active": enrollment.is_active,
            }
            if enrollment
            else None,
        }

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

        # fetch profile
        profile = (
            db.query(TeacherProfile)
            .filter(TeacherProfile.teacher_id == teacher_id)
            .first()
        )

        # fetch assigned classes — one query, no N+1
        assignments = (
            db.query(ClassTeacher).filter(ClassTeacher.teacher_id == teacher_id).all()
        )
        class_ids = [ct.class_id for ct in assignments]
        classes_db = db.query(Class).filter(Class.class_id.in_(class_ids)).all()
        class_map = {c.class_id: c for c in classes_db}

        assigned_classes = [
            {
                "class_id": str(ct.class_id),
                "grade_level": class_map[ct.class_id].grade_level
                if ct.class_id in class_map
                else None,
                "section": class_map[ct.class_id].section
                if ct.class_id in class_map
                else None,
                "subject": ct.subject,
                "is_classroom_teacher": ct.is_classroom_teacher,
                "assigned_date": ct.assigned_date,
            }
            for ct in assignments
        ]

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
            "profile": {
                "designation": profile.designation,
                "salary": str(profile.salary) if profile.salary else None,
                "join_date": str(profile.join_date) if profile.join_date else None,
            }
            if profile
            else None,
            "assigned_classes": assigned_classes,
            "total_classes": len(assigned_classes),
        }

    def get_class_by_id(self, db: Session, admin: User, class_id: uuid.UUID) -> dict:
        class_ = get_class_or_404(db, class_id)

        if class_.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This class does not belong to your school",
            )

        # count enrolled students
        student_count = (
            db.query(Enrollment)
            .filter(
                Enrollment.class_id == class_id,
                Enrollment.is_active == True,
            )
            .count()
        )

        # get assigned teachers
        assignments = (
            db.query(ClassTeacher).filter(ClassTeacher.class_id == class_id).all()
        )

        return {
            "class_id": str(class_.class_id),
            # "class_name": class_.class_name,
            "grade_level": class_.grade_level,
            "section": class_.section,
            "school_id": str(class_.school_id),
            "created_at": class_.created_at,
            "student_count": student_count,
            "teachers": [
                {
                    "teacher_id": str(ct.teacher_id),
                    "subject": ct.subject,
                    "is_classroom_teacher": ct.is_classroom_teacher,
                    "assigned_date": ct.assigned_date,
                }
                for ct in assignments
            ],
        }

    def delete_class(self, db: Session, admin: User, class_id: uuid.UUID) -> dict:
        class_ = get_class_or_404(db, class_id)

        if class_.school_id != admin.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This class does not belong to your school",
            )

        # block deletion if students are actively enrolled
        active_enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.class_id == class_id,
                Enrollment.is_active == True,
            )
            .count()
        )
        if active_enrollments > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete class — {active_enrollments} student(s) are still enrolled. Remove them first.",
            )

        db.delete(class_)
        db.commit()
        return {
            "message": f"Class '{class_.grade_level} {class_.section or ''}' deleted successfully."
        }

    def _validate_and_map_columns(self, headers: List[str]) -> dict:
        """
        Validate column headers and return mapping of expected columns to their indices.
        Flexible matching: case-insensitive, ignores extra columns.
        """

        # Expected columns (order matters for our current code)
        expected_columns = {
            "admission_number": [
                "admission number",
                "admission no",
                "admission_number",
            ],
            "first_name": ["first name", "first_name", "firstname"],
            "last_name": ["last name", "last_name", "lastname"],
            "date_of_birth": ["date of birth", "dob", "date_of_birth", "date"],
            "email": ["email", "email address", "email_address"],
            "parent_name": [
                "parent name",
                "parent_name",
                "guardian name",
                "guardian_name",
            ],
            "parent_phone": ["parent phone", "parent_phone", "phone", "contact"],
            "class_grade": ["class", "grade", "class grade", "class_grade"],
            "section": ["section", "class section", "class_section"],
        }

        # Convert headers to lowercase for matching
        headers_lower = [h.lower().strip() if h else "" for h in headers]

        # Create mapping: expected_col -> actual_index
        column_mapping = {}
        matched_cols = set()

        for expected_col, variants in expected_columns.items():
            for idx, header in enumerate(headers_lower):
                if header in variants and idx not in matched_cols:
                    column_mapping[expected_col] = idx
                    matched_cols.add(idx)
                    break

        # Check if all required columns are found
        required_cols = ["first_name", "email", "class_grade", "section"]
        missing_cols = [col for col in required_cols if col not in column_mapping]

        if missing_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_cols)}",
            )

        return column_mapping

    async def bulk_enroll_students(
        self, db: Session, admin: User, file: UploadFile
    ) -> dict:

        # Step 1: Validate file type
        if file.filename.endswith(".xlsx"):
            file_type = "xlsx"
        elif file.filename.endswith(".csv"):
            file_type = "csv"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be .xlsx or .csv",
            )

        # Step 2: Read file content
        content = await file.read()

        # Step 3: Parse file and validate columns
        rows = []
        column_mapping = None

        if file_type == "xlsx":
            workbook = openpyxl.load_workbook(io.BytesIO(content))
            worksheet = workbook.active

            # Get headers from first row
            headers = [cell.value for cell in worksheet[1]]
            column_mapping = self._validate_and_map_columns(headers)

            # Parse data rows
            for row_num, row in enumerate(
                worksheet.iter_rows(min_row=2, values_only=True), start=2
            ):
                rows.append(
                    {
                        "row_number": row_num,
                        "admission_number": row[column_mapping.get("admission_number")],
                        "first_name": row[column_mapping.get("first_name")],
                        "last_name": row[column_mapping.get("last_name")],
                        "date_of_birth": row[column_mapping.get("date_of_birth")],
                        "email": row[column_mapping.get("email")],
                        "parent_name": row[column_mapping.get("parent_name")],
                        "parent_phone": row[column_mapping.get("parent_phone")],
                        "class_grade": row[column_mapping.get("class_grade")],
                        "section": row[column_mapping.get("section")],
                    }
                )

        else:  # CSV
            content_str = content.decode("utf-8")
            reader = csv.reader(io.StringIO(content_str))

            # Get headers from first row
            headers = next(reader)
            column_mapping = self._validate_and_map_columns(headers)

            # Parse data rows
            for row_num, row in enumerate(reader, start=2):
                rows.append(
                    {
                        "row_number": row_num,
                        "admission_number": row[column_mapping.get("admission_number")]
                        if column_mapping.get("admission_number") < len(row)
                        else None,
                        "first_name": row[column_mapping.get("first_name")]
                        if column_mapping.get("first_name") < len(row)
                        else None,
                        "last_name": row[column_mapping.get("last_name")]
                        if column_mapping.get("last_name") < len(row)
                        else None,
                        "date_of_birth": row[column_mapping.get("date_of_birth")]
                        if column_mapping.get("date_of_birth") < len(row)
                        else None,
                        "email": row[column_mapping.get("email")]
                        if column_mapping.get("email") < len(row)
                        else None,
                        "parent_name": row[column_mapping.get("parent_name")]
                        if column_mapping.get("parent_name") < len(row)
                        else None,
                        "parent_phone": row[column_mapping.get("parent_phone")]
                        if column_mapping.get("parent_phone") < len(row)
                        else None,
                        "class_grade": row[column_mapping.get("class_grade")]
                        if column_mapping.get("class_grade") < len(row)
                        else None,
                        "section": row[column_mapping.get("section")]
                        if column_mapping.get("section") < len(row)
                        else None,
                    }
                )

        # Step 4: Validate all rows first
        failed_rows = []
        skipped_rows = []
        valid_rows = []

        for row in rows:
            error = None

            # Check required fields
            if (
                not row["first_name"]
                or not row["email"]
                or not row["class_grade"]
                or not row["section"]
            ):
                error = "Missing required fields"

            # Check email format
            elif not self._is_valid_email(row["email"]):
                error = "Invalid email format"

            # Check DOB format (dd-mm-yyyy)
            elif not self._is_valid_dob(row["date_of_birth"]):
                error = "Invalid DOB format (use dd-mm-yyyy)"

            # Check if email already enrolled
            elif self._email_already_enrolled(db, row["email"]):
                skipped_rows.append(
                    {
                        "row_number": row["row_number"],
                        "email": row["email"],
                        "reason": "Email already enrolled",
                    }
                )
                continue

            # Check if admission_number already enrolled
            elif row["admission_number"] and self._admission_number_already_enrolled(
                db, row["admission_number"]
            ):
                skipped_rows.append(
                    {
                        "row_number": row["row_number"],
                        "admission_number": row["admission_number"],
                        "reason": "Admission number already enrolled",
                    }
                )
                continue

            # Check if class+section exists
            elif not self._class_section_exists(db, row["class_grade"], row["section"]):
                error = f"Class {row['class_grade']} Section {row['section']} does not exist"

            if error:
                failed_rows.append({"row_number": row["row_number"], "reason": error})
            else:
                valid_rows.append(row)

        # Step 5: If there are failed rows, return validation failure
        if failed_rows:
            return {
                "status": "validation_failed",
                "total_rows": len(rows),
                "enrolled_count": 0,
                "skipped_count": len(skipped_rows),
                "failed_count": len(failed_rows),
                "skipped_rows": skipped_rows,
                "failed_rows": failed_rows,
            }

        # Step 6: Enroll all valid rows
        enrolled_count = 0

        for row in valid_rows:
            try:
                # Call existing register_student method for each valid row
                self.register_student(
                    db=db,
                    admin=admin,
                    email=row["email"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    date_of_birth=self._parse_dob(row["date_of_birth"]),
                    class_grade=row["class_grade"],
                    section=row["section"],
                    admission_number=row["admission_number"],
                    parent_name=row["parent_name"],
                    parent_phone=row["parent_phone"],
                )
                enrolled_count += 1
            except Exception as e:
                # If enrollment fails, add to failed rows
                failed_rows.append({"row_number": row["row_number"], "reason": str(e)})

        return {
            "status": "success",
            "total_rows": len(rows),
            "enrolled_count": enrolled_count,
            "skipped_count": len(skipped_rows),
            "failed_count": len(failed_rows),
            "skipped_rows": skipped_rows,
            "failed_rows": failed_rows,
        }

    # Helper methods
    def _is_valid_email(self, email: str) -> bool:
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _is_valid_dob(self, dob) -> bool:
        if dob is None:
            return False
        try:
            if isinstance(dob, str):
                datetime.strptime(dob, "%d-%m-%Y")
            return True
        except:
            return False

    def _parse_dob(self, dob) -> datetime:
        if isinstance(dob, str):
            return datetime.strptime(dob, "%d-%m-%Y").date()
        return dob

    def _email_already_enrolled(self, db: Session, email: str) -> bool:
        from src.db.models import User, Enrollment

        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user.user_id, Enrollment.is_active == True)
            .first()
        )
        return enrollment is not None

    def _admission_number_already_enrolled(
        self, db: Session, admission_number: int
    ) -> bool:
        from src.db.models import User

        user = db.query(User).filter(User.admission_number == admission_number).first()
        return user is not None

    def _class_section_exists(
        self, db: Session, class_grade: int, section: str
    ) -> bool:
        from src.db.models import Class

        class_record = (
            db.query(Class)
            .filter(Class.grade_level == class_grade, Class.section == section.upper())
            .first()
        )
        return class_record is not None
