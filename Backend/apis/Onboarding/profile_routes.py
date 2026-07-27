# ==============================================================================
# File: profile_routes.py
#
# Description:
# Provides API endpoints for retrieving the logged-in user's
# company profile information from the database.
# ==============================================================================

from fastapi import APIRouter, HTTPException

from db import get_conn


# ==============================================================================
# Router Configuration
# ==============================================================================

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)


# ==============================================================================
# Get Company Profile
# ==============================================================================

@router.get("/{user_id}")
def get_company_profile(user_id: int):
    """
    Fetches the latest company profile for the specified user.
    """

    try:

        # ----------------------------------------------------------------------
        # Create Database Connection
        # ----------------------------------------------------------------------

        conn = get_conn()
        cursor = conn.cursor(dictionary=True)

        # ----------------------------------------------------------------------
        # Fetch Latest Company Profile
        # ----------------------------------------------------------------------

        query = """
        SELECT
            company_name,
            specialties,
            brands,
            services,
            industry,
            headquarters,
            website
        FROM delphi_company_profiles
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """

        cursor.execute(query, (user_id,))
        row = cursor.fetchone()

        # ----------------------------------------------------------------------
        # Return Error If Profile Does Not Exist
        # ----------------------------------------------------------------------

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Profile not found"
            )

        # ----------------------------------------------------------------------
        # Return Company Profile
        # ----------------------------------------------------------------------

        return {
            "success": True,
            "profile": row
        }

    except Exception as e:

        # ----------------------------------------------------------------------
        # Handle Unexpected Errors
        # ----------------------------------------------------------------------

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        # ----------------------------------------------------------------------
        # Close Database Resources
        # ----------------------------------------------------------------------

        try:
            cursor.close()
            conn.close()
        except:
            pass