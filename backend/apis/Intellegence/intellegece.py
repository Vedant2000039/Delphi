from fastapi import APIRouter
from pydantic import BaseModel
# import snowflake.connector
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

load_dotenv()

router = APIRouter(
    prefix="/intellegence",
    tags=["Intellegence"]
)


class ChatRequest(BaseModel):
    message: str


# Load Snowflake Private Key
def load_private_key():
    with open(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as key:
        p_key = serialization.load_pem_private_key(
            key.read(),
            password=None
        )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return pkb


# SQL Safety Function
def is_safe_sql(sql: str) -> bool:
    sql_upper = sql.strip().upper()

    # Allow only SELECT queries
    if not sql_upper.startswith("SELECT"):
        return False

    # Block dangerous keywords
    blocked_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "MERGE",
        "CREATE"
    ]

    for keyword in blocked_keywords:
        if keyword in sql_upper:
            return False

    return True


@router.post("/chat")
def chat_with_cortex(request: ChatRequest):

    user_message = request.message

    try:

        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            role=os.getenv("SNOWFLAKE_ROLE"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            private_key=load_private_key()
        )

        cursor = conn.cursor()

        # STEP 1 — Read YAML from stage
        read_yaml_query = """
        SELECT $1
        FROM @DELPHI_STAGE/DELPHI.yaml
        (FILE_FORMAT => 'FF_YAML')
        """

        cursor.execute(read_yaml_query)

        yaml_rows = cursor.fetchall()

        yaml_content = "\n".join(
            [row[0] for row in yaml_rows]
        )

        # STEP 2 — Generate SQL from Cortex
        cortex_sql_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'snowflake-arctic',
            $$
            You are a SQL generator.

            Use ONLY the provided YAML metadata.

            Rules:
            - Generate only SELECT SQL
            - No explanations
            - No comments
            - No formatting text
            - Return ONLY SQL

            YAML CONTENT:
            {yaml_content}

            USER QUESTION:
            {user_message}
            $$
        );
        """

        cursor.execute(cortex_sql_query)

        generated_sql = cursor.fetchone()[0].strip()

        # STEP 3 — SQL Safety Check
        if not is_safe_sql(generated_sql):
            return {
                "error": "Unsafe SQL generated",
                "sql": generated_sql
            }

        # STEP 4 — Execute Generated SQL
        cursor.execute(generated_sql)

        rows = cursor.fetchall()

        # Get column names
        columns = [col[0] for col in cursor.description]

        # Convert to table-style JSON
        result_data = []

        for row in rows:
            row_dict = dict(zip(columns, row))
            result_data.append(row_dict)

        return {
            "data": result_data,
            "row_count": len(result_data)
        }

    except Exception as e:

        return {
            "error": str(e)
        }

    finally:

        try:
            cursor.close()
            conn.close()
        except:
            pass