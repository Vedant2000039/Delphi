# ==============================================================================
# File: backend/apis/Authentication/register.py
#
# Description:
# This module handles user registration for Delphi AI.
#
# Features:
# 1. Register new users
# 2. Check existing user accounts
# 3. Generate Email Verification OTP
# 4. Send OTP via Email
# 5. Store OTP in Database
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
# Request Model
# ==============================================================================

class RegisterRequest(BaseModel):
    """
    Request model for user registration.
    """

    first_name: str
    last_name: str
    company_name: str
    email: EmailStr
    password: str


# ==============================================================================
# Helper Function : Send Email Verification OTP
# ==============================================================================

def send_otp_email(to_email: str, otp: str):
    """
    Sends the Email Verification OTP to the registered email.

    Parameters
    ----------
    to_email : str
        Recipient email address.

    otp : str
        Six-digit verification code.
    """

    # --------------------------------------------------------------------------
    # SMTP Configuration
    # --------------------------------------------------------------------------

    smtp_host = os.getenv("SMTP_HOST", "smtp.zoho.in")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    # Display OTP with spaces for better readability
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

    # Plain Text Email
    msg.attach(
        MIMEText(
            f"Your Delphi AI OTP is: {otp}\nExpires in 10 minutes.",
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

            print(f"OTP email sent successfully to {to_email}")

    except Exception as e:
        print(f"SMTP Error: {e}")
        raise


# ==============================================================================
# API : User Registration
# ==============================================================================

@router.post("/register")
def register(req: RegisterRequest):
    """
    Registers a new user and sends an Email Verification OTP.

    Workflow
    --------
    1. Check if the email already exists.
    2. If verified, prevent duplicate registration.
    3. If unverified, generate and resend a new OTP.
    4. Hash the user's password.
    5. Create a new user account.
    6. Generate and store OTP.
    7. Send OTP email.
    """

    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    try:

        # ----------------------------------------------------------------------
        # Check Whether Email Already Exists
        # ----------------------------------------------------------------------

        cur.execute("""
            SELECT
                user_id,
                email_verified
            FROM Mst_tbldelphiusers
            WHERE email = %s
        """, (req.email,))

        existing = cur.fetchone()

        # ----------------------------------------------------------------------
        # Existing User Found
        # ----------------------------------------------------------------------

        if existing:

            # User already verified
            if existing["email_verified"] == 1:
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered. Please login."
                )

            # ------------------------------------------------------------------
            # User Exists But Email Is Not Verified
            # ------------------------------------------------------------------

            user_id = existing["user_id"]

            # Generate New OTP
            otp_code = "".join(random.choices(string.digits, k=6))
            otp_expiry = datetime.now() + timedelta(minutes=10)

            # Invalidate Previous OTPs
            cur.execute("""
                UPDATE tbl_user_email_otp
                SET is_used = 1
                WHERE user_id = %s
                  AND is_used = 0
            """, (user_id,))

            # Store New OTP
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
                user_id,
                req.email,
                otp_code,
                otp_expiry
            ))

            conn.commit()

            # Send OTP Email
            try:
                send_otp_email(req.email, otp_code)

            except Exception as e:
                print(f"Email send error: {e}")

            return {
                "message": "Account exists but email not verified. New OTP sent.",
                "user_id": user_id,
                "email": req.email
            }

        # ----------------------------------------------------------------------
        # Hash User Password
        # ----------------------------------------------------------------------

        hashed_password = bcrypt.hashpw(
            req.password.encode(),
            bcrypt.gensalt()
        ).decode()

        # ----------------------------------------------------------------------
        # Create New User Account
        # ----------------------------------------------------------------------

        cur.execute("""
            INSERT INTO Mst_tbldelphiusers
            (
                role_id,
                user_first_name,
                user_last_name,
                company_name,
                email,
                password,
                email_verified,
                is_active
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                0,
                1
            )
        """, (
            2,
            req.first_name,
            req.last_name,
            req.company_name,
            req.email,
            hashed_password
        ))

        user_id = cur.lastrowid

        # ----------------------------------------------------------------------
        # Generate Email Verification OTP
        # ----------------------------------------------------------------------

        otp_code = "".join(random.choices(string.digits, k=6))
        otp_expiry = datetime.now() + timedelta(minutes=10)

        # ----------------------------------------------------------------------
        # Save OTP in Database
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
            user_id,
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

            return {
                "message": "Registration successful but email delivery failed. Please use Resend OTP.",
                "user_id": user_id,
                "email": req.email
            }

        # ----------------------------------------------------------------------
        # Registration Successful
        # ----------------------------------------------------------------------

        return {
            "message": "Registration successful. OTP sent to your email.",
            "user_id": user_id,
            "email": req.email
        }

    finally:

        # ----------------------------------------------------------------------
        # Close Database Resources
        # ----------------------------------------------------------------------

        cur.close()
        conn.close()