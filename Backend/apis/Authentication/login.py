# ==============================================================================
# File: backend/apis/Authentication/login.py
#
# Description:
# This module handles user authentication for Delphi AI.
#
# Features:
# 1. Authenticate registered users
# 2. Verify email verification status
# 3. Verify account activation status
# 4. Validate password using BCrypt
# 5. Return authenticated user details
# ==============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import bcrypt

from db import get_conn

# ------------------------------------------------------------------------------
# Router Initialization
# ------------------------------------------------------------------------------

router = APIRouter()


# ==============================================================================
# Request Models
# ==============================================================================

class LoginRequest(BaseModel):
    """
    Request model for user login.
    """

    email: EmailStr
    password: str


# ==============================================================================
# API : User Login
# ==============================================================================

@router.post("/login")
def login(req: LoginRequest):
    """
    Authenticates a user using email and password.

    Workflow
    --------
    1. Check whether the user exists.
    2. Verify the account is active.
    3. Verify the email has been verified.
    4. Validate the password using BCrypt.
    5. Return authenticated user information.
    """

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------------------------
        # Fetch User Details
        # ----------------------------------------------------------------------

        cur.execute("""
            SELECT
                u.user_id,
                u.user_first_name,
                u.user_last_name,
                u.email,
                u.password,
                u.email_verified,
                u.is_active,
                u.role_id,
                r.role_name,
                u.company_name
            FROM Mst_tbldelphiusers u
            JOIN Mst_delphirole r
                ON u.role_id = r.role_id
            WHERE u.email = %s
        """, (req.email,))

        user = cur.fetchone()

        # ----------------------------------------------------------------------
        # Validate User Existence
        # ----------------------------------------------------------------------

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # ----------------------------------------------------------------------
        # Check Account Status
        # ----------------------------------------------------------------------

        if not user["is_active"]:
            raise HTTPException(
                status_code=403,
                detail="Account is deactivated"
            )

        # ----------------------------------------------------------------------
        # Check Email Verification Status
        # ----------------------------------------------------------------------

        if not user["email_verified"]:
            raise HTTPException(
                status_code=403,
                detail="Email not verified. Please verify your OTP first."
            )

        # ----------------------------------------------------------------------
        # Verify Password Using BCrypt
        # ----------------------------------------------------------------------

        password_match = bcrypt.checkpw(
            req.password.encode(),
            user["password"].encode()
        )

        if not password_match:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # ----------------------------------------------------------------------
        # Return Authenticated User Details
        # ----------------------------------------------------------------------

        return {
            "message": "Login successful",
            "user": {
                "user_id": user["user_id"],
                "full_name": f"{user['user_first_name']} {user['user_last_name']}",
                "email": user["email"],
                "role_id": user["role_id"],
                "role_name": user["role_name"],
                "company_name": user["company_name"]
            }
        }

    finally:
        # ----------------------------------------------------------------------
        # Close Database Resources
        # ----------------------------------------------------------------------

        cur.close()
        conn.close()