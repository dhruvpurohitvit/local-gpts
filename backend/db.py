import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone


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
                created_at TIMESTAMP,
                user_id TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                password_hash TEXT,
                theme TEXT DEFAULT 'dark',
                default_model TEXT DEFAULT 'auto',
                default_temperature REAL DEFAULT 0.0,
                default_num_ctx INTEGER DEFAULT 16384,
                default_system_prompt TEXT DEFAULT '',
                default_landing_page TEXT DEFAULT 'chat',
                session_retention_days INTEGER DEFAULT 30,
                created_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL
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
        self.add_column_if_missing(
            cursor,
            "sessions",
            "user_id",
            "TEXT"
        )
        for column_name, definition in (
            ("password_hash", "TEXT"),
            ("theme", "TEXT DEFAULT 'dark'"),
            ("default_model", "TEXT DEFAULT 'auto'"),
            ("default_temperature", "REAL DEFAULT 0.0"),
            ("default_num_ctx", "INTEGER DEFAULT 16384"),
            ("default_system_prompt", "TEXT DEFAULT ''"),
            ("default_landing_page", "TEXT DEFAULT 'chat'"),
            ("session_retention_days", "INTEGER DEFAULT 30"),
        ):
            self.add_column_if_missing(cursor, "users", column_name, definition)


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

    def create_session(self, user_id=None):

        session_id = str(
            uuid.uuid4()
        )

        self.create_session_with_id(
            session_id,
            user_id
        )

        return session_id


    def create_session_with_id(
        self,
        session_id,
        user_id=None
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
                    created_at,
                    user_id
                )
                VALUES (?, ?, ?)
            """, (
                session_id,
                datetime.now().isoformat(),
                user_id
            ))

            connection.commit()

        connection.close()

        return session_id

    def session_belongs_to_user(self, session_id, user_id):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        connection.close()
        return row is not None and row["user_id"] == user_id

    def ensure_user(self, username, name, email, password_hash=None):
        connection = self.get_connection()
        connection.execute(
            """INSERT OR IGNORE INTO users
            (username, name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (username, name, email, password_hash, datetime.now().isoformat()),
        )
        if password_hash:
            connection.execute(
                "UPDATE users SET name = ?, email = ?, password_hash = COALESCE(password_hash, ?) WHERE username = ?",
                (name, email, password_hash, username),
            )
        connection.commit()
        connection.close()

    def user_exists(self, username):
        connection = self.get_connection()
        row = connection.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        connection.close()
        return row is not None

    def create_user(self, username, name, email, password_hash):
        connection = self.get_connection()
        connection.execute(
            "INSERT INTO users (username, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, name, email, password_hash, datetime.now().isoformat()),
        )
        connection.commit()
        connection.close()

    def get_user(self, username):
        connection = self.get_connection()
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        connection.close()
        return dict(row) if row else None

    def update_user_settings(self, username, values):
        allowed = {
            "name", "theme", "default_model", "default_temperature",
            "default_num_ctx", "default_system_prompt", "default_landing_page",
            "session_retention_days",
        }
        updates = [(key, value) for key, value in values.items() if key in allowed]
        if not updates:
            return self.get_user(username)
        assignments = ", ".join(f"{key} = ?" for key, _ in updates)
        connection = self.get_connection()
        connection.execute(f"UPDATE users SET {assignments} WHERE username = ?", [value for _, value in updates] + [username])
        connection.commit()
        connection.close()
        return self.get_user(username)

    def update_user_password(self, username, password_hash):
        connection = self.get_connection()
        connection.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
        connection.commit()
        connection.close()

    def cleanup_expired_sessions(self, username, retention_days):
        cutoff = datetime.now() - timedelta(days=int(retention_days))
        connection = self.get_connection()
        rows = connection.execute(
            "SELECT session_id FROM sessions WHERE user_id = ? AND created_at < ?",
            (username, cutoff.isoformat()),
        ).fetchall()
        session_ids = [row["session_id"] for row in rows]
        for session_id in session_ids:
            connection.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM artifacts WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        connection.commit()
        connection.close()
        return session_ids

    def create_auth_session(self, token_hash, username, expires_at):
        connection = self.get_connection()
        connection.execute(
            "INSERT INTO auth_sessions (token_hash, username, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token_hash, username, expires_at, datetime.now().isoformat()),
        )
        connection.commit()
        connection.close()

    def get_auth_session(self, token_hash):
        connection = self.get_connection()
        row = connection.execute(
            "SELECT username, expires_at FROM auth_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        connection.close()
        if not row:
            return None
        try:
            if datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                self.delete_auth_session(token_hash)
                return None
        except ValueError:
            self.delete_auth_session(token_hash)
            return None
        return dict(row)

    def delete_auth_session(self, token_hash):
        connection = self.get_connection()
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
        connection.commit()
        connection.close()


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
        limit=100,
        user_id=None
    ):

        connection = self.get_connection()

        cursor = connection.cursor()

        query = """
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
            {user_filter}
            ORDER BY
                COALESCE(
                    last_activity,
                    s.created_at
                ) DESC
            LIMIT ?
        """.format(user_filter="WHERE s.user_id = ?" if user_id is not None else "")
        params = [user_id, limit] if user_id is not None else [limit]
        cursor.execute(query, params)

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

    def _ensure_project_tables(self, cursor):
        """Create projects, project_sessions, and tasks tables if absent, and migrate columns."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at  TIMESTAMP,
                user_id     TEXT,
                archived    INTEGER DEFAULT 0
            )
        """)
        self.add_column_if_missing(cursor, "projects", "user_id",     "TEXT")
        self.add_column_if_missing(cursor, "projects", "archived",    "INTEGER DEFAULT 0")
        self.add_column_if_missing(cursor, "projects", "description", "TEXT DEFAULT ''")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                session_id TEXT    NOT NULL,
                attached_at TIMESTAMP,
                UNIQUE(project_id, session_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                status      TEXT DEFAULT 'todo',
                created_at  TIMESTAMP,
                updated_at  TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        self.add_column_if_missing(cursor, "tasks", "description", "TEXT DEFAULT ''")
        self.add_column_if_missing(cursor, "tasks", "updated_at",  "TIMESTAMP")

    # ----------------------------------------------------------
    # PROJECT CRUD
    # ----------------------------------------------------------

    def create_project(self, name: str, description: str = "", user_id=None) -> int:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        cur.execute(
            "INSERT INTO projects (name, description, created_at, user_id, archived) VALUES (?, ?, ?, ?, 0)",
            (name, description, datetime.now().isoformat(), user_id),
        )
        p_id = cur.lastrowid
        conn.commit()
        conn.close()
        return p_id

    def get_projects(self, user_id=None):
        conn = self.get_connection()
        cur  = conn.cursor()
        try:
            self._ensure_project_tables(cur)
            if user_id is None:
                cur.execute("SELECT * FROM projects WHERE archived = 0 ORDER BY id DESC")
            else:
                cur.execute("SELECT * FROM projects WHERE user_id = ? AND archived = 0 ORDER BY id DESC", (user_id,))
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        conn.close()
        return [dict(r) for r in rows]

    def get_project(self, project_id: int, user_id=None):
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        p = dict(row)
        if user_id and p.get("user_id") != user_id:
            return None
        return p

    def rename_project(self, project_id: int, name: str, description: str, user_id=None) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        query = "UPDATE projects SET name = ?, description = ? WHERE id = ?"
        params: list = [name, description, project_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        cur.execute(query, params)
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def archive_project(self, project_id: int, user_id=None) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        query  = "UPDATE projects SET archived = 1 WHERE id = ?"
        params: list = [project_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        cur.execute(query, params)
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_project(self, project_id: int, user_id=None) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        # Verify ownership
        cur.execute("SELECT user_id FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row or (user_id and row["user_id"] != user_id):
            conn.close()
            return False
        cur.execute("DELETE FROM tasks           WHERE project_id  = ?", (project_id,))
        cur.execute("DELETE FROM project_sessions WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM projects         WHERE id         = ?", (project_id,))
        conn.commit()
        conn.close()
        return True

    # ----------------------------------------------------------
    # SESSION ↔ PROJECT LINK
    # ----------------------------------------------------------

    def attach_session_to_project(self, project_id: int, session_id: str, user_id=None) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        # Ownership check
        cur.execute("SELECT user_id FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row or (user_id and row["user_id"] != user_id):
            conn.close()
            return False
        try:
            cur.execute(
                "INSERT OR IGNORE INTO project_sessions (project_id, session_id, attached_at) VALUES (?, ?, ?)",
                (project_id, session_id, datetime.now().isoformat()),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            return False
        conn.close()
        return True

    def detach_session_from_project(self, project_id: int, session_id: str, user_id=None) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        cur.execute("SELECT user_id FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row or (user_id and row["user_id"] != user_id):
            conn.close()
            return False
        cur.execute(
            "DELETE FROM project_sessions WHERE project_id = ? AND session_id = ?",
            (project_id, session_id),
        )
        conn.commit()
        conn.close()
        return True

    def get_project_sessions(self, project_id: int):
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        cur.execute("""
            SELECT s.session_id, s.created_at,
                   (SELECT content FROM messages
                    WHERE messages.session_id = s.session_id AND role = 'user'
                    ORDER BY id ASC LIMIT 1) AS first_message,
                   ps.attached_at
            FROM project_sessions ps
            JOIN sessions s ON s.session_id = ps.session_id
            WHERE ps.project_id = ?
            ORDER BY ps.attached_at DESC
        """, (project_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_project_detail(self, project_id: int, user_id=None):
        project = self.get_project(project_id, user_id=user_id)
        if not project:
            return None
        project["sessions"] = self.get_project_sessions(project_id)
        project["tasks"]    = self.get_tasks(project_id)
        return project

    # ----------------------------------------------------------
    # TASKS CRUD
    # ----------------------------------------------------------

    def create_task(self, project_id: int, title: str, description: str = "", status: str = "todo") -> int:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO tasks (project_id, title, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, title, description, status, now, now),
        )
        t_id = cur.lastrowid
        conn.commit()
        conn.close()
        return t_id

    def get_tasks(self, project_id: int):
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        cur.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY id ASC",
            (project_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_task(self, task_id: int, project_id: int, title: str = None,
                    description: str = None, status: str = None) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        sets, params = [], []
        if title       is not None: sets.append("title = ?");       params.append(title)
        if description is not None: sets.append("description = ?"); params.append(description)
        if status      is not None: sets.append("status = ?");      params.append(status)
        if not sets:
            conn.close()
            return False
        sets.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params += [task_id, project_id]
        cur.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ? AND project_id = ?", params)
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_task(self, task_id: int, project_id: int) -> bool:
        conn = self.get_connection()
        cur  = conn.cursor()
        self._ensure_project_tables(cur)
        cur.execute("DELETE FROM tasks WHERE id = ? AND project_id = ?", (task_id, project_id))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


# ==========================================================
# GLOBAL DATABASE INSTANCE
# ==========================================================

db = DatabaseManager()