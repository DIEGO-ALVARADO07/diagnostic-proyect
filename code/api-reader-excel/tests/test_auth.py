import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.dependencies import require_roles
from auth.models import Account, AuthBase
from auth.permission import Permission
from auth.role import Role, has_permission
from auth.security import hash_password, verify_password
from auth.user import UserCreate, UserUpdate
from users.routes import read_user, update_user


class PasswordSecurityTests(unittest.TestCase):
    def test_password_hash_verifies_only_the_original_password(self) -> None:
        password = "long-enough-test-password"
        password_hash = hash_password(password)

        self.assertNotIn(password, password_hash)
        self.assertTrue(verify_password(password, password_hash))
        self.assertFalse(verify_password("another-password", password_hash))
        self.assertFalse(verify_password(password, "invalid-hash"))


class RolePermissionTests(unittest.TestCase):
    def test_student_cannot_read_other_users_or_upload_excel(self) -> None:
        self.assertTrue(has_permission(Role.ESTUDIANTE, Permission.READ_OWN_PROFILE))
        self.assertFalse(has_permission(Role.ESTUDIANTE, Permission.READ_USERS))
        self.assertFalse(has_permission(Role.ESTUDIANTE, Permission.UPLOAD_EXCEL))

    def test_instructor_can_upload_but_cannot_delete_users(self) -> None:
        self.assertTrue(has_permission(Role.INSTRUCTOR, Permission.UPLOAD_EXCEL))
        self.assertFalse(has_permission(Role.INSTRUCTOR, Permission.DELETE_USERS))

    def test_role_dependency_rejects_student_for_instructor_action(self) -> None:
        instructor_only = require_roles(Role.INSTRUCTOR)
        student = Account(
            id=3,
            username="student",
            email="student@example.com",
            full_name="Student",
            password_hash="unused",
            role=Role.ESTUDIANTE.value,
            is_active=True,
        )

        with self.assertRaises(HTTPException) as error:
            instructor_only(student)

        self.assertEqual(error.exception.status_code, 403)


class UserScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        AuthBase.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.student = Account(
            username="student",
            email="student@example.com",
            full_name="Student",
            password_hash="unused",
            role=Role.ESTUDIANTE.value,
            is_active=True,
        )
        self.other_student = Account(
            username="other",
            email="other@example.com",
            full_name="Other Student",
            password_hash="unused",
            role=Role.ESTUDIANTE.value,
            is_active=True,
        )
        self.instructor = Account(
            username="instructor",
            email="instructor@example.com",
            full_name="Instructor",
            password_hash="unused",
            role=Role.INSTRUCTOR.value,
            is_active=True,
        )
        self.session.add_all((self.student, self.other_student, self.instructor))
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_student_cannot_read_or_edit_another_account(self) -> None:
        with self.assertRaises(HTTPException) as read_error:
            read_user(self.other_student.id, self.student, self.session)
        self.assertEqual(read_error.exception.status_code, 403)

        with self.assertRaises(HTTPException) as update_error:
            update_user(
                self.other_student.id,
                UserUpdate(full_name="Changed"),
                self.student,
                self.session,
            )
        self.assertEqual(update_error.exception.status_code, 403)

    def test_student_can_edit_own_profile(self) -> None:
        updated = update_user(
            self.student.id,
            UserUpdate(full_name="Updated Name"),
            self.student,
            self.session,
        )

        self.assertEqual(updated.full_name, "Updated Name")

    def test_instructor_cannot_change_another_users_password(self) -> None:
        with self.assertRaises(HTTPException) as error:
            update_user(
                self.other_student.id,
                UserUpdate(password="new-secure-password"),
                self.instructor,
                self.session,
            )

        self.assertEqual(error.exception.status_code, 403)

    def test_public_account_creation_cannot_assign_superadmin(self) -> None:
        with self.assertRaises(ValidationError):
            UserCreate(
                username="new-user",
                email="new@example.com",
                full_name="New User",
                password="long-enough-password",
                role=Role.SUPERADMIN.value,
            )
