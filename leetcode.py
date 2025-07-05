import re
import json
import requests
import asyncio
import aiohttp
import pytz

from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from utils.database import ProblemsDatabaseManager, DailyChallengeDatabaseManager
from utils.logger import setup_logging, get_logger
from utils.config import get_config

# Set up logging
setup_logging()
logger = get_logger("leetcode")

class LeetCodeClient:
    """
    LeetCode API Client for fetching problems, daily challenges and more.
    Supports both LeetCode.com and LeetCode.cn domains.
    """
    PROBLEMS_BASE_URL = "https://leetcode.com/api/problems/{}"
    CATEGORIES = ["algorithms", "database", "shell"]
    RATINGS_URL = "https://raw.githubusercontent.com/zerotrac/leetcode_problem_rating/refs/heads/main/ratings.txt"

    def __init__(self, domain="com", data_dir="./data", db_path="./data/data.db",
                 max_retries=3, retry_delay=1, cache_ttl=3600):
        """
        Initialize the LeetCode client
        
        Args:
            domain (str): Domain to use - 'com' for leetcode.com or 'cn' for leetcode.cn
            data_dir (str): Directory to store cached data
            db_path (str): Path to the SQLite database file
            max_retries (int): Maximum number of retry attempts for API calls
            retry_delay (int): Delay in seconds between retry attempts
            cache_ttl (int): Time-to-live for cached ratings in seconds
        """
        self.domain = domain.lower()
        if self.domain not in ["com", "cn"]:
            raise ValueError("Domain must be either 'com' or 'cn'")
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.base_url = f"https://leetcode.{self.domain}"
        self.graphql_url = f"{self.base_url}/graphql"
        self.time_zone = "Asia/Shanghai" if self.domain == "cn" else "UTC"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)  # Ensure data directory exists
        self.problems_db = ProblemsDatabaseManager(db_path)
        self.daily_db = DailyChallengeDatabaseManager(db_path)
        self.ratings = {}
        self.ratings_ttl = cache_ttl
        self.ratings_last_update = 0
        
        # Background task tracking
        self._background_tasks = set()
        # Semaphore for concurrent API requests
        self._fetch_semaphore = asyncio.Semaphore(5)
        
        logger.info(f"Initialized LeetCode client with domain: leetcode.{self.domain}")
    
    async def shutdown(self):
        """Cancel all background tasks gracefully"""
        if self._background_tasks:
            logger.info(f"Cancelling {len(self._background_tasks)} background tasks...")
            for task in self._background_tasks:
                task.cancel()
            # Wait for all tasks to complete cancellation
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            logger.info("All background tasks cancelled")

    async def init_all_problems(self, init_ratings=False):
        """
        Fetch all problems from LeetCode across all categories.
        """
        problems = await self.fetch_all_problems()
        self.problems_db.update_problems(problems)
        logger.debug(f"Total problems fetched: {len(problems)}")
        if init_ratings:
            ratings = await self.fetch_ratings()
        return problems

    async def fetch_all_problems(self):
        """
        Get all problems from LeetCode across all categories.
        
        Returns:
            list: List of all problems
        """
        tasks = [
            self.fetch_category_problems(category)
            for category in self.CATEGORIES
        ]
        all_results = await asyncio.gather(*tasks)
        problems = []
        for plist in all_results:
            problems.extend(plist)
        return problems

    async def fetch_category_problems(self, category):
        """
        Get all problems for a specific category.
        
        Args:
            category (str): Category name ("algorithms", "database", or "shell")
            
        Returns:
            list: Problems in the category
        """
        url = self.PROBLEMS_BASE_URL.format(category + "/")
        attempt = 0
        while attempt < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers={
                        "User-Agent": "Mozilla/5.0",
                        "X-Requested-With": "XMLHttpRequest"
                    }) as res:
                        if res.status != 200:
                            raise Exception(f"HTTP {res.status}")
                        text = await res.text()
                        try:
                            json_data = json.loads(text)
                        except json.JSONDecodeError:
                            snippet = text[:200].replace('\n', ' ').replace('\r', ' ')
                            raise Exception(f"Failed to parse JSON. Snippet: {snippet}")
                        problems = self._parse_problems(json_data, category.title())
                        logger.info(f"Downloaded {category} problems.")
                        return problems
            except Exception as e:
                attempt += 1
                logger.error(f"Failed to fetch {category} (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Giving up on {category} after {self.max_retries} attempts.")
                    return []

    def _parse_problems(self, json_data, category):
        """
        Parse problems from API resonse.
        
        Args:
            json_data (dict): JSON data from the API
            
        Returns:
            list: Parsed problems
        """
        total_problems = json_data.get("num_total", len(json_data.get("stat_status_pairs", [])))
        problems = []
        for p in json_data.get("stat_status_pairs", []):
            if p.get("stat", {}).get("question__hide", False):
                continue
            stat = p["stat"]
            total_submitted = stat.get("total_submitted", 1) or 1
            ac_rate = stat.get("total_acs", 0) * 100 / total_submitted
            slug = stat.get("question__title_slug")
            problem = {
                "id": stat.get("frontend_question_id"),
                "slug": slug,
                "title": stat.get("question__title"),
                "title_cn": "",
                "difficulty": self._level_to_name(p.get("difficulty", {}).get("level", 0)),
                "ac_rate": ac_rate,
                "link": f"https://leetcode.com/problems/{slug}/",
                "category": category.title(),
                "paid_only": int(p.get("paid_only", False)),
                "rating": 0,  # reserve
                "tags": None,  # reserve
                "content": None,  # reserve
                "content_cn": None,  # reserve
                "contest": None,  # reserve
                "problem_index": None,  # reserve
                "similar_questions": None  # reserve
            }
            problems.append(problem)
        logger.debug(f"Downloaded {len(problems)}/{total_problems} problems in {category} category.")
        return problems

    def _level_to_name(self, level):
        """Convert numeric difficulty level to string representation."""
        return {1: "Easy", 2: "Medium", 3: "Hard"}.get(level, "Unknown")

    async def fetch_ratings(self):
        """
        Fetch problem ratings from GitHub repository.
        
        Returns:
            dict: Problem ratings mapped by problem ID
        """
        attempt = 0
        while attempt < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.RATINGS_URL) as res:
                        if res.status != 200:
                            raise Exception(f"HTTP {res.status}")
                        text = await res.text()
                        ratings_data = {}
                        lines = text.strip().split('\n')
                        for line in lines[1:]:
                            parts = line.strip().split('\t')
                            if len(parts) < 7:  
                                parts += [''] * (7 - len(parts))
                            if len(parts) >= 2:
                                try:
                                    problem_id = int(parts[1])
                                    # Store additional information
                                    ratings_data[problem_id] = {
                                        'id': problem_id,
                                        'rating': float(parts[0]),
                                        'title': parts[2],
                                        'title_cn': parts[3],
                                        'slug': parts[4],
                                        'contest': parts[5],
                                        'problem_index': parts[6]
                                    }
                                except Exception:
                                    continue
                        logger.info(f"Downloaded {len(ratings_data)} ratings.")
                        return ratings_data
            except Exception as e:
                attempt += 1
                logger.error(f"Failed to fetch ratings (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Giving up on ratings after {self.max_retries} attempts.")
                    return {}

    async def fetch_problem_detail(self, slug):
        """
        Get detailed information for a specific problem.
        
        Args:
            slug (str): Problem slug/title-slug
            
        Returns:
            dict: Problem details including content, tags, etc.
        """
        url = self.graphql_url
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json"
        }
        query = """
            query getQuestionDetail($titleSlug: String!) {
                question(titleSlug: $titleSlug) {
                    questionId
                    questionFrontendId
                    title
                    titleSlug
                    translatedTitle
                    difficulty
                    acRate
                    isPaidOnly
                    stats
                    translatedContent
                    content
                    similarQuestions
                    topicTags {
                        name
                        id
                        slug
                    }
                    categoryTitle
                }
            }
            """
        payload = {
            "query": query,
            "variables": {"titleSlug": slug},
            "operationName": "getQuestionDetail"
        }

        attempt = 0
        while attempt < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload) as res:
                        if res.status != 200:
                            raise Exception(f"HTTP {res.status}")
                        text = await res.text()
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            snippet = text[:200].replace('\n', ' ').replace('\r', ' ')
                            raise Exception(f"Failed to parse JSON. Snippet: {snippet}")

                        q = data.get("data", {}).get("question")
                        if not q:
                            raise Exception(f"Question not found for slug '{slug}'")
                        return {
                            "id": q.get("questionFrontendId"),
                            "category": q.get("categoryTitle", "").title(),
                            "title": q.get("title"),
                            "title_cn": q.get("translatedTitle"),
                            "slug": slug,
                            "link": f"https://leetcode.com/problems/{slug}/",
                            "difficulty": q.get("difficulty"),
                            "ac_rate": float(q.get("acRate", "0")),
                            "content": q.get("content"),
                            "content_cn": q.get("translatedContent"),
                            "stats": q.get("stats"),
                            "similar_questions": json.loads(q.get("similarQuestions", "[]")),
                            "tags": [tag['name'] for tag in q.get('topicTags', [])],
                            "paid_only": 1 if q.get("isPaidOnly") else 0
                        }
            except Exception as e:
                attempt += 1
                logger.error(f"Failed to fetch problem '{slug}' (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Giving up on problem '{slug}' after {self.max_retries} attempts.")
                    return None

    async def get_problem(self, problem_id=None, slug=None):
        """
        Fetch problem information by ID or slug
        
        Args:
            problem_id (str): LeetCode problem ID
            slug (str): LeetCode problem slug
            
        Returns:
            dict: Problem information if found, None otherwise
        """
        problem = self.problems_db.get_problem(id=problem_id, slug=slug)

        # If problem not found, fetch all problems from LeetCode API to initialize
        if not problem:
            logger.info(f"Problem {problem_id or slug} not found, fetching all problems from LeetCode API...")
            await self.init_all_problems()
            problem = self.problems_db.get_problem(id=problem_id, slug=slug)
            # If problem still not found, return None
            if not problem:
                logger.error(f"Problem {problem_id or slug} still not found in database after fetching all problems.")
                return None

        # If problem found, update problem detail and rating if needed
        problem_id_for_log = problem.get('id')
        logger.debug(f"Problem {problem_id_for_log} found in database: {problem['rating']}")
        if problem['slug'] and (not problem.get('tags') or not problem.get('content')):
            logger.debug(f"Problem {problem_id_for_log} still not have detail information, fetching problem detail from LeetCode API...")
            problem_detail = await self.fetch_problem_detail(problem['slug'])
            if problem_detail:
                for key, value in problem_detail.items():
                    problem[key] = problem.get(key, value) or value
                self.problems_db.update_problem(problem)

        if not problem['rating']:
            logger.debug(f"Problem {problem_id_for_log} still not have rating, fetching rating from LeetCode API...")
            await self.get_problem_rating(problem_id_for_log)
            problem = self.problems_db.get_problem(problem_id_for_log)

        return problem

    async def get_problem_rating(self, problem_id):
        """
        Get the problem rating based on problem ID.
        
        Args:
            problem_id (str or int): LeetCode problem ID
            
        Returns:
            float or int: Problem rating if found, 0 otherwise
        """
        try:
            # Make sure problem_id is an integer
            problem_id = int(problem_id) if not isinstance(problem_id, int) else problem_id
            
            # 1. Try to get problem data from database
            problem = self.problems_db.get_problem(problem_id)
            if problem and problem.get('rating') and float(problem['rating']) > 0:
                logger.info(f"Found rating for problem {problem_id} in database: {problem['rating']}")
                return float(problem['rating'])
            
            def _update_problem_data(problem, info):
                for key, value in info.items():
                    problem[key] = problem.get(key, value) or value
                self.problems_db.update_problem(problem)
                logger.info(f"Updated problem {problem_id} in database: {problem['rating']}")
                return float(problem['rating'])
            
            # 2. Check if cache is expired
            current_time = int(datetime.now().timestamp())
            cache_expired = current_time - self.ratings_last_update > self.ratings_ttl
            
            # 3. If cache is valid, check if the ratings data contains this problem ID
            if not cache_expired and len(self.ratings) > 0:
                if problem_id in self.ratings:
                    info = self.ratings[problem_id]
                    logger.info(f"Found rating for problem {problem_id} in memory cache: {info['rating']}")
                    _update_problem_data(problem, info)
                    return float(info['rating'])
                else:
                    logger.info(f"Problem {problem_id} not found in existing cache")
                    return 0
            else:
                logger.info(f"Ratings cache expired (last update: {self.ratings_last_update}), updating...")
            
            # 4. Cache is expired or empty, update all ratings
            updated = await self.fetch_ratings()
            if updated:
                # Replace the entire ratings dict instead of updating
                self.ratings = updated  
                self.ratings_last_update = current_time
                logger.info(f"Ratings cache updated at {self.ratings_last_update} with {len(updated)} entries")
                
                if problem_id in self.ratings:
                    info = self.ratings[problem_id]
                    logger.info(f"Found rating for problem {problem_id} in updated cache: {info['rating']}")
                    _update_problem_data(problem, info)
                    return float(info['rating'])

        except Exception as e:
            logger.error(f"Error getting rating for problem {problem_id}: {e}")
        
        # If no rating is found, return 0
        return 0
    
    async def fetch_daily_challenge(self, domain=None):
        """
        Get the daily challenge question from LeetCode API.
        
        Args:
            domain (str, optional): Domain to use ('com' or 'cn'). If None, uses the client's domain.
            
        Returns:
            dict: Daily challenge information
        """
        # If domain is not provided, use the client's domain
        if domain is None:
            domain = self.domain
            
        base_url = f"https://leetcode.{domain}"
        api_endpoint = f"{base_url}/graphql"
        
        if domain == "cn":
            query = """
            query questionOfToday {
                todayRecord {
                    date
                    userStatus
                    question {
                        questionId
                        frontendQuestionId: questionFrontendId
                        difficulty
                        title
                        titleCn: translatedTitle
                        titleSlug
                        paidOnly: isPaidOnly
                        freqBar
                        isFavor
                        acRate
                        status
                        hasVideoSolution
                        topicTags {
                            name
                            nameTranslated: translatedName
                            id
                        }
                    }
                }
            }
            """
        else:
            query = """
            query questionOfToday {
                activeDailyCodingChallengeQuestion {
                    date
                    link
                    question {
                        acRate
                        difficulty
                        freqBar
                        frontendQuestionId: questionFrontendId
                        isFavor
                        paidOnly: isPaidOnly
                        status
                        title
                        titleSlug
                        hasVideoSolution
                        hasSolution
                        topicTags {
                            name
                            id
                            slug
                        }
                    }
                }
            }
            """
        headers = {'Content-Type': 'application/json'}
        payload = {"query": query}
        
        logger.info(f"Fetching daily challenge from LeetCode {domain.upper()} API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, headers=headers, json=payload) as res:
                if res.status != 200:
                    error_msg = f"API request failed, status code: {res.status}, response: {await res.text()}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                raw_data = await res.json()
                
                if domain == "cn":
                    question_info = raw_data['data']['todayRecord'][0]
                    question = question_info['question']
                    link = f"{base_url}/problems/{question['titleSlug']}/"
                else:
                    question_info = raw_data['data']['activeDailyCodingChallengeQuestion']
                    question = question_info['question']
                    link = f"{base_url}{question_info['link']}"
                
                qid = question['frontendQuestionId']
                slug = question['titleSlug']
                
                # Create basic daily challenge data
                daily = dict(
                    date=question_info['date'],
                    domain=domain,
                    qid=qid,
                    title=question['title'],
                    title_cn=question.get('titleCn', ''),
                    difficulty=question['difficulty'],
                    rating=None,  # This will be fetched from get_problem
                    ac_rate=question['acRate'] if domain == "com" else question['acRate'] * 100,
                    slug=slug,
                    link=link,
                    tags=[tag['name'] for tag in question['topicTags']]
                )
                
                # Get problem detail
                problem = await self.get_problem(problem_id=qid, slug=slug)
                if problem:
                    for key, value in problem.items():
                        daily[key] = daily.get(key, value) or value
                    # Update database
                    self.daily_db.update_daily(daily)
                    logger.info(f"Daily challenge for {daily['date']} (domain: {domain}) written to database")
                
                return daily

    async def get_daily_challenge(self, date_str=None, domain=None):
        """
        Get the daily challenge data for the specified date.
        Checks for existing data file first before fetching from LeetCode API.
        
        Args:
            date_str (str, optional): The date string in format 'YYYY-MM-DD'. 
                                     If None, caller should handle getting the current date.
        
        Returns:
            dict: The daily challenge information
        """
        # If domain is not provided, use the client's domain
        if domain is None:
            domain = self.domain

        tz = pytz.timezone("Asia/Shanghai") if self.domain == "cn" else pytz.timezone("UTC")
        today = datetime.now(tz).strftime("%Y-%m-%d")

        # If date_str is not provided, use today's date
        if date_str is None:
            date_str = today
        # If date_str is not in 'YYYY-MM-DD' format, raise error
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            raise ValueError("date_str must be in 'YYYY-MM-DD' format")

        today_time = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=tz)
        query_time = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
        if query_time > today_time:
            raise ValueError("date_str must be in the past")
        
        # 1. Check database
        daily = self.daily_db.get_daily_by_date(date_str, domain)
        if daily:
            logger.info(f"Found daily challenge for {date_str} in database")
            return daily
        
        # 2. Check file (for legacy data)
        yy, mm, _ = date_str.split('-')
        file_path = self.data_dir / domain / "daily" / yy / mm / f"{date_str}.json"
        
        # Check if there is already a file for today
        info = None
        if file_path.exists():
            logger.info(f"Found existing challenge data at {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
            except Exception as e:
                logger.error(f"Error reading existing file: {e}")
                info = None
            info["date"] = info.get("date", date_str) or date_str
            info["domain"] = info.get("domain", domain) or domain

            # Get problem detail
            problem = await self.get_problem(problem_id=info['qid'], slug=info.get('slug', None))
            if problem:
                for key, value in problem.items():
                    info[key] = info.get(key, value) or value
                # Update database
                self.daily_db.update_daily(info)
                logger.info(f"Daily challenge for {info['date']} (domain: {domain}) written to database")
            return info
        
        # If no valid file is found, fetch the data
        if info is None and query_time == today_time:
            logger.info("Fetching new challenge data...")
            info = await self.fetch_daily_challenge(self.domain)
            return info
        
        # If still no data found and domain is 'com', try fetching monthly data
        if info is None and domain == "com":
            logger.info(f"No data found for {date_str}, attempting to fetch monthly data...")
            year, month, _ = date_str.split('-')
            year_int = int(year)
            month_int = int(month)
            
            monthly_data = await self.fetch_monthly_daily_challenges(year_int, month_int)
            
            if monthly_data and 'challenges' in monthly_data:
                logger.info(f"Fetched {len(monthly_data['challenges'])} daily challenges for {year}-{month}")
                
                # First, find and process the requested date
                requested_challenge = None
                other_challenges = []
                
                for challenge in monthly_data['challenges']:
                    if challenge.get('date') == date_str:
                        requested_challenge = challenge
                    else:
                        other_challenges.append(challenge)
                
                # Process the requested challenge first
                if requested_challenge:
                    challenge_date = requested_challenge.get('date')
                    question_id = requested_challenge.get('question_id')
                    slug = requested_challenge.get('slug')
                    
                    if question_id and slug:
                        problem = await self.get_problem(problem_id=question_id, slug=slug)
                        if problem:
                            # Prepare daily challenge data
                            info = {
                                'date': challenge_date,
                                'domain': domain,
                                'id': problem.get('id'),
                                'slug': problem.get('slug'),
                                'title': problem.get('title'),
                                'title_cn': problem.get('title_cn'),
                                'difficulty': problem.get('difficulty'),
                                'ac_rate': problem.get('ac_rate'),
                                'rating': problem.get('rating'),
                                'contest': problem.get('contest'),
                                'problem_index': problem.get('problem_index'),
                                'tags': problem.get('tags', []),
                                'link': problem.get('link'),
                                'category': problem.get('category'),
                                'paid_only': problem.get('paid_only'),
                                'content': problem.get('content'),
                                'content_cn': problem.get('content_cn'),
                                'similar_questions': problem.get('similar_questions', [])
                            }
                            
                            # Store in database immediately
                            self.daily_db.update_daily(info)
                            logger.info(f"Processed requested challenge for {date_str}")
                
                # Create a background task to process other challenges
                if other_challenges and info:
                    task = asyncio.create_task(
                        self._process_remaining_monthly_challenges(other_challenges, domain, year, month)
                    )
                    # Track the background task
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                    logger.info(f"Started background task to process {len(other_challenges)} remaining challenges")
                
                # Return the requested date's challenge if found
                if info:
                    return info
                else:
                    logger.warning(f"Requested date {date_str} not found in monthly data for domain {domain}.")
        
        return None
    
    async def fetch_recent_ac_submissions(self, username, limit=15):
        """
        Fetch recent AC (Accepted) submissions for a given username
        
        Args:
            username (str): LeetCode username
            limit (int): Number of submissions to fetch (default: 15)
        
        Returns:
            list: List of recent AC submissions with basic info (id, title, slug, timestamp)
        """
        if self.domain != "com":
            logger.warning("User submissions are only available on leetcode.com")
            return []
            
        # GraphQL query for recent AC submissions
        query = """
        query recentAcSubmissions($username: String!, $limit: Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
            }
        }
        """
        
        # Variables for the query
        variables = {
            "username": username,
            "limit": limit
        }
        
        # Request headers
        headers = {
            'Content-Type': 'application/json',
            'Referer': f'{self.base_url}/u/{username}/'
        }
        
        # Request payload
        payload = {
            "query": query,
            "variables": variables,
            "operationName": "recentAcSubmissions"
        }
        
        try:
            logger.info(f"Fetching recent AC submissions for user: {username}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.graphql_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return []
                    
                    data = await response.json()
                    if 'errors' in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return []
                    
                    submissions = data.get('data', {}).get('recentAcSubmissionList', [])
                    logger.info(f"Successfully fetched {len(submissions)} submissions")
                    
                    # Return basic submission info without fetching problem details
                    # This improves performance by deferring detailed lookups
                    basic_submissions = []
                    for submission in submissions:
                        basic_submission = {
                            'submission_id': submission['id'],
                            'title': submission['title'],
                            'slug': submission['titleSlug'],
                            'timestamp': submission['timestamp'],
                            'submission_time': datetime.fromtimestamp(int(submission['timestamp'])).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        basic_submissions.append(basic_submission)
                    
                    return basic_submissions
            
        except Exception as e:
            logger.error(f"Error fetching submissions: {str(e)}", exc_info=True)
            return []

    async def fetch_monthly_daily_challenges(self, year, month):
        """
        Fetch all daily coding challenges for a specific month and year
        
        Note: LeetCode API only provides data from April 2020 onwards.
        
        Args:
            year (int): Year (e.g., 2025)
            month (int): Month (1-12)
            
        Returns:
            dict: Monthly challenge data with challenges and weekly challenges
        """
        if self.domain != "com":
            logger.warning("Monthly daily challenges are only available on leetcode.com")
            return {}
            
        # Check if the requested date is before April 2020
        if year < 2020 or (year == 2020 and month < 4):
            logger.warning(f"Monthly daily challenges are only available from April 2020 onwards. Requested: {year}-{month:02d}")
            return {}
            
        # GraphQL query for monthly daily challenges
        query = """
        query dailyCodingQuestionRecords($year: Int!, $month: Int!) {
            dailyCodingChallengeV2(year: $year, month: $month) {
                challenges {
                    date
                    userStatus
                    link
                    question {
                        questionFrontendId
                        title
                        titleSlug
                    }
                }
                weeklyChallenges {
                    date
                    userStatus
                    link
                    question {
                        questionFrontendId
                        title
                        titleSlug
                        isPaidOnly
                    }
                }
            }
        }
        """
        
        # Variables for the query
        variables = {
            "year": year,
            "month": month
        }
        
        # Request headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://leetcode.com/problemset/',
            'Origin': 'https://leetcode.com'
        }
        
        # Request payload
        payload = {
            "query": query,
            "variables": variables,
            "operationName": "dailyCodingQuestionRecords"
        }
        
        try:
            logger.info(f"Fetching monthly daily challenges for {year}-{month}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.graphql_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return {}
                    
                    data = await response.json()
                    if 'errors' in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return {}
                    
                    monthly_data = data.get('data', {}).get('dailyCodingChallengeV2', {})
                    challenges = monthly_data.get('challenges', [])
                    weekly_challenges = monthly_data.get('weeklyChallenges', [])
                    
                    logger.info(f"Successfully fetched {len(challenges)} daily challenges and {len(weekly_challenges)} weekly challenges")
                    
                    # Format the response data
                    formatted_data = {
                        'year': year,
                        'month': month,
                        'challenges': [],
                        'weekly_challenges': []
                    }
                    
                    # Process daily challenges
                    for challenge in challenges:
                        question = challenge.get('question', {})
                        formatted_challenge = {
                            'date': challenge.get('date'),
                            'user_status': challenge.get('userStatus'),
                            'link': challenge.get('link'),
                            'question_id': question.get('questionFrontendId'),
                            'title': question.get('title'),
                            'slug': question.get('titleSlug')
                        }
                        formatted_data['challenges'].append(formatted_challenge)
                    
                    # Process weekly challenges
                    for weekly_challenge in weekly_challenges:
                        question = weekly_challenge.get('question', {})
                        formatted_weekly = {
                            'date': weekly_challenge.get('date'),
                            'user_status': weekly_challenge.get('userStatus'),
                            'link': weekly_challenge.get('link'),
                            'question_id': question.get('questionFrontendId'),
                            'title': question.get('title'),
                            'slug': question.get('titleSlug'),
                            'paid_only': question.get('isPaidOnly', False)
                        }
                        formatted_data['weekly_challenges'].append(formatted_weekly)
                    
                    return formatted_data
            
        except Exception as e:
            logger.error(f"Error fetching monthly challenges: {str(e)}", exc_info=True)
            return {}
    
    async def _process_remaining_monthly_challenges(self, challenges, domain, year, month):
        """
        Process remaining monthly challenges in the background
        
        Args:
            challenges (list): List of challenge data to process
            domain (str): Domain (com or cn)
            year (str): Year
            month (str): Month
        """
        try:
            logger.info(f"Background task: Processing {len(challenges)} remaining challenges for {year}-{month}")
            processed_count = 0
            
            for challenge in challenges:
                try:
                    challenge_date = challenge.get('date')
                    if not challenge_date:
                        continue
                    
                    # Get detailed problem information
                    question_id = challenge.get('question_id')
                    slug = challenge.get('slug')
                    
                    if question_id and slug:
                        # Use semaphore to limit concurrent API requests
                        async with self._fetch_semaphore:
                            problem = await self.get_problem(problem_id=question_id, slug=slug)
                        if problem:
                            # Prepare daily challenge data
                            daily_data = {
                                'date': challenge_date,
                                'domain': domain,
                                'id': problem.get('id'),
                                'slug': problem.get('slug'),
                                'title': problem.get('title'),
                                'title_cn': problem.get('title_cn'),
                                'difficulty': problem.get('difficulty'),
                                'ac_rate': problem.get('ac_rate'),
                                'rating': problem.get('rating'),
                                'contest': problem.get('contest'),
                                'problem_index': problem.get('problem_index'),
                                'tags': problem.get('tags', []),
                                'link': problem.get('link'),
                                'category': problem.get('category'),
                                'paid_only': problem.get('paid_only'),
                                'content': problem.get('content'),
                                'content_cn': problem.get('content_cn'),
                                'similar_questions': problem.get('similar_questions', [])
                            }
                            
                            # Store in database
                            self.daily_db.update_daily(daily_data)
                            processed_count += 1
                            
                            # Add a configurable delay to avoid overwhelming the API
                            config = get_config()
                            delay = config.get("leetcode.monthly_fetch_delay", 0.5)
                            await asyncio.sleep(delay)
                            
                except aiohttp.ClientError as e:
                    logger.error(f"Network error processing challenge for date {challenge.get('date', 'unknown')}: {str(e)}")
                    continue
                except asyncio.CancelledError:
                    logger.info("Background task cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error processing challenge for date {challenge.get('date', 'unknown')}: {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"Background task completed: Processed {processed_count}/{len(challenges)} challenges for {year}-{month}")
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in background monthly challenge processing: {str(e)}", exc_info=True)

def html_to_text(html):
    """
    Convert HTML to formatted text.
    
    Args:
        html (str): HTML content
        
    Returns:
        str: Formatted text
    """
    soup = BeautifulSoup(html, "html.parser")
    for sup in soup.find_all("sup"):
        sup.replace_with("^" + sup.get_text())
    for strong in soup.find_all("strong"):
        strong.replace_with(f"**{strong.get_text()}**")
    for em in soup.find_all("em"):
        em.replace_with(f"*{em.get_text()}*")
    for code in soup.find_all("code"):
        code.replace_with(f"`{code.get_text()}`")
    for li in soup.find_all("li"):
        li.insert_before("- ")
    for pre in soup.find_all("pre"):
        pre.replace_with(
            ''.join(f"\t{line}\n" for line in pre.get_text().strip().split("\n")))
    for br in soup.find_all("br"):
        br.replace_with("\n\n")
    for p in soup.find_all("p"):
        p.insert_before("\n\n")
    text = soup.get_text()
    lines = [line.rstrip() for line in text.splitlines()]
    keywords = {"Example": 2, "Constraints": 2}
    for i, line in enumerate(lines):
        for keyword, level in keywords.items():
            if keyword in line:
                lines[i] = f"{'#' * level} {line}"
    text = "\n".join(line for line in lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()

async def main():
    """Main entry point for running the LeetCode client from command line."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--full", action="store_true", help="Fetch all problems")
    parser.add_argument("--daily", action="store_true", help="Fetch daily challenge")
    parser.add_argument("--date", type=str, help="Fetch daily challenge for a specific date")
    parser.add_argument("--monthly", nargs=2, type=int, metavar=('YEAR', 'MONTH'), help="Fetch monthly daily challenges (e.g., --monthly 2025 1)")
    args = parser.parse_args()
    
    client = LeetCodeClient(data_dir="data")

    if args.init:
        logger.info("Initializing database...")
        await client.init_all_problems()

    if args.full:
        logger.info("Fetching all problems...")
        problems = await client.init_all_problems()
        for i, problem in enumerate(problems):
            problems[i] = await client.get_problem(problem['id'])
    
    if args.daily:
        logger.info("Fetching daily challenge...")
        daily = await client.fetch_daily_challenge()
        print(json.dumps(daily, indent=4))

    if args.date:
        logger.info(f"Fetching daily challenge for {args.date}...")
        daily = await client.get_daily_challenge(date_str=args.date)
        print(json.dumps(daily, indent=4))

    if args.monthly:
        year, month = args.monthly
        logger.info(f"Fetching monthly daily challenges for {year}-{month:02d}...")
        # Validate date range
        if year < 2020 or (year == 2020 and month < 4):
            logger.error("Monthly daily challenges are only available from April 2020 onwards.")
            print("Error: Monthly daily challenges are only available from April 2020 onwards.")
            return
        monthly_data = await client.fetch_monthly_daily_challenges(year, month)
        print(json.dumps(monthly_data, indent=4, ensure_ascii=False))

async def test():
    client = LeetCodeClient(data_dir="data")
    problem = await client.get_problem(slug="two-sum")
    print(json.dumps(problem, indent=4))

if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(test())