# ==============================================================================
# File: backend/apis/Authentication/forgot_password.py
#
# Description:
# This module handles the Forgot Password functionality for Delphi AI.
#
# Features:
# 1. Send Password Reset OTP
# 2. Verify Password Reset OTP
# 3. Reset User Password
# 4. Send OTP Email using SMTP
# ==============================================================================

from datetime import datetime, timedelta
import os
import random
import smtplib
import string

import bcrypt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from db import get_conn

# ------------------------------------------------------------------------------
# Router Initialization
# ------------------------------------------------------------------------------

router = APIRouter()


# ==============================================================================
# Request Models
# ==============================================================================

class ForgotPasswordRequest(BaseModel):
    """
    Request model for initiating forgot password.
    """
    email: EmailStr


class VerifyForgotOTPRequest(BaseModel):
    """
    Request model for verifying the password reset OTP.
    """
    email: EmailStr
    otp_code: str


class ResetPasswordRequest(BaseModel):
    """
    Request model for resetting password.
    """
    email: EmailStr
    otp_code: str
    new_password: str


# ==============================================================================
# Helper Function : Send Password Reset OTP Email
# ==============================================================================

def send_otp_email(to_email: str, otp: str):
    """
    Sends a Password Reset OTP to the user's email.

    Parameters
    ----------
    to_email : str
        Recipient email address.

    otp : str
        6-digit OTP used for password reset.
    """

    # --------------------------------------------------------------------------
    # SMTP Configuration
    # --------------------------------------------------------------------------

    smtp_host = os.getenv("SMTP_HOST", "smtp.zoho.in")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    # Format OTP for better readability
    otp_spaced = " ".join(list(otp))

    # --------------------------------------------------------------------------
    # HTML Email Template
    # --------------------------------------------------------------------------

    html = f"""
    <!DOCTYPE html>
    <html>
    ...
    {otp_spaced}
    ...
    </html>
    """

    # --------------------------------------------------------------------------
    # Create Email Message
    # --------------------------------------------------------------------------

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Delphi AI - Password Reset Code"
    msg["From"] = smtp_user
    msg["To"] = to_email

    # Plain Text Email
    msg.attach(
        MIMEText(
            f"Your Delphi AI password reset OTP is: {otp}\nExpires in 10 minutes.",
            "plain"
        )
    )

    # HTML Email
    msg.attach(MIMEText(html, "html"))

    # --------------------------------------------------------------------------
    # Send Email
    # --------------------------------------------------------------------------

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(smtp_user, smtp_password)

            server.sendmail(
                smtp_user,
                to_email,
                msg.as_string()
            )

            print(f"Password reset OTP sent successfully to {to_email}")

    except Exception as e:
        print(f"SMTP Error: {e}")
        raise


# ==============================================================================
# API : Forgot Password
# ==============================================================================

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    """
    Generates a password reset OTP and sends it to the user's email.

    Workflow
    --------
    1. Verify user exists
    2. Ensure account is active
    3. Invalidate previous OTPs
    4. Generate a new OTP
    5. Store OTP in database
    6. Send OTP via email
    """

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------------------------
        # Check Whether User Exists
        # ----------------------------------------------------------------------

        cur.execute("""
            SELECT
                user_id,
                is_active
            FROM Mst_tbldelphiusers
            WHERE email = %s
        """, (req.email,))

        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="No account found with this email."
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=403,
                detail="Account is deactivated."
            )

        # ----------------------------------------------------------------------
        # Invalidate Previous Active OTPs
        # ----------------------------------------------------------------------

        cur.execute("""
            UPDATE tbl_user_email_otp
            SET is_used = 1
            WHERE user_id = %s
              AND is_used = 0
        """, (user["user_id"],))

        # ----------------------------------------------------------------------
        # Generate New OTP
        # ----------------------------------------------------------------------

        otp_code = "".join(random.choices(string.digits, k=6))
        otp_expiry = datetime.now() + timedelta(minutes=10)

        # ----------------------------------------------------------------------
        # Store OTP in Database
        # ----------------------------------------------------------------------

        cur.execute("""
            INSERT INTO tbl_user_email_otp
            (
                user_id,
                email,
                otp_code,
                otp_expiry,
                is_used
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                0
            )
        """, (
            user["user_id"],
            req.email,
            otp_code,
            otp_expiry
        ))

        conn.commit()

        # ----------------------------------------------------------------------
        # Send OTP Email
        # ----------------------------------------------------------------------

        try:
            send_otp_email(req.email, otp_code)

        except Exception as e:
            print(f"Email send error: {e}")

            raise HTTPException(
                status_code=500,
                detail="Failed to send OTP email. Please try again."
            )

        return {
            "message": "Password reset OTP sent to your email.",
            "email": req.email
        }

    finally:
        cur.close()
        conn.close()


# ==============================================================================
# API : Verify Forgot Password OTP
# ==============================================================================

@router.post("/verify-forgot-otp")
def verify_forgot_otp(req: VerifyForgotOTPRequest):
    """
    Verifies the OTP entered by the user before allowing
    password reset.

    Workflow
    --------
    1. Fetch latest active OTP
    2. Check OTP exists
    3. Validate expiry
    4. Validate OTP
    """

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------------------------
        # Fetch Latest Active OTP
        # ----------------------------------------------------------------------

        cur.execute("""
            SELECT
                o.otp_id,
                o.otp_code,
                o.otp_expiry,
                u.user_id
            FROM tbl_user_email_otp o
            JOIN Mst_tbldelphiusers u
                ON o.user_id = u.user_id
            WHERE o.email = %s
              AND o.is_used = 0
            ORDER BY o.created_at DESC
            LIMIT 1
        """, (req.email,))

        otp_row = cur.fetchone()

        # ----------------------------------------------------------------------
        # OTP Validation
        # ----------------------------------------------------------------------

        if not otp_row:
            raise HTTPException(
                status_code=400,
                detail="No active OTP found. Please request a new one."
            )

        if datetime.now() > otp_row["otp_expiry"]:
            raise HTTPException(
                status_code=400,
                detail="OTP has expired. Please request a new one."
            )

        if otp_row["otp_code"] != req.otp_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP. Please check and try again."
            )

        return {
            "message": "OTP verified. You can now reset your password."
        }

    finally:
        cur.close()
        conn.close()


# ==============================================================================
# API : Reset Password
# ==============================================================================

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    """
    Resets the user's password after successful OTP verification.

    Workflow
    --------
    1. Validate latest OTP
    2. Validate password strength
    3. Hash new password
    4. Update password
    5. Mark OTP as used
    """

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------------------------
        # Fetch Latest Active OTP
        # ----------------------------------------------------------------------

        cur.execute("""
            SELECT
                o.otp_id,
                o.otp_code,
                o.otp_expiry,
                u.user_id
            FROM tbl_user_email_otp o
            JOIN Mst_tbldelphiusers u
                ON o.user_id = u.user_id
            WHERE o.email = %s
              AND o.is_used = 0
            ORDER BY o.created_at DESC
            LIMIT 1
        """, (req.email,))

        otp_row = cur.fetchone()

        # ----------------------------------------------------------------------
        # OTP Validation
        # ----------------------------------------------------------------------

        if not otp_row:
            raise HTTPException(
                status_code=400,
                detail="No active OTP found. Please restart the process."
            )

        if datetime.now() > otp_row["otp_expiry"]:
            raise HTTPException(
                status_code=400,
                detail="OTP has expired. Please request a new one."
            )

        if otp_row["otp_code"] != req.otp_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP."
            )

        # ----------------------------------------------------------------------
        # Password Validation
        # ----------------------------------------------------------------------

        if len(req.new_password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 6 characters."
            )

        # ----------------------------------------------------------------------
        # Hash Password Using BCrypt
        # ----------------------------------------------------------------------

        hashed_password = bcrypt.hashpw(
            req.new_password.encode(),
            bcrypt.gensalt()
        ).decode()

        # ----------------------------------------------------------------------
        # Update User Password
        # ----------------------------------------------------------------------

        cur.execute("""
            UPDATE Mst_tbldelphiusers
            SET password = %s
            WHERE user_id = %s
        """, (
            hashed_password,
            otp_row["user_id"]
        ))

        # ----------------------------------------------------------------------
        # Mark OTP as Used
        # ----------------------------------------------------------------------

        cur.execute("""
            UPDATE tbl_user_email_otp
            SET is_used = 1
            WHERE otp_id = %s
        """, (otp_row["otp_id"],))

        conn.commit()

        return {
            "message": "Password reset successfully. You can now log in."
        }

    finally:
        cur.close()
        conn.close()