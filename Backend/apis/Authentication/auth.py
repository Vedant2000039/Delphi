# ===================================================================
# File: backend/apis/Authentication/auth.py
#
# Description:
# This module handles Email OTP Authentication for Delphi AI.
#
# Features:
# 1. Verify Email OTP
# 2. Resend OTP
# 3. Send OTP Email using SMTP
# 4. Fetch User Details after Verification
# ====================================================================

from datetime import datetime, timedelta
import os
import random
import smtplib
import string

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

class VerifyOTPRequest(BaseModel):
    """
    Request model used for OTP verification.
    """
    email: EmailStr
    otp_code: str


class ResendOTPRequest(BaseModel):
    """
    Request model used for resending OTP.
    """
    email: EmailStr


# ==============================================================================
# Helper Function : Send OTP Email
# ==============================================================================

def send_otp_email(to_email: str, otp: str):
    """
    Sends OTP email to the user using SMTP.

    Parameters
    ----------
    to_email : str
        Recipient email address

    otp : str
        6-digit verification code
    """

    # SMTP Configuration (Loaded from Environment Variables)
    smtp_host = os.getenv("SMTP_HOST", "smtp.zoho.in")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    # Add spaces between OTP digits for better readability
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
    msg["Subject"] = "Delphi AI - Email Verification Code"
    msg["From"] = smtp_user
    msg["To"] = to_email

    # Plain Text Version
    msg.attach(
        MIMEText(
            f"Your Delphi AI OTP is: {otp}\nExpires in 10 minutes.",
            "plain"
        )
    )

    # HTML Version
    msg.attach(MIMEText(html, "html"))

    # --------------------------------------------------------------------------
    # Send Email
    # --------------------------------------------------------------------------

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            # Login to SMTP Server
            server.login(smtp_user, smtp_password)

            # Send Email
            server.sendmail(
                smtp_user,
                to_email,
                msg.as_string()
            )

            print(f"OTP email sent successfully to {to_email}")

    except Exception as e:
        print(f"SMTP Error: {e}")
        raise


# ==============================================================================
# API : Verify OTP
# ==============================================================================

@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    """
    Verifies the OTP entered by the user.

    Steps:
    1. Fetch latest active OTP
    2. Check OTP exists
    3. Check OTP expiry
    4. Validate OTP
    5. Mark OTP as used
    6. Verify user's email
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
                o.is_used,
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

        # Check Expiry
        if datetime.now() > otp_row["otp_expiry"]:
            raise HTTPException(
                status_code=400,
                detail="OTP has expired. Please request a new one."
            )

        # Check OTP Match
        if otp_row["otp_code"] != req.otp_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP. Please check and try again."
            )

        # ----------------------------------------------------------------------
        # Mark OTP as Used
        # ----------------------------------------------------------------------

        cur.execute("""
            UPDATE tbl_user_email_otp
            SET is_used = 1
            WHERE otp_id = %s
        """, (otp_row["otp_id"],))

        # ----------------------------------------------------------------------
        # Mark Email as Verified
        # ----------------------------------------------------------------------

        cur.execute("""
            UPDATE Mst_tbldelphiusers
            SET email_verified = 1
            WHERE user_id = %s
        """, (otp_row["user_id"],))

        conn.commit()

        return {
            "message": "Email verified successfully. You can now log in."
        }

    finally:
        cur.close()
        conn.close()


# ==============================================================================
# API : Resend OTP
# ==============================================================================

@router.post("/resend-otp")
def resend_otp(req: ResendOTPRequest):
    """
    Generates and sends a new OTP.

    Steps:
    1. Check if user exists
    2. Ensure email is not already verified
    3. Invalidate previous OTPs
    4. Generate new OTP
    5. Save OTP in database
    6. Send OTP Email
    """

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------------------------
        # Fetch User
        # ----------------------------------------------------------------------

        cur.execute("""
            SELECT
                user_id,
                email_verified
            FROM Mst_tbldelphiusers
            WHERE email = %s
        """, (req.email,))

        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Email not found. Please register first."
            )

        if user["email_verified"] == 1:
            raise HTTPException(
                status_code=400,
                detail="Email is already verified. Please login."
            )

        # ----------------------------------------------------------------------
        # Invalidate Existing OTPs
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

        # Save OTP
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
            "message": "New OTP sent to your email."
        }

    finally:
        cur.close()
        conn.close()


# ==============================================================================
# API : Get User By Email
# ==============================================================================

@router.get("/user-by-email")
def get_user_by_email(email: str):
    """
    Returns user details after successful OTP verification.

    Used by the frontend to store authenticated user
    information (including user_id) in localStorage.
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
                u.company_name,
                u.email,
                r.role_name
            FROM Mst_tbldelphiusers u
            JOIN Mst_delphirole r
                ON u.role_id = r.role_id
            WHERE u.email = %s
              AND u.is_active = 1
        """, (email,))

        user = cur.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return {
            "success": True,
            "user": user
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cur.close()
        conn.close()