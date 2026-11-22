import unittest

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.exceptions import ApplicationError
from modules.security.dtos.requests.auth import LoginRequest
from modules.security.dependencies import require_roles
from modules.security.entities import AccessToken, Account, AuthBase
from modules.security.entities.permission import Permission
from modules.security.entities.role import Role, has_permission
from modules.security.security import hash_password, verify_password
from modules.security.services.auth_service import AuthService
from modules.security.services.user_service import UserService
from modules.security.dtos.requests.users import (
    UserCreateRequest as UserCreate,
    UserUpdateRequest as UserUpdate,
)


class PasswordSecurityTests(unittest.TestCase):
    def test_password_hash_verifies_only_the_original_password(self) -> None:
        password = "long-enough-test-password"
        password_hash = hash_password(password)

        self.assertNotIn(password, password_hash)
        self.assertTrue(verify_password(password, password_hash))
        self.assertFalse(verify_password("another-password", password_hash))
        self.assertFalse(verify_password(password, "invalid-hash"))


class EntityOrganizationTests(unittest.TestCase):
    def test_existing_imports_resolve_to_entities_package(self) -> None:
        self.assertEqual(Account.__module__, "modules.security.entities.account")
        self.assertEqual(AccessToken.__module__, "modules.security.entities.access_token")
        self.assertEqual(Role.__module__, "modules.security.entities.role")
        self.assertEqual(Permission.__module__, "modules.security.entities.permission")


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

        with self.assertRaises(ApplicationError) as error:
            instructor_only(student)

        self.assertEqual(error.exception.status_code, 403)


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        AuthBase.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.account = Account(
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            password_hash=hash_password("long-enough-password"),
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.session.add(self.account)
        self.session.commit()
        self.service = AuthService(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_login_returns_safe_user_dto_and_stores_only_token_hash(self) -> None:
        response = self.service.login(
            LoginRequest(username="ADMIN", password="long-enough-password")
        )
        stored_token = self.session.scalar(select(AccessToken))

        self.assertIsNotNone(stored_token)
        self.assertNotEqual(stored_token.token_hash, response.access_token)
        self.assertNotIn("password_hash", response.user.model_dump())
        self.assertEqual(response.user.username, "admin")

    def test_login_rejects_bad_credentials_with_bearer_challenge(self) -> None:
        with self.assertRaises(ApplicationError) as error:
            self.service.login(LoginRequest(username="admin", password="incorrect"))

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.headers, {"WWW-Authenticate": "Bearer"})


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
        self.superadmin = Account(
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.session.add_all(
            (self.student, self.other_student, self.instructor, self.superadmin)
        )
        self.session.commit()
        self.service = UserService(self.session)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_student_cannot_read_or_edit_another_account(self) -> None:
        with self.assertRaises(ApplicationError) as read_error:
            self.service.read_user(self.other_student.id, self.student)
        self.assertEqual(read_error.exception.status_code, 403)

        with self.assertRaises(ApplicationError) as update_error:
            self.service.update_user(
                self.other_student.id,
                UserUpdate(full_name="Changed"),
                self.student,
            )
        self.assertEqual(update_error.exception.status_code, 403)

    def test_student_can_edit_own_profile(self) -> None:
        updated = self.service.update_user(
            self.student.id,
            UserUpdate(full_name="Updated Name"),
            self.student,
        )

        self.assertEqual(updated.full_name, "Updated Name")

    def test_instructor_cannot_change_another_users_password(self) -> None:
        with self.assertRaises(ApplicationError) as error:
            self.service.update_user(
                self.other_student.id,
                UserUpdate(password="new-secure-password"),
                self.instructor,
            )

        self.assertEqual(error.exception.status_code, 403)

    def test_user_response_does_not_expose_password_hash(self) -> None:
        response = self.service.read_my_profile(self.student)

        self.assertNotIn("password_hash", response.model_dump())
        self.assertNotIn("password", response.model_dump())

    def test_non_admin_cannot_create_accounts_through_service(self) -> None:
        payload = UserCreate(
            username="new-user",
            email="new@example.com",
            full_name="New User",
            password="long-enough-password",
            role=Role.ESTUDIANTE.value,
        )

        with self.assertRaises(ApplicationError) as error:
            self.service.create_user(payload, self.instructor)

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
