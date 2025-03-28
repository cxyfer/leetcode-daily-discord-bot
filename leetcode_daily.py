import os
import requests
import json
import logging
from utils.logger import setup_logging, get_logger
from pathlib import Path

# Set up logging
setup_logging()
logger = get_logger("bot.leetcode")

class LeetCodeClient:
    """
    LeetCode API Client for fetching challenges and problem information
    Supports both LeetCode.com and LeetCode.cn domains
    """
    
    def __init__(self, domain="com", data_dir="./data"):
        """
        Initialize the LeetCode client
        
        Args:
            domain (str): Domain to use - 'com' for leetcode.com or 'cn' for leetcode.cn
            data_dir (str): Directory to store cached data
        """
        self.domain = domain.lower()
        if self.domain not in ["com", "cn"]:
            raise ValueError("Domain must be either 'com' or 'cn'")
        
        self.base_url = f"https://leetcode.{self.domain}"
        self.api_endpoint = f"{self.base_url}/graphql"
        self.time_zone = "UTC+8" if self.domain == "cn" else "UTC"
        self.data_dir = Path(data_dir)
        self.ratings_file = self.data_dir / "leetcode_ratings.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized LeetCode client with domain: leetcode.{self.domain}")
    
    def fetch_daily_challenge_data(self):
        """
        Get the daily challenge question from LeetCode API
        
        Returns:
            dict: Raw API response data
        """
        # GraphQL query statement - different for CN and COM domains
        if self.domain == "cn":
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
                    userStatus
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
        
        # Set request headers and body
        headers = {'Content-Type': 'application/json'}
        payload = {"query": query}
        
        logger.info(f"Fetching daily challenge from LeetCode {self.domain.upper()} API...")
        res = requests.post(self.api_endpoint, headers=headers, json=payload)
        
        # Check if the API request is successful
        if res.status_code != 200:
            error_msg = f"API request failed, status code: {res.status_code}, response: {res.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        return res.json()

    def extract_challenge_info(self, raw_data):
        """
        Extract the information of the daily challenge
        
        Args:
            raw_data (dict): API response JSON data
            
        Returns:
            dict: Extracted challenge information
        """
        if self.domain == "cn":
            question_info = raw_data['data']['todayRecord'][0]
            question = question_info['question']
            # Use constructed link for CN domain
            link = f"{self.base_url}/problems/{question['titleSlug']}/"
        else:
            question_info = raw_data['data']['activeDailyCodingChallengeQuestion']
            question = question_info['question']
            link = f"{self.base_url}{question_info['link']}"
        
        # Extract the fields
        date = question_info['date']
        title = question['title']
        difficulty = question['difficulty']
        qid = question['frontendQuestionId']
        tags = [tag['name'] for tag in question['topicTags']]
        rating = self.get_problem_rating(qid)
        
        return dict(date=date, qid=qid, title=title, difficulty=difficulty, rating=rating, link=link, tags=tags)

    def get_problem_rating(self, problem_id):
        """
        Get the problem rating based on problem ID
        
        Args:
            problem_id (str): LeetCode problem ID
            
        Returns:
            float or int: Problem rating if found, -1 otherwise
        """
        os.makedirs(os.path.dirname(self.ratings_file), exist_ok=True)
        
        # Load existing ratings file if it exists
        if self.ratings_file.exists():
            with open(self.ratings_file, 'r', encoding='utf-8') as f:
                ratings_data = json.load(f)
        else:
            ratings_data = {}
            
        # Check if problem_id exists in our cached data
        if problem_id in ratings_data:
            # Return just the rating value if that's all we need
            if isinstance(ratings_data[problem_id], dict) and 'rating' in ratings_data[problem_id]:
                return ratings_data[problem_id]['rating']
        
        # If not found, try to update the ratings file
        try:
            updated = self.update_ratings_file()
            if updated:
                # Reload the updated data
                with open(self.ratings_file, 'r', encoding='utf-8') as f:
                    ratings_data = json.load(f)
                if problem_id in ratings_data:
                    if isinstance(ratings_data[problem_id], dict) and 'rating' in ratings_data[problem_id]:
                        return ratings_data[problem_id]['rating']
        except Exception as e:
            logger.error(f"Error updating ratings: {e}")
        
        # Return -1 if problem rating is not found
        return -1

    def update_ratings_file(self):
        """
        Update the ratings file from the GitHub repository
        
        Returns:
            bool: True if update was successful, False otherwise
        """
        ratings_url = "https://raw.githubusercontent.com/zerotrac/leetcode_problem_rating/refs/heads/main/ratings.txt"
        
        try:
            logger.info("Updating LeetCode problem ratings...")
            response = requests.get(ratings_url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch ratings: {response.status_code}")
                return False
            
            # Parse the ratings data
            ratings_data = {}
            lines = response.text.strip().split('\n')
            
            # Skip header line
            for line in lines[1:]:  # Skip the header line
                parts = line.strip().split('\t')  # Split by tab, not space
                if len(parts) >= 2:  # Ensure we have at least rating and problem ID
                    try:
                        rating = float(parts[0])
                        problem_id = parts[1]
                        # Store additional information (optional)
                        ratings_data[problem_id] = {
                            'rating': rating,
                            'title': parts[2] if len(parts) > 2 else '',
                            'title_zh': parts[3] if len(parts) > 3 else '',
                            'slug': parts[4] if len(parts) > 4 else '',
                            'contest': parts[5] if len(parts) > 5 else '',
                            'problem_index': parts[6] if len(parts) > 6 else ''
                        }
                    except ValueError:
                        # Skip lines that can't be parsed correctly
                        logger.warning(f"Skipping invalid line: {line}")
                        continue
            
            # Save the parsed data
            with open(self.ratings_file, 'w', encoding='utf-8') as f:
                json.dump(ratings_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Ratings updated successfully. {len(ratings_data)} problems loaded.")
            return True
        
        except Exception as e:
            logger.error(f"Error updating ratings: {e}")
            return False

    def get_daily_challenge(self, date_str=None):
        """
        Get the daily challenge data for the specified date.
        Checks for existing data file first before fetching from LeetCode API.
        
        Args:
            date_str (str, optional): The date string in format 'YYYY-MM-DD'. 
                                     If None, caller should handle getting the current date.
        
        Returns:
            dict: The daily challenge information
        """
        # If date_str is not provided, raise error
        if date_str is None:
            raise ValueError("date_str must be provided in 'YYYY-MM-DD' format")
        
        # Parse date components
        yy, mm, _ = date_str.split('-')
        
        # Create the file path and directory
        file_dir = self.data_dir / self.domain / "daily" / yy / mm
        file_path = file_dir / f"{date_str}.json"
        
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
        
        # If no valid file is found, fetch the data
        if info is None:
            logger.info("Fetching new challenge data...")
            challenge_data = self.fetch_daily_challenge_data()
            info = self.extract_challenge_info(challenge_data)
            file_dir.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            logger.info(f"Challenge data saved to {file_path}")
        
        return info
    
    def fetch_recent_ac_submissions(self, username, limit=15):
        """
        Fetch recent AC (Accepted) submissions for a given username
        
        Args:
            username (str): LeetCode username
            limit (int): Number of submissions to fetch (default: 15)
        
        Returns:
            list: List of recent AC submissions, each containing:
                - id: submission id
                - title: problem title
                - titleSlug: problem title slug
                - timestamp: submission timestamp
        """
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
            response = requests.post(self.api_endpoint, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            if 'errors' in data:
                logger.error(f"GraphQL errors: {data['errors']}")
                return []
            
            submissions = data.get('data', {}).get('recentAcSubmissionList', [])
            logger.info(f"Successfully fetched {len(submissions)} submissions")
            return submissions
            
        except Exception as e:
            logger.error(f"Error fetching submissions: {str(e)}")
            return []

    # Placeholder for future API methods
    def fetch_problem_by_id(self, problem_id):
        """
        Fetch a specific problem by ID
        
        Args:
            problem_id (str): LeetCode problem ID
            
        Returns:
            dict: Problem information
        """
        # Placeholder for implementation
        logger.info(f"Method fetch_problem_by_id not fully implemented yet")
        pass


if __name__ == "__main__":
    try:
        # For testing, create a client instance
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")

        lcus = LeetCodeClient()
        info = lcus.get_daily_challenge(today)
        logger.debug(f"Today's challenge in LCUS: {info['qid']}. {info['title']} ({info['difficulty']})")

        lccn = LeetCodeClient(domain="cn")
        info_cn = lccn.get_daily_challenge(today)
        logger.debug(f"Today's challenge in LCCN: {info_cn['qid']}. {info_cn['title']} ({info_cn['difficulty']})")

        # Fetch recent AC submissions
        submissions = lcus.fetch_recent_ac_submissions("Yawn_Sean", limit=10)
        for submission in submissions:
            logger.debug(f"Submission: {submission['title']} ({submission['timestamp']})")
        
    except Exception as e:
        logger.error(f"Error: {e}") 