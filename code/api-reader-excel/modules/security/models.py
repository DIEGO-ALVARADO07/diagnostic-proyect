"""Compatibility imports for the original ORM model module."""

from modules.security.entities import AccessToken, Account, AuthBase, utcnow

__all__ = ["AccessToken", "Account", "AuthBase", "utcnow"]
