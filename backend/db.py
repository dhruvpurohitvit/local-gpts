import os
import sqlite3
import uuid
from datetime import datetime


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

DEFAULT_DB_PATH = os.path.join(
    PROJECT_ROOT,
    "storage",
    "app_state.db"
)


class DatabaseManager:

    def __init__(self, db_path=DEFAULT_DB_PATH):

        self.db_path = db_path

        directory = os.path.dirname(
            self.db_path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        self.initialize_database()


    def get_connection(self):

        connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        connection.row_factory = sqlite3.Row

        return connection


    # ==========================================================
    # DATABASE MIGRATION HELPERS
    # ==========================================================

    def column_exists(
        self,
        cursor,
        table_name,
        column_name
    ):

        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )

        columns = cursor.fetchall()

        return any(
            column["name"] == column_name
            for column in columns
        )


    def add_column_if_missing(
        self,
        cursor,
        table_name,
        column_name,
        column_definition
    ):

        if not self.column_exists(
            cursor,
            table_name,
            column_name
        ):

            print(
                f"Migrating database: adding "
                f"{column_name} to {table_name}"
            )

            cursor.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name}
                {column_definition}
                """
            )


    # ==========================================================
    # DATABASE INITIALIZATION
    # ==========================================================

    def initialize_database(self):

        connection = self.get_connection()

        cursor = connection.cursor()

        # ------------------------------------------------------
        # SESSIONS
        # ------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP
            )
        """)


        # ------------------------------------------------------
        # MESSAGES
        # ------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                model_used TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id)
            )
        """)


        # ------------------------------------------------------
        # ARTIFACTS
        # ------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                file_name TEXT,
                file_path TEXT,
                file_type TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id)
            )
        """)


        # ------------------------------------------------------
        # NETWORK LOGS
        # ------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                workbench_airgapped INTEGER,
                workbench_status TEXT,
                workbench_external_socket_count INTEGER,
                system_airgapped INTEGER,
                system_status TEXT,
                system_external_socket_count INTEGER
            )
        """)


        # ======================================================
        # MIGRATE OLD DATABASES
        # ======================================================

        # Sessions

        self.add_column_if_missing(
            cursor,
            "sessions",
            "created_at",
            "TIMESTAMP"
        )


        # Messages

        self.add_column_if_missing(
            cursor,
            "messages",
            "role",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "messages",
            "content",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "messages",
            "model_used",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "messages",
            "timestamp",
            "TIMESTAMP"
        )


        # Artifacts

        self.add_column_if_missing(
            cursor,
            "artifacts",
            "session_id",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "artifacts",
            "file_name",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "artifacts",
            "file_path",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "artifacts",
            "file_type",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "artifacts",
            "created_at",
            "TIMESTAMP"
        )


        # Network Logs

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "timestamp",
            "TIMESTAMP"
        )

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "workbench_airgapped",
            "INTEGER"
        )

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "workbench_status",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "workbench_external_socket_count",
            "INTEGER"
        )

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "system_airgapped",
            "INTEGER"
        )

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "system_status",
            "TEXT"
        )

        self.add_column_if_missing(
            cursor,
            "network_logs",
            "system_external_socket_count",
            "INTEGER"
        )


        connection.commit()

        connection.close()


    # ==========================================================
    # SESSION MANAGEMENT
    # ==========================================================

    def create_session(self):

        session_id = str(
            uuid.uuid4()
        )

        self.create_session_with_id(
            session_id
        )

        return session_id


    def create_session_with_id(
        self,
        session_id
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT session_id
            FROM sessions
            WHERE session_id = ?
        """, (
            session_id,
        ))

        existing_session = cursor.fetchone()

        if not existing_session:

            cursor.execute("""
                INSERT INTO sessions (
                    session_id,
                    created_at
                )
                VALUES (?, ?)
            """, (
                session_id,
                datetime.now().isoformat()
            ))

            connection.commit()

        connection.close()

        return session_id


    def session_exists(
        self,
        session_id
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT session_id
            FROM sessions
            WHERE session_id = ?
        """, (
            session_id,
        ))

        session = cursor.fetchone()

        connection.close()

        return session is not None


    def get_all_sessions(
        self,
        limit=100
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                s.session_id,
                s.created_at,
                (
                    SELECT content
                    FROM messages
                    WHERE messages.session_id = s.session_id
                    AND role = 'user'
                    ORDER BY id ASC
                    LIMIT 1
                ) AS first_message,
                (
                    SELECT MAX(timestamp)
                    FROM messages
                    WHERE messages.session_id = s.session_id
                ) AS last_activity
            FROM sessions s
            ORDER BY
                COALESCE(
                    last_activity,
                    s.created_at
                ) DESC
            LIMIT ?
        """, (
            limit,
        ))

        rows = cursor.fetchall()

        connection.close()

        sessions = []

        for row in rows:

            sessions.append({
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "first_message": row["first_message"],
                "last_activity": row["last_activity"]
            })

        return sessions


    # ==========================================================
    # MESSAGE MANAGEMENT
    # ==========================================================

    def save_message(
        self,
        session_id,
        role,
        content,
        model_used=None
    ):

        if not self.session_exists(
            session_id
        ):

            self.create_session_with_id(
                session_id
            )

        timestamp = datetime.now().isoformat()

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO messages (
                session_id,
                role,
                content,
                model_used,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            role,
            content,
            model_used,
            timestamp
        ))

        connection.commit()

        connection.close()


    def get_session_history(
        self,
        session_id,
        limit=100
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                role,
                content,
                model_used,
                timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (
            session_id,
            limit
        ))

        rows = cursor.fetchall()

        connection.close()

        history = []

        for row in rows:

            history.append({
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "model_used": row["model_used"],
                "timestamp": row["timestamp"]
            })

        return history


    # ==========================================================
    # ARTIFACT MANAGEMENT
    # ==========================================================

    def register_artifact(
        self,
        session_id,
        file_name,
        file_path,
        file_type
    ):

        if not self.session_exists(
            session_id
        ):

            self.create_session_with_id(
                session_id
            )

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO artifacts (
                session_id,
                file_name,
                file_path,
                file_type,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            file_name,
            file_path,
            file_type,
            datetime.now().isoformat()
        ))

        artifact_id = cursor.lastrowid

        connection.commit()

        connection.close()

        return artifact_id


    def get_session_artifacts(
        self,
        session_id
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                session_id,
                file_name,
                file_path,
                file_type,
                created_at
            FROM artifacts
            WHERE session_id = ?
            ORDER BY id ASC
        """, (
            session_id,
        ))

        rows = cursor.fetchall()

        connection.close()

        artifacts = []

        for row in rows:

            artifacts.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "file_name": row["file_name"],
                "file_path": row["file_path"],
                "file_type": row["file_type"],
                "created_at": row["created_at"]
            })

        return artifacts


    def get_artifact_by_id(
        self,
        artifact_id
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                session_id,
                file_name,
                file_path,
                file_type,
                created_at
            FROM artifacts
            WHERE id = ?
        """, (
            artifact_id,
        ))

        row = cursor.fetchone()

        connection.close()

        if not row:

            return None

        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "file_name": row["file_name"],
            "file_path": row["file_path"],
            "file_type": row["file_type"],
            "created_at": row["created_at"]
        }


    # ==========================================================
    # NETWORK SENTRY LOGGING
    # ==========================================================

    def save_network_log(
        self,
        workbench_airgapped,
        workbench_status,
        workbench_external_count,
        system_airgapped,
        system_status,
        system_external_count,
        details=None
    ):

        connection = self.get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO network_logs (
                timestamp,
                workbench_airgapped,
                workbench_status,
                workbench_external_socket_count,
                system_airgapped,
                system_status,
                system_external_socket_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            int(workbench_airgapped),
            workbench_status,
            workbench_external_count,
            int(system_airgapped),
            system_status,
            system_external_count
        ))
        log_id = cursor.lastrowid
        connection.commit()
        connection.close()
        return log_id

    # ==========================================================
    # PROJECTS & TASKS
    # ==========================================================
    def create_project(self, name, description=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, description TEXT, created_at TIMESTAMP)")
        cursor.execute("INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)", (name, description, datetime.now().isoformat()))
        p_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return p_id

    def get_projects(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM projects ORDER BY id DESC")
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            rows = []
        conn.close()
        return [dict(r) for r in rows]

# ==========================================================
# GLOBAL DATABASE INSTANCE
# ==========================================================

db = DatabaseManager()