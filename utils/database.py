import sqlite3
import os
import json
import time
from pathlib import Path
from .logger import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger("bot.db")

class SettingsDatabaseManager:
    """
    This class manages server settings in the database.
    """
    
    def __init__(self, db_path="data/settings.db"):
        """
        Initialize the database manager

        Args:
            db_path (str): The path to the database file
        """

        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Database manager initialized with database at {db_path}")
    
    def _init_db(self):
        """Initialize the database, create necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create server settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            server_id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            role_id INTEGER,
            post_time TEXT DEFAULT '00:00',
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.debug("Database tables initialized")
    
    def get_server_settings(self, server_id):
        """Get the settings for a specific server
        
        Args:
            server_id (int): Discord server ID
            
            Returns:
                dict: server settings, return None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT channel_id, role_id, post_time, timezone FROM server_settings WHERE server_id = ?",
            (server_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            logger.debug(f"Server {server_id} settings: {result}")
            return {"server_id": server_id,
                    "channel_id": result[0],
                    "role_id": result[1],
                    "post_time": result[2],
                    "timezone": result[3]}
        return None
    
    def set_server_settings(self, server_id, channel_id, role_id=None, post_time="00:00", timezone="UTC"):
        """Set or update server settings
        
        Args:
            server_id (int): Discord server ID
            channel_id (int): The channel ID to send the daily challenge
            role_id (int, optional): The role ID to mention
            post_time (str, optional): The time to send the daily challenge, format "HH:MM"
            timezone (str, optional): The timezone name
            
        Returns:
            bool: return True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO server_settings (server_id, channel_id, role_id, post_time, timezone)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(server_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    role_id = excluded.role_id,
                    post_time = excluded.post_time,
                    timezone = excluded.timezone,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (server_id, channel_id, role_id, post_time, timezone)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting server settings: {e}")
            return False
        finally:
            logger.debug(f"Server {server_id} settings updated: ({channel_id}, {role_id}, {post_time}, {timezone})")
            conn.close()
    
    def set_channel(self, server_id, channel_id):
        """Update the server notification channel
        
        Args:
            server_id (int): Discord server ID
            channel_id (int): The channel ID
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                channel_id,
                settings.get("role_id"),
                settings.get("post_time", "00:00"),
                settings.get("timezone", "UTC")
            )
        else:
            return self.set_server_settings(server_id, channel_id)
    
    def set_role(self, server_id, role_id):
        """Update the server notification role
        
        Args:
            server_id (int): Discord server ID
            role_id (int): The role ID
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                settings.get("channel_id"),
                role_id,
                settings.get("post_time", "00:00"),
                settings.get("timezone", "UTC")
            )
        return False  # return False if server settings not found
    
    def set_post_time(self, server_id, post_time):
        """Update the server notification time
        
        Args:
            server_id (int): Discord server ID
            post_time (str): The time to send the daily challenge, format "HH:MM"
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                settings.get("channel_id"),
                settings.get("role_id"),
                post_time,
                settings.get("timezone", "UTC")
            )
        return False  # return False if server settings not found
    
    def set_timezone(self, server_id, timezone):
        """Update the server notification timezone
        
        Args:
            server_id (int): Discord server ID
            timezone (str): The timezone name
            
        Returns:
            bool: return True if updated successfully
        """
        settings = self.get_server_settings(server_id)
        if settings:
            return self.set_server_settings(
                server_id,
                settings.get("channel_id"),
                settings.get("role_id"),
                settings.get("post_time", "00:00"),
                timezone
            )
        return False  # return False if server settings not found
    
    def get_all_servers(self):
        """Get all servers with settings
        
        Returns:
            list: A list of dictionaries containing all server settings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT server_id, channel_id, role_id, post_time, timezone FROM server_settings"
        )
        results = cursor.fetchall()
        conn.close()
        
        servers = []
        for row in results:
            servers.append({
                "server_id": row[0],
                "channel_id": row[1],
                "role_id": row[2],
                "post_time": row[3],
                "timezone": row[4]
            })
        
        return servers
    
    def delete_server_settings(self, server_id):
        """Delete server settings
        
        Args:
            server_id (int): Discord server ID
            
        Returns:
            bool: return True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM server_settings WHERE server_id = ?", (server_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting server settings: {e}")
            return False
        finally:
            conn.close()

class ProblemsDatabaseManager:
    """
    Manage LeetCode problem data database operations
    """
    def __init__(self, db_path="data/data.db"):
        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Problems DB manager initialized with database at {db_path}")

    def _init_db(self):
        """Create problems table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL,
            title TEXT,
            title_cn TEXT,
            difficulty TEXT,
            ac_rate REAL,
            rating REAL,
            contest TEXT,
            problem_index TEXT,
            tags TEXT,
            link TEXT,
            category TEXT,
            paid_only INTEGER,
            content TEXT,
            content_cn TEXT,
            similar_questions TEXT
        )
        ''')
        conn.commit()
        conn.close()
        logger.debug("Problems table initialized")

    def update_problems(self, problems):
        """
        Insert problem data in batch. If the problem already exists, it will be ignored.
        Use single SQL execution for batch insertion to improve performance.
        
        Args:
            problems (list[dict]): problem data list
            
        Returns:
            int: actual inserted data count
        """
        total_count = len(problems)
        if total_count == 0:
            return 0
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Prepare data to insert
        values = []
        for problem in problems:
            values.append((
                problem.get("id"),
                problem.get("slug"),
                problem.get("title"),
                problem.get("title_cn"),
                problem.get("difficulty"),
                problem.get("ac_rate"),
                problem.get("rating"),
                problem.get("contest"),
                problem.get("problem_index"),
                problem.get("tags"),
                problem.get("link"),
                problem.get("category"),
                problem.get("paid_only"),
                problem.get("content"),
                problem.get("content_cn"),
                problem.get("similar_questions", None)
            ))
        
        try:
            cursor.executemany('''
            INSERT OR IGNORE INTO problems (
                id, slug, title, title_cn, difficulty, ac_rate,
                rating, contest, problem_index, tags, link,
                category, paid_only, content, content_cn, similar_questions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', values)
            
            conn.commit()
            
            # get actual inserted data count
            inserted_count = cursor.rowcount
            
            logger.info(f"Batch inserted {inserted_count}/{total_count} problems (ignored {total_count - inserted_count} existing problems)")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error inserting problems: {e}")
            return 0
        finally:
            conn.close()

    def update_problem(self, problem, force_update=False):
        """
        Insert or update single problem data.
        
        Args:
            problem (dict): problem data, must contain id or slug field for identification
            force_update (bool, optional): force update all fields. If False, empty values will not overwrite existing data. Default is False.
            
        Returns:
            bool: True if update succeeded, False otherwise
            
        Raises:
            ValueError: when problem parameter doesn't contain id field
        """
        # Check if id exists to identify the problem
        problem_id = problem.get("id")
        
        if not problem_id:
            raise ValueError("Problem must have 'id' field for identification")
        
        # If not force update, get existing data and merge
        if not force_update:
            existing_problem = self.get_problem(problem_id)
            if existing_problem:
                # Merge update: if new data field is empty, keep old data
                for key in existing_problem:
                    if key != "id" and (key not in problem or problem[key] is None or problem[key] == ""):
                        problem[key] = existing_problem[key]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO problems (
                id, slug, title, title_cn, difficulty, ac_rate,
                rating, contest, problem_index, tags, link,
                category, paid_only, content, content_cn, similar_questions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                problem_id,
                problem.get("slug"),
                problem.get("title"),
                problem.get("title_cn"),
                problem.get("difficulty"),
                problem.get("ac_rate"),
                problem.get("rating"),
                problem.get("contest"),
                problem.get("problem_index"),
                json.dumps(problem.get("tags", [])),
                problem.get("link"),
                problem.get("category"),
                problem.get("paid_only"),
                problem.get("content"),
                problem.get("content_cn"),
                json.dumps(problem.get("similar_questions", []))
            ))
            
            conn.commit()
            logger.debug(f"Updated problem with id={problem_id}, force_update={force_update}")
            return True
                
        except Exception as e:
            logger.error(f"Error updating problem: {e}")
            return False
        finally:
            conn.close()

    def get_problem(self, id=None, slug=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if id:
            cursor.execute("SELECT * FROM problems WHERE id = ?", (id,))
        elif slug:
            cursor.execute("SELECT * FROM problems WHERE slug = ?", (slug,))
        row = cursor.fetchone()
        conn.close()
        if row:
            problem = self._row_to_dict(row)
            problem["tags"] = json.loads(problem["tags"]) if problem["tags"] else []
            problem["similar_questions"] = json.loads(problem["similar_questions"]) if problem["similar_questions"] else []
            return problem
        return None

    def _row_to_dict(self, row):
        keys = [
            "id", "slug", "title", "title_cn", "difficulty", "ac_rate", "rating",
            "contest", "problem_index", "tags", "link", "category", "paid_only",
            "content", "content_cn", "similar_questions"
        ]
        return dict(zip(keys, row))

class LLMTranslateDatabaseManager:
    """
    管理 LLM 翻譯結果的資料庫操作
    """
    def __init__(self, db_path="data/data.db", expire_seconds=604800):
        self.db_path = db_path
        self.expire_seconds = expire_seconds
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"LLMTranslate DB manager initialized with database at {db_path}, expire_seconds={expire_seconds}")

    def _init_db(self):
        """建立 llm_translate_results 資料表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_translate_results (
            problem_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            translation TEXT,
            created_at INTEGER NOT NULL,
            model_name TEXT,
            PRIMARY KEY (problem_id, domain)
        )
        ''')
        conn.commit()
        conn.close()
        logger.debug("llm_translate_results table initialized")

    def get_translation(self, problem_id, domain, expire_seconds=None):
        """
        查詢翻譯結果，若超過 expire_seconds 則回傳 None
        """
        if expire_seconds is None:
            expire_seconds = self.expire_seconds
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT translation, created_at, model_name FROM llm_translate_results WHERE problem_id = ? AND domain = ?",
            (problem_id, domain)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            translation, created_at, model_name = row
            now = int(time.time())
            if now - created_at <= expire_seconds:
                return {
                    "translation": translation,
                    "model_name": model_name
                }
        return None

    def save_translation(self, problem_id, domain, translation, model_name=None):
        """
        寫入或覆蓋翻譯結果，使用 UNIX timestamp 儲存時間
        
        Args:
            problem_id (int): 題目ID
            domain (str): 網域 (com/cn)
            translation (str): 翻譯內容
            model_name (str, optional): 使用的模型名稱
        """
        now = int(time.time())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO llm_translate_results (problem_id, domain, translation, created_at, model_name)
        VALUES (?, ?, ?, ?, ?)
        ''', (problem_id, domain, translation, now, model_name))
        conn.commit()
        conn.close()
        logger.info(f"Saved LLM translation for problem_id={problem_id}, domain={domain}, model={model_name}")

class LLMInspireDatabaseManager:
    """
    管理 LLM 靈感啟發結果的資料庫操作
    """
    def __init__(self, db_path="data/data.db", expire_seconds=604800):
        self.db_path = db_path
        self.expire_seconds = expire_seconds
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"LLMInspire DB manager initialized with database at {db_path}, expire_seconds={expire_seconds}")

    def _init_db(self):
        """建立 llm_inspire_results 資料表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_inspire_results (
            problem_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            thinking TEXT,
            traps TEXT,
            algorithms TEXT,
            inspiration TEXT,
            created_at INTEGER NOT NULL,
            model_name TEXT,
            PRIMARY KEY (problem_id, domain)
        )
        ''')
        conn.commit()
        conn.close()
        logger.debug("llm_inspire_results table initialized")

    def get_inspire(self, problem_id, domain, expire_seconds=None):
        """
        查詢靈感啟發結果，若超過 expire_seconds（預設使用初始化時設定的值）則回傳 None
        """
        if expire_seconds is None:
            expire_seconds = self.expire_seconds
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT thinking, traps, algorithms, inspiration, created_at, model_name FROM llm_inspire_results WHERE problem_id = ? AND domain = ?",
            (problem_id, domain)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            thinking, traps, algorithms, inspiration, created_at, model_name = row
            now = int(time.time())
            if now - created_at <= expire_seconds:
                return {
                    "thinking": thinking,
                    "traps": traps,
                    "algorithms": algorithms,
                    "inspiration": inspiration,
                    "model_name": model_name
                }
        return None

    def save_inspire(self, problem_id, domain, thinking, traps, algorithms, inspiration, model_name=None):
        """
        寫入或覆蓋靈感啟發結果，使用 UNIX timestamp 儲存時間
        
        Args:
            problem_id (int): 題目ID
            domain (str): 網域 (com/cn)
            thinking (str): 思路內容
            traps (str): 陷阱內容
            algorithms (str): 演算法內容
            inspiration (str): 靈感內容
            model_name (str, optional): 使用的模型名稱
        """
        now = int(time.time())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # 確保所有欄位都是 str
        def safe_str(val):
            if val is None:
                return ""
            if isinstance(val, (dict, list)):
                import json
                return json.dumps(val, ensure_ascii=False)
            return str(val)
        cursor.execute('''
        INSERT OR REPLACE INTO llm_inspire_results (problem_id, domain, thinking, traps, algorithms, inspiration, created_at, model_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            problem_id,
            domain,
            safe_str(thinking),
            safe_str(traps),
            safe_str(algorithms),
            safe_str(inspiration),
            now,
            model_name
        ))
        conn.commit()
        conn.close()
        logger.info(f"Saved LLM inspire for problem_id={problem_id}, domain={domain}, model={model_name}")

    def _row_to_dict(self, row):
        keys = ["id", "slug", "title", "title_cn", "difficulty", "ac_rate", "rating", "contest", "problem_index", "tags", "link", "category", "paid_only", "content", "content_cn", "similar_questions"]
        return dict(zip(keys, row))

class DailyChallengeDatabaseManager:
    """
    Manage LeetCode daily challenge data database operations
    """
    def __init__(self, db_path="data/data.db"):
        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"DailyChallenge DB manager initialized with database at {db_path}")

    def _init_db(self):
        """Create daily_challenge table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_challenge (
            date TEXT NOT NULL,
            domain TEXT NOT NULL,
            id INTEGER,
            slug TEXT NOT NULL,
            title TEXT,
            title_cn TEXT,
            difficulty TEXT,
            ac_rate REAL,
            rating REAL,
            contest TEXT,
            problem_index TEXT,
            tags TEXT,
            link TEXT,
            category TEXT,
            paid_only INTEGER,
            content TEXT,
            content_cn TEXT,
            similar_questions TEXT,
            PRIMARY KEY (date, domain)
        )
        ''')
        conn.commit()
        conn.close()
        logger.debug("DailyChallenge table initialized")

    def update_daily(self, daily):
        """
        Insert or update daily challenge data
        Args:
            daily (dict): daily challenge data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO daily_challenge (date, domain, id, slug, title, title_cn, difficulty, ac_rate, rating, contest, problem_index, tags, link, category, paid_only, content, content_cn, similar_questions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, domain) DO UPDATE SET
                id=excluded.id,
                slug=excluded.slug,
                title=excluded.title,
                title_cn=excluded.title_cn,
                difficulty=excluded.difficulty,
                ac_rate=excluded.ac_rate,
                rating=excluded.rating,
                contest=excluded.contest,
                problem_index=excluded.problem_index,
                tags=excluded.tags,
                link=excluded.link,
                category=excluded.category,
                paid_only=excluded.paid_only,
                content=excluded.content,
                content_cn=excluded.content_cn,
                similar_questions=excluded.similar_questions
            ''', (
                daily.get("date"),
                daily.get("domain"),
                daily.get("id"),
                daily.get("slug"),
                daily.get("title"),
                daily.get("title_cn"),
                daily.get("difficulty"),
                daily.get("ac_rate"),
                daily.get("rating"),
                daily.get("contest"),
                daily.get("problem_index"),
                json.dumps(daily.get("tags", [])),
                daily.get("link"),
                daily.get("category"),
                daily.get("paid_only"),
                daily.get("content"),
                daily.get("content_cn"),
                json.dumps(daily.get("similar_questions", []))
            ))
            conn.commit()
            logger.info(f"Inserted/updated daily challenge for {daily.get('date')} {daily.get('domain')}")
            return True
        except Exception as e:
            logger.error(f"Error inserting/updating daily challenge: {e}")
            return False
        finally:
            conn.close()

    def get_daily_by_date(self, date, domain):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_challenge WHERE date = ? AND domain = ?", (date, domain))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["date", "domain", "id", "slug", "title", "title_cn", "difficulty", "ac_rate", "rating", "contest", "problem_index", "tags", "link", "category", "paid_only", "content", "content_cn", "similar_questions"]
            result = dict(zip(keys, row))
            result["tags"] = json.loads(result["tags"]) if result["tags"] else []
            result["similar_questions"] = json.loads(result["similar_questions"]) if result["similar_questions"] else []
            return result
        return None
 
if __name__ == "__main__":
    # Example usage
    db_manager = SettingsDatabaseManager()
    db_manager.set_server_settings(123456789, 987654321, role_id=111222333, post_time="12:00", timezone="UTC")
    settings = db_manager.get_server_settings(123456789)
    logger.debug(settings)
    db_manager.delete_server_settings(123456789)  # Delete settings for server ID 123456789 