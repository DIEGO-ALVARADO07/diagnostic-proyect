from enum import Enum


class Permission(str, Enum):
    READ_USERS = "read_users"
    UPDATE_USERS = "update_users"
    CREATE_USERS = "create_users"
    DELETE_USERS = "delete_users"
    READ_OWN_PROFILE = "read_own_profile"
    UPDATE_OWN_PROFILE = "update_own_profile"
    UPLOAD_EXCEL = "upload_excel"