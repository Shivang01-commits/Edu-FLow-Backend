# Padhai App — Complete Backend Testing Guide
Base URL: http://127.0.0.1:8000

---

## POSTMAN SETUP (do this first)

### 1. Create Environment
In Postman → Environments → New → Name it "Padhai Local"

Add these variables:
| Variable          | Initial Value                  |
|-------------------|-------------------------------|
| base_url          | http://127.0.0.1:8000          |
| access_token      | (leave empty)                  |
| refresh_token     | (leave empty)                  |
| school_id         | (leave empty)                  |
| admin_id          | (leave empty)                  |
| teacher_id        | (leave empty)                  |
| student_id        | (leave empty)                  |
| class_id          | (leave empty)                  |
| class_chapter_id  | (leave empty)                  |
| book_id           | (leave empty)                  |

### 2. Auto-save token script
On every LOGIN request → Tests tab → paste this:
```javascript
const res = pm.response.json();
if (res.access_token) {
    pm.environment.set("access_token", res.access_token);
    pm.environment.set("refresh_token", res.refresh_token);
    console.log("Tokens saved ✅");
}
```

### 3. Authorization on all protected routes
Header → Key: Authorization  Value: Bearer {{access_token}}

---

## PHASE 0 — SEED & HEALTH CHECK

### T01 — Health check
```
GET {{base_url}}/
Expected: 200
{
  "message": "Backend running successfully"
}
```

### T02 — Run seed script first
```bash
python seed_sudo_admin.py
```
Expected output:
```
✅ sudo_admin created successfully!
   Email:    superadmin@padhai.com
   Password: SuperAdmin@123
```

---

## PHASE 1 — AUTH TESTS

### T03 — Login as sudo_admin
```
POST {{base_url}}/auth/login
Body (JSON):
{
  "email": "superadmin@padhai.com",
  "password": "SuperAdmin@123"
}

Expected: 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "is_password_changed": true,
  "user": {
    "role": "sudo_admin",
    "school_id": null
  }
}
```
→ Tokens auto-saved via Tests script

### T04 — Login with wrong password
```
POST {{base_url}}/auth/login
Body:
{
  "email": "superadmin@padhai.com",
  "password": "wrongpassword"
}

Expected: 401
{ "detail": "Invalid email or password" }
```

### T05 — Login with non-existent email
```
POST {{base_url}}/auth/login
Body:
{
  "email": "nobody@padhai.com",
  "password": "anything"
}

Expected: 401
{ "detail": "Invalid email or password" }
```

### T06 — Get profile (/auth/me)
```
GET {{base_url}}/auth/me
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "user_id": "...",
  "email": "superadmin@padhai.com",
  "role": "sudo_admin",
  "school_id": null,
  "is_password_changed": true
}
```

### T07 — Get profile without token
```
GET {{base_url}}/auth/me
(no Authorization header)

Expected: 403
{ "detail": "Not authenticated" }
```

### T08 — Refresh access token
```
POST {{base_url}}/auth/refresh
Headers: Authorization: Bearer {{refresh_token}}

Expected: 200
{
  "access_token": "eyJ...(new token)",
  "token_type": "bearer"
}
```

### T09 — Refresh using access token (should fail)
```
POST {{base_url}}/auth/refresh
Headers: Authorization: Bearer {{access_token}}

Expected: 401
{ "detail": "Invalid token type — use refresh token" }
```

### T10 — Change password
```
POST {{base_url}}/auth/change-password
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "old_password": "SuperAdmin@123",
  "new_password": "NewAdmin@456"
}

Expected: 200
{ "message": "Password changed successfully" }
```
→ Change it back after this test:
old_password: "NewAdmin@456", new_password: "SuperAdmin@123"

### T11 — Change password with wrong old password
```
POST {{base_url}}/auth/change-password
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "old_password": "wrongpassword",
  "new_password": "NewAdmin@456"
}

Expected: 400
{ "detail": "Current password is incorrect" }
```

### T12 — Change password to same password
```
POST {{base_url}}/auth/change-password
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "old_password": "SuperAdmin@123",
  "new_password": "SuperAdmin@123"
}

Expected: 400
{ "detail": "New password must be different from your current password" }
```

---

## PHASE 2 — SUDO ADMIN TESTS
(still logged in as sudo_admin from T03)

### T13 — Create school
```
POST {{base_url}}/sudo/schools
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "school_name": "Delhi Public School",
  "admin_email": "admin@dps.com",
  "school_address": "Sector 45, Noida",
  "school_phone": "9876543210"
}

Expected: 201
{
  "school_id": "uuid...",
  "school_name": "Delhi Public School",
  "is_active": true
}
```
→ In Tests tab: pm.environment.set("school_id", pm.response.json().school_id);

### T14 — Create duplicate school (same admin_email)
```
POST {{base_url}}/sudo/schools
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "school_name": "Another School",
  "admin_email": "admin@dps.com"
}

Expected: 409
{ "detail": "A school with admin email admin@dps.com already exists" }
```

### T15 — List all schools
```
GET {{base_url}}/sudo/schools
Headers: Authorization: Bearer {{access_token}}

Expected: 200
[
  {
    "school_id": "...",
    "school_name": "Delhi Public School",
    "is_active": true
  }
]
```

### T16 — Get school by ID
```
GET {{base_url}}/sudo/schools/{{school_id}}
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{ "school_id": "{{school_id}}", "school_name": "Delhi Public School" }
```

### T17 — Get school with invalid ID
```
GET {{base_url}}/sudo/schools/00000000-0000-0000-0000-000000000000
Headers: Authorization: Bearer {{access_token}}

Expected: 404
{ "detail": "School not found" }
```

### T18 — Create admin for school
```
POST {{base_url}}/sudo/admins/create
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "school_id": "{{school_id}}",
  "email": "admin@dps.com",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "date_of_birth": "1985-06-15"
}

Expected: 201
{
  "message": "Admin created for 'Delhi Public School'. Login details sent to their email.",
  "admin_id": "uuid...",
  "email": "admin@dps.com",
  "school": "Delhi Public School"
}
```
→ Check the email for password
→ In Tests tab: pm.environment.set("admin_id", pm.response.json().admin_id);

### T19 — Create duplicate admin for same school
```
POST {{base_url}}/sudo/admins/create
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "school_id": "{{school_id}}",
  "email": "admin2@dps.com",
  "first_name": "Another",
  "last_name": "Admin",
  "date_of_birth": "1990-01-01"
}

Expected: 409
{ "detail": "School '...' already has an active admin (admin@dps.com). Deactivate the existing admin first." }
```

### T20 — Try sudo_admin route as non-sudo_admin (use any other token later)
(skip for now — test after admin login)

### T21 — Deactivate school (test last — do this after all other tests)
```
POST {{base_url}}/sudo/schools/{{school_id}}/deactivate
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{ "message": "School 'Delhi Public School' deactivated. All associated users deactivated." }
```
⚠️ DO THIS LAST — it deactivates all users

---

## PHASE 3 — ADMIN TESTS

### T22 — Login as admin
```
POST {{base_url}}/auth/login
Body:
{
  "email": "admin@dps.com",
  "password": "<password from welcome email>"
}

Expected: 200
{
  "is_password_changed": false,    ← shows banner on frontend
  "user": { "role": "admin" }
}
```
→ Tokens auto-saved

### T23 — Admin accessing sudo route (should fail)
```
POST {{base_url}}/sudo/schools
Headers: Authorization: Bearer {{access_token}}
Body: { "school_name": "Hack School", "admin_email": "x@x.com" }

Expected: 403
{ "detail": "Access denied. Required roles: ['sudo_admin']. Your role: admin" }
```

### T24 — Create class
```
POST {{base_url}}/admin/classes
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "class_name": "Class 10",
  "grade_level": 10,
  "section": "A"
}

Expected: 201
{
  "class_id": "uuid...",
  "class_name": "Class 10",
  "grade_level": 10,
  "section": "A"
}
```
→ Save: pm.environment.set("class_id", pm.response.json().class_id);

### T25 — Create duplicate class
```
POST {{base_url}}/admin/classes
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "class_name": "Class 10",
  "grade_level": 10,
  "section": "A"
}

Expected: 409
{ "detail": "Class 'Class 10 A' already exists in your school" }
```

### T26 — Create another class (we need 2)
```
POST {{base_url}}/admin/classes
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "class_name": "Class 10",
  "grade_level": 10,
  "section": "B"
}

Expected: 201
```

### T27 — List classes
```
GET {{base_url}}/admin/classes
Headers: Authorization: Bearer {{access_token}}

Expected: 200
[
  { "class_name": "Class 10", "section": "A" },
  { "class_name": "Class 10", "section": "B" }
]
```

### T28 — Register teacher
```
POST {{base_url}}/admin/teachers/register
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "email": "science.teacher@dps.com",
  "first_name": "Anil",
  "last_name": "Sharma",
  "date_of_birth": "1988-03-20"
}

Expected: 201
{
  "message": "Teacher registered. Login details sent to their email.",
  "teacher_id": "uuid...",
  "email": "science.teacher@dps.com"
}
```
→ Save: pm.environment.set("teacher_id", pm.response.json().teacher_id);

### T29 — Register teacher with duplicate email
```
POST {{base_url}}/admin/teachers/register
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "email": "science.teacher@dps.com",
  "first_name": "Duplicate",
  "last_name": "Teacher",
  "date_of_birth": "1990-01-01"
}

Expected: 409
{ "detail": "A user with email science.teacher@dps.com already exists" }
```

### T30 — List teachers
```
GET {{base_url}}/admin/teachers
Headers: Authorization: Bearer {{access_token}}

Expected: 200
[
  { "first_name": "Anil", "role": "teacher" }
]
```

### T31 — Assign teacher to class
```
POST {{base_url}}/admin/classes/{{class_id}}/assign-teacher
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "teacher_id": "{{teacher_id}}",
  "subject": "Science",
  "is_classroom_teacher": true
}

Expected: 201
{
  "class_teacher_id": "uuid...",
  "subject": "Science",
  "is_classroom_teacher": true
}
```

### T32 — Assign same teacher+subject to same class again
```
POST {{base_url}}/admin/classes/{{class_id}}/assign-teacher
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "teacher_id": "{{teacher_id}}",
  "subject": "Science",
  "is_classroom_teacher": false
}

Expected: 409
{ "detail": "Teacher is already assigned to this class for this subject" }
```

### T33 — Assign same teacher different subject (should work)
```
POST {{base_url}}/admin/classes/{{class_id}}/assign-teacher
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "teacher_id": "{{teacher_id}}",
  "subject": "Math",
  "is_classroom_teacher": false
}

Expected: 201
```

### T34 — Register student
```
POST {{base_url}}/admin/students/register
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "email": "student1@dps.com",
  "first_name": "Rohan",
  "last_name": "Mehta",
  "date_of_birth": "2008-09-12",
  "class_id": "{{class_id}}"
}

Expected: 201
{
  "message": "Student registered and enrolled. Login details sent to their email.",
  "student_id": "uuid...",
  "email": "student1@dps.com",
  "class": "Class 10 A"
}
```
→ Save: pm.environment.set("student_id", pm.response.json().student_id);

### T35 — Register student with class from another school
```
POST {{base_url}}/admin/students/register
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "email": "intruder@other.com",
  "first_name": "Bad",
  "last_name": "Actor",
  "date_of_birth": "2008-01-01",
  "class_id": "00000000-0000-0000-0000-000000000000"
}

Expected: 404
{ "detail": "Class not found" }
```

### T36 — List students in class
```
GET {{base_url}}/admin/classes/{{class_id}}/students
Headers: Authorization: Bearer {{access_token}}

Expected: 200
[
  {
    "student_id": "...",
    "first_name": "Rohan",
    "email": "student1@dps.com"
  }
]
```

### T37 — List all students
```
GET {{base_url}}/admin/students
Headers: Authorization: Bearer {{access_token}}

Expected: 200 — list of all students in this school
```

### T38 — Bulk register students via CSV
```
POST {{base_url}}/admin/students/bulk-register
Headers: Authorization: Bearer {{access_token}}
Body: form-data
  Key: file   Type: File   Value: bulk_students_template.csv
  (replace class_id in CSV with actual {{class_id}} before uploading)

Expected: 201
{
  "total_rows": 5,
  "successful_count": 4,
  "failed_count": 1,
  "successful": [...],
  "failed": [
    { "row": 3, "reason": "..." }
  ]
}
```

### T39 — Bulk register with wrong file type
```
POST {{base_url}}/admin/students/bulk-register
Headers: Authorization: Bearer {{access_token}}
Body: form-data
  Key: file   Type: File   Value: any_file.txt

Expected: 422
{ "detail": "Only .csv files are accepted" }
```

### T40 — Resend password to student
```
POST {{base_url}}/admin/students/{{student_id}}/resend-password
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{ "message": "New password generated and sent to student1@dps.com" }
```

### T41 — Deactivate student
```
POST {{base_url}}/admin/students/{{student_id}}/deactivate
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{ "message": "User student1@dps.com has been deactivated" }
```

### T42 — Deactivated student tries to login
```
POST {{base_url}}/auth/login
Body:
{
  "email": "student1@dps.com",
  "password": "<their password>"
}

Expected: 403
{ "detail": "Your account has been deactivated. Contact your school administrator." }
```
→ Reactivate: re-register with a different email for remaining tests

---

## PHASE 4 — TEACHER TESTS

### T43 — Login as teacher
```
POST {{base_url}}/auth/login
Body:
{
  "email": "science.teacher@dps.com",
  "password": "<password from welcome email>"
}

Expected: 200
{
  "is_password_changed": false,
  "user": { "role": "teacher" }
}
```

### T44 — Teacher accessing admin route (should fail)
```
POST {{base_url}}/admin/classes
Headers: Authorization: Bearer {{access_token}}
Body: { "class_name": "Hack", "grade_level": 1 }

Expected: 403
{ "detail": "Access denied. Required roles: ['admin']. Your role: teacher" }
```

### T45 — Teacher dashboard
```
GET {{base_url}}/teacher/dashboard
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "teacher": { "first_name": "Anil", "is_password_changed": false },
  "total_classes": 2,
  "classes": [
    {
      "class_name": "Class 10",
      "section": "A",
      "subject": "Science",
      "student_count": 1,
      "total_chapters": 0,
      "published_chapters": 0
    }
  ]
}
```

### T46 — Get chapters for class (empty initially)
```
GET {{base_url}}/teacher/classes/{{class_id}}/chapters
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "class_id": "...",
  "subject": "Science",
  "chapters": []
}
```

### T47 — Teacher accessing class they aren't assigned to
```
GET {{base_url}}/teacher/classes/00000000-0000-0000-0000-000000000000/chapters
Headers: Authorization: Bearer {{access_token}}

Expected: 403
{ "detail": "You are not assigned to this class" }
```

### T48 — Browse available global books
```
GET {{base_url}}/teacher/classes/{{class_id}}/books
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "grade_level": 10,
  "subject": "Science",
  "books": []   ← empty until sudo_admin adds books
}
```

---

## PHASE 5 — BOOK TESTS (sudo_admin)
Login as sudo_admin first (T03)

### T49 — Create global book
```
POST {{base_url}}/books/
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "book_name": "NCERT",
  "class_grade": 10,
  "subject": "science",
  "chapter_number": 1,
  "chapter_title": "Chemical Reactions and Equations",
  "summary": {
    "overview": "This chapter covers chemical reactions",
    "key_concepts": ["reactants", "products", "balancing equations"],
    "sections": [
      { "title": "What is a Chemical Reaction", "content": "A process that involves..." }
    ],
    "important_terms": [
      { "term": "Reactant", "definition": "Substance that reacts" }
    ],
    "takeaway": "Chemical reactions involve change in substances"
  },
  "qa_bank": {
    "questions": [
      {
        "question_number": 1,
        "type": "short_answer",
        "question": "What is a chemical reaction?",
        "answer": "A process that transforms reactants into products",
        "marks": 2
      }
    ]
  },
  "quiz": {
    "quiz_title": "Chapter 1 Quiz",
    "total_marks": 10,
    "questions": [
      {
        "question_number": 1,
        "question": "Which of the following is a chemical change?",
        "options": {
          "A": "Melting of ice",
          "B": "Burning of wood",
          "C": "Cutting of paper",
          "D": "Dissolving sugar"
        },
        "correct_option": "B",
        "explanation": "Burning involves a chemical change"
      }
    ]
  },
  "ppt_structure": {
    "presentation_title": "Chemical Reactions",
    "slides": [
      {
        "slide_number": 1,
        "slide_type": "title",
        "title": "Chemical Reactions and Equations",
        "bullet_points": [],
        "speaker_notes": "Welcome students"
      }
    ]
  },
  "isbn": "978-81-7450-123"
}

Expected: 201
{ "book_id": "uuid...", "book_name": "NCERT", "chapter_title": "Chemical Reactions..." }
```
→ Save: pm.environment.set("book_id", pm.response.json().book_id);

### T50 — Create duplicate book
```
POST {{base_url}}/books/
Headers: Authorization: Bearer {{access_token}}
Body: same as T49

Expected: 409
{ "detail": "Book already exists for NCERT / Class 10 / science / Chapter 1." }
```

### T51 — List books
```
GET {{base_url}}/books/
Headers: Authorization: Bearer {{access_token}}

Expected: 200 — array with the book
```

### T52 — List books filtered
```
GET {{base_url}}/books/?book_name=NCERT&class_grade=10
Headers: Authorization: Bearer {{access_token}}

Expected: 200 — filtered results
```

### T53 — Get book by ID
```
GET {{base_url}}/books/{{book_id}}
Headers: Authorization: Bearer {{access_token}}

Expected: 200 — full book object
```

### T54 — Search book by metadata
```
GET {{base_url}}/books/search?book_name=NCERT&class_grade=10&subject=science&chapter_number=1
Headers: Authorization: Bearer {{access_token}}

Expected: 200 — the book
```

### T55 — Update specific field only
```
PATCH {{base_url}}/books/{{book_id}}
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "chapter_title": "Chemical Reactions and Equations (Updated)"
}

Expected: 200 — book with updated chapter_title
```

### T56 — Update with no fields
```
PATCH {{base_url}}/books/{{book_id}}
Headers: Authorization: Bearer {{access_token}}
Body: {}

Expected: 422
{ "detail": "No fields provided to update" }
```

---

## PHASE 6 — CLASS CHAPTER TESTS (teacher)
Login as teacher first (T43)

### T57 — Teacher browses books (should now show NCERT book)
```
GET {{base_url}}/teacher/classes/{{class_id}}/books
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "books": [
    {
      "book_id": "{{book_id}}",
      "book_name": "NCERT",
      "chapter_number": 1,
      "is_assigned": false
    }
  ]
}
```

### T58 — Assign chapter to class
```
POST {{base_url}}/class-chapters/{{class_id}}/assign
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "book_id": "{{book_id}}",
  "teacher_id": "{{teacher_id}}",
  "chapter_title": "Chemical Reactions and Equations",
  "subject": "Science"
}

Expected: 201
{
  "class_chapter_id": "uuid...",
  "is_summary_overridden": false,
  "published_date": null
}
```
→ Save: pm.environment.set("class_chapter_id", pm.response.json().class_chapter_id);

### T59 — Assign same chapter to same class again
```
POST {{base_url}}/class-chapters/{{class_id}}/assign
Headers: Authorization: Bearer {{access_token}}
Body: same as T58

Expected: 409
{ "detail": "This chapter is already assigned to this class" }
```

### T60 — Get resolved content (teacher view — before publish)
```
GET {{base_url}}/class-chapters/{{class_chapter_id}}/content
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "chapter_title": "Chemical Reactions...",
  "summary": { "overview": "This chapter covers..." },  ← from global book
  "overrides": {
    "summary": false,
    "qa_bank": false,
    "quiz": false,
    "ppt_structure": false
  },
  "is_published": false
}
```

### T61 — Override summary
```
PATCH {{base_url}}/class-chapters/{{class_chapter_id}}/override/summary
Headers: Authorization: Bearer {{access_token}}
Body:
{
  "summary": {
    "overview": "Teacher's custom overview for Class 10A",
    "key_concepts": ["custom concept 1", "custom concept 2"],
    "sections": [],
    "important_terms": [],
    "takeaway": "Custom takeaway for this class"
  }
}

Expected: 200
{ "is_summary_overridden": true, "custom_summary": {...} }
```

### T62 — Get content after override
```
GET {{base_url}}/class-chapters/{{class_chapter_id}}/content
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "summary": { "overview": "Teacher's custom overview..." },  ← teacher's version
  "overrides": { "summary": true }
}
```

### T63 — Student tries to access before publish
Register a fresh student and login as them first, then:
```
GET {{base_url}}/class-chapters/{{class_chapter_id}}/student-view
Headers: Authorization: Bearer <student_token>

Expected: 403
{ "detail": "This chapter has not been published yet" }
```

### T64 — Publish chapter (as teacher)
```
POST {{base_url}}/class-chapters/{{class_chapter_id}}/publish
Headers: Authorization: Bearer <teacher_token>

Expected: 200
{
  "message": "Chapter published successfully",
  "published_date": "2024-..."
}
```

### T65 — Student accesses after publish
```
GET {{base_url}}/class-chapters/{{class_chapter_id}}/student-view
Headers: Authorization: Bearer <student_token>

Expected: 200
{
  "summary": { "overview": "Teacher's custom overview..." },  ← teacher's version
  "overrides": { "summary": true }
}
```

### T66 — Reset summary override
```
POST {{base_url}}/class-chapters/{{class_chapter_id}}/reset-overrides
Headers: Authorization: Bearer <teacher_token>
Body:
{
  "fields": ["summary"]
}

Expected: 200
{ "is_summary_overridden": false }
```

### T67 — Get content after reset (should show global again)
```
GET {{base_url}}/class-chapters/{{class_chapter_id}}/content
Headers: Authorization: Bearer <teacher_token>

Expected: 200
{
  "summary": { "overview": "This chapter covers..." },  ← back to global
  "overrides": { "summary": false }
}
```

### T68 — Unpublish chapter
```
POST {{base_url}}/class-chapters/{{class_chapter_id}}/unpublish
Headers: Authorization: Bearer <teacher_token>

Expected: 200
{ "message": "Chapter unpublished successfully" }
```

### T69 — Student tries to access unpublished chapter
```
GET {{base_url}}/class-chapters/{{class_chapter_id}}/student-view
Headers: Authorization: Bearer <student_token>

Expected: 403
{ "detail": "This chapter has not been published yet" }
```

---

## PHASE 7 — STUDENT TESTS

### T70 — Login as student
```
POST {{base_url}}/auth/login
Body:
{
  "email": "student1@dps.com",
  "password": "<password from welcome email>"
}

Expected: 200
{
  "is_password_changed": false,
  "user": { "role": "student" }
}
```

### T71 — Student accessing teacher route (should fail)
```
GET {{base_url}}/teacher/dashboard
Headers: Authorization: Bearer {{access_token}}

Expected: 403
{ "detail": "Access denied. Required roles: ['teacher']. Your role: student" }
```

### T72 — Student dashboard
```
GET {{base_url}}/student/dashboard
Headers: Authorization: Bearer {{access_token}}

Expected: 200
{
  "student": { "first_name": "Rohan", "is_password_changed": false },
  "class": {
    "class_name": "Class 10",
    "section": "A",
    "school_name": "Delhi Public School"
  },
  "teachers": [
    { "first_name": "Anil", "subject": "Science", "is_classroom_teacher": true }
  ],
  "published_chapters": [],   ← empty because chapter was unpublished in T68
  "quiz_summary": {
    "total_attempts": 0,
    "average_score": 0.0,
    "recent_attempts": []
  }
}
```

### T73 — Publish chapter again and check student dashboard
```
(login as teacher, publish chapter — T64 again)
(login as student)
GET {{base_url}}/student/dashboard

Expected: published_chapters now shows the chapter
```

### T74 — Student list published chapters
```
GET {{base_url}}/student/chapters
Headers: Authorization: Bearer <student_token>

Expected: 200
[
  {
    "class_chapter_id": "{{class_chapter_id}}",
    "chapter_title": "Chemical Reactions...",
    "subject": "Science"
  }
]
```

### T75 — Student list chapters for their class
```
GET {{base_url}}/class-chapters/student/class/{{class_id}}
Headers: Authorization: Bearer <student_token>

Expected: 200 — list of published chapters
```

### T76 — Student accessing another class's chapters
```
GET {{base_url}}/class-chapters/student/class/00000000-0000-0000-0000-000000000000
Headers: Authorization: Bearer <student_token>

Expected: 403
{ "detail": "You are not enrolled in this class" }
```

### T77 — Student quiz history (empty initially)
```
GET {{base_url}}/student/quiz-history
Headers: Authorization: Bearer <student_token>

Expected: 200
[]
```

---

## PHASE 8 — EDGE CASE TESTS

### T78 — Expired token test
```
(wait 30 min or manually expire by changing SECRET_KEY temporarily)
GET {{base_url}}/auth/me
Headers: Authorization: Bearer <old_access_token>

Expected: 401
{ "detail": "Token is invalid or expired" }
```

### T79 — Malformed token
```
GET {{base_url}}/auth/me
Headers: Authorization: Bearer thisisnotavalidtoken

Expected: 401
{ "detail": "Token is invalid or expired" }
```

### T80 — Invalid UUID in path
```
GET {{base_url}}/books/not-a-uuid
Headers: Authorization: Bearer {{access_token}}

Expected: 422 (FastAPI validation error)
```

### T81 — Missing required field in body
```
POST {{base_url}}/admin/classes
Headers: Authorization: Bearer <admin_token>
Body:
{
  "class_name": "Class 9"
  (missing grade_level)
}

Expected: 422
{ "detail": [{ "msg": "field required", "loc": ["body", "grade_level"] }] }
```

### T82 — Invalid email format
```
POST {{base_url}}/admin/teachers/register
Headers: Authorization: Bearer <admin_token>
Body:
{
  "email": "notanemail",
  "first_name": "Test",
  "date_of_birth": "1990-01-01"
}

Expected: 422
{ "detail": [{ "msg": "value is not a valid email address" }] }
```

### T83 — Invalid date format
```
POST {{base_url}}/admin/students/register
Headers: Authorization: Bearer <admin_token>
Body:
{
  "email": "test@test.com",
  "first_name": "Test",
  "date_of_birth": "20-01-1990",
  "class_id": "{{class_id}}"
}

Expected: 422
```

### T84 — Delete book
```
DELETE {{base_url}}/books/{{book_id}}
Headers: Authorization: Bearer <sudo_admin_token>

Expected: 200
{ "message": "Book uuid... deleted successfully" }
```

### T85 — Get deleted book
```
GET {{base_url}}/books/{{book_id}}
Headers: Authorization: Bearer <sudo_admin_token>

Expected: 404
{ "detail": "Book not found" }
```

---

## TESTING CHECKLIST

Copy this and tick off as you test:

### Auth
- [ ] T03 Login sudo_admin
- [ ] T04 Wrong password
- [ ] T05 Non-existent email
- [ ] T06 Get profile
- [ ] T07 No token
- [ ] T08 Refresh token
- [ ] T09 Wrong token type for refresh
- [ ] T10 Change password
- [ ] T11 Wrong old password
- [ ] T12 Same password

### Sudo Admin
- [ ] T13 Create school
- [ ] T14 Duplicate school
- [ ] T15 List schools
- [ ] T16 Get school by ID
- [ ] T17 Invalid school ID
- [ ] T18 Create admin
- [ ] T19 Duplicate admin for school

### Admin
- [ ] T22 Login admin
- [ ] T23 Admin accessing sudo route
- [ ] T24 Create class
- [ ] T25 Duplicate class
- [ ] T27 List classes
- [ ] T28 Register teacher
- [ ] T29 Duplicate teacher email
- [ ] T30 List teachers
- [ ] T31 Assign teacher to class
- [ ] T32 Duplicate teacher assignment
- [ ] T33 Same teacher different subject
- [ ] T34 Register student
- [ ] T35 Student wrong class
- [ ] T36 List students in class
- [ ] T37 List all students
- [ ] T38 Bulk CSV upload
- [ ] T39 Wrong file type
- [ ] T40 Resend password
- [ ] T41 Deactivate student
- [ ] T42 Deactivated user login

### Teacher
- [ ] T43 Login teacher
- [ ] T44 Teacher accessing admin route
- [ ] T45 Teacher dashboard
- [ ] T46 Chapters (empty)
- [ ] T47 Unassigned class
- [ ] T48 Browse books

### Books
- [ ] T49 Create book
- [ ] T50 Duplicate book
- [ ] T51 List books
- [ ] T52 Filter books
- [ ] T53 Get by ID
- [ ] T54 Search by metadata
- [ ] T55 Update field
- [ ] T56 Update no fields

### Class Chapters
- [ ] T57 Books now visible to teacher
- [ ] T58 Assign chapter
- [ ] T59 Duplicate assignment
- [ ] T60 Get content before publish
- [ ] T61 Override summary
- [ ] T62 Content after override
- [ ] T63 Student before publish
- [ ] T64 Publish chapter
- [ ] T65 Student after publish
- [ ] T66 Reset override
- [ ] T67 Content after reset
- [ ] T68 Unpublish
- [ ] T69 Student after unpublish

### Student
- [ ] T70 Login student
- [ ] T71 Student accessing teacher route
- [ ] T72 Student dashboard
- [ ] T73 Dashboard after publish
- [ ] T74 List published chapters
- [ ] T75 List via class ID
- [ ] T76 Wrong class
- [ ] T77 Quiz history empty

### Edge Cases
- [ ] T79 Malformed token
- [ ] T80 Invalid UUID
- [ ] T81 Missing required field
- [ ] T82 Invalid email
- [ ] T83 Invalid date
- [ ] T84 Delete book
- [ ] T85 Get deleted book
- [ ] T21 Deactivate school (do this last)