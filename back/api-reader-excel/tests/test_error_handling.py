import asyncio
import json
import unittest

from app import app
from core.exceptions import ApplicationError
from modules.security.dependencies import get_current_token


class ApplicationErrorHandlerTests(unittest.TestCase):
    """Las dependencias de seguridad ya no usan HTTPException: la respuesta
    debe conservar el mismo formato ({"detail": ...}) y cabeceras."""

    def _render(self, error: ApplicationError):
        handler = app.exception_handlers[ApplicationError]
        return asyncio.run(handler(None, error))

    def test_missing_credentials_keep_401_contract(self) -> None:
        with self.assertRaises(ApplicationError) as context:
            get_current_token(None, db=None)

        response = self._render(context.exception)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(
            json.loads(response.body),
            {"detail": "Credenciales de acceso inválidas o vencidas."},
        )

    def test_structured_detail_is_preserved(self) -> None:
        response = self._render(
            ApplicationError(422, {"message": "x", "available_sheets": ["A"]})
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            json.loads(response.body),
            {"detail": {"message": "x", "available_sheets": ["A"]}},
        )


if __name__ == "__main__":
    unittest.main()
