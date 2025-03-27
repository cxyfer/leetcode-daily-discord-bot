import os
import requests
import json
import logging
from utils.logger import setup_logging # Added import

# Setup logging configuration once
setup_logging() # Added call

# Get a logger for this module
logger = logging.getLogger(__name__) # Added module logger

class GraphQLClient:
    """
    A base client for interacting with GraphQL APIs.
    """
    def __init__(self, endpoint: str, headers: dict = None):
        """
        Initializes the GraphQL client.

        Args:
            endpoint (str): The URL of the GraphQL endpoint.
            headers (dict, optional): Default headers for requests. Defaults to {'Content-Type': 'application/json'}.
        """
        if not endpoint:
            raise ValueError("GraphQL endpoint URL cannot be empty.")
        self.endpoint = endpoint
        self.headers = headers or {'Content-Type': 'application/json'}

    def execute(self, query: str, variables: dict = None) -> dict:
        """
        Executes a GraphQL query or mutation.

        Args:
            query (str): The GraphQL query string.
            variables (dict, optional): Variables for the GraphQL query. Defaults to None.

        Returns:
            dict: The JSON response from the API.

        Raises:
            Exception: If the API request fails or returns an error.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.info(f"Sending GraphQL request to {self.endpoint}...") # Changed to logger.info
        try:
            res = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=10) # Added timeout
            res.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}") # Changed to logger.error
            raise Exception(f"API request failed: {e}") from e

        response_data = res.json()
        if 'errors' in response_data:
            logger.error(f"GraphQL API returned errors: {response_data['errors']}") # Changed to logger.error
            raise Exception(f"GraphQL API returned errors: {response_data['errors']}")

        logger.info("GraphQL request successful.") # Changed to logger.info
        return response_data

class LeetCodeClient(GraphQLClient):
    """
    A client specifically for interacting with the LeetCode GraphQL API.
    """
    DEFAULT_ENDPOINT = 'https://leetcode.com/graphql'
    DAILY_CHALLENGE_QUERY = """
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

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, headers: dict = None):
        """
        Initializes the LeetCode client.

        Args:
            endpoint (str, optional): The LeetCode GraphQL endpoint URL. Defaults to DEFAULT_ENDPOINT.
            headers (dict, optional): Headers for requests. Defaults to None.
        """
        super().__init__(endpoint, headers)

    def fetch_daily_challenge_raw(self) -> dict:
        """
        Fetches the raw data for the daily challenge question from LeetCode.

        Returns:
            dict: The raw JSON response containing daily challenge information.
        """
        logger.info("Fetching daily challenge from LeetCode API...") # Changed to logger.info
        return self.execute(self.DAILY_CHALLENGE_QUERY)

# --- Existing functions (potentially refactorable into classes later) ---

def extract_challenge_info(raw_data: dict) -> dict:
    """
    Extract the information of the daily challenge.

    Args:
        raw_data (dict): API response JSON data from LeetCodeClient.fetch_daily_challenge_raw().

    Returns:
        dict: Extracted challenge information.

    Raises:
        KeyError: If expected keys are missing in the raw_data.
    """
    try:
        question_info = raw_data['data']['activeDailyCodingChallengeQuestion']
        question = question_info['question']

        # Extract the fields
        date = question_info['date']
        title = question['title']
        difficulty = question['difficulty']
        link = f"https://leetcode.com{question_info['link']}"
        qid = question['frontendQuestionId']
        tags = [tag['name'] for tag in question.get('topicTags', [])] # Use .get for safety
        rating = get_problem_rating(qid) # Keep dependency for now

        return dict(date=date, qid=qid, title=title, difficulty=difficulty, rating=rating, link=link, tags=tags)
    except KeyError as e:
        logger.error(f"Missing expected key in raw API data: {e}") # Changed to logger.error
        raise KeyError(f"Missing expected key in raw API data: {e}") from e
    except TypeError as e:
        logger.error(f"Unexpected data structure in raw API data: {e}. Data: {raw_data}") # Changed to logger.error
        raise TypeError(f"Unexpected data structure in raw API data: {e}") from e


def get_problem_rating(problem_id: str, ratings_file: str = "./data/leetcode_ratings.json") -> float:
    """
    Get the problem rating based on problem ID, updating the cache if necessary.

    Args:
        problem_id (str): LeetCode problem ID.
        ratings_file (str): Path to the ratings JSON file.

    Returns:
        float: Problem rating if found, -1 otherwise.
    """
    os.makedirs(os.path.dirname(ratings_file), exist_ok=True)

    ratings_data = {}
    # Load existing ratings file if it exists
    if os.path.exists(ratings_file):
        try:
            with open(ratings_file, 'r', encoding='utf-8') as f:
                ratings_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Could not load ratings file {ratings_file}: {e}. Will attempt to update.") # Changed to logger.warning
            ratings_data = {} # Ensure ratings_data is a dict

    # Check if problem_id exists in our cached data
    rating_info = ratings_data.get(problem_id)
    if isinstance(rating_info, dict) and 'rating' in rating_info:
        return rating_info['rating']

    # If not found, try to update the ratings file
    logger.info(f"Rating for problem ID {problem_id} not found in cache. Attempting to update ratings file.") # Changed to logger.info
    try:
        updated = update_ratings_file(ratings_file)
        if updated:
            # Reload the updated data
            try:
                with open(ratings_file, 'r', encoding='utf-8') as f:
                    ratings_data = json.load(f)
                rating_info = ratings_data.get(problem_id)
                if isinstance(rating_info, dict) and 'rating' in rating_info:
                    logger.info(f"Found rating for problem ID {problem_id} after update.") # Changed to logger.info
                    return rating_info['rating']
                else:
                     logger.warning(f"Rating for problem ID {problem_id} still not found after successful update.") # Changed to logger.warning
            except (json.JSONDecodeError, FileNotFoundError) as e:
                 logger.error(f"Failed to reload ratings file {ratings_file} after update: {e}") # Changed to logger.error

        else:
            logger.warning("Ratings file update failed or did not occur.") # Changed to logger.warning

    except Exception as e:
        logger.error(f"An error occurred during ratings update check: {e}") # Changed to logger.error

    # Return -1 if problem rating is not found after all attempts
    logger.warning(f"Could not find rating for problem ID {problem_id}.") # Changed to logger.warning
    return -1.0 # Return float for consistency

def update_ratings_file(ratings_file: str = "./data/leetcode_ratings.json") -> bool:
    """
    Update the ratings file from the GitHub repository.

    Args:
        ratings_file (str): Path to the ratings JSON file.

    Returns:
        bool: True if update was successful and data was written, False otherwise.
    """
    ratings_url = "https://raw.githubusercontent.com/zerotrac/leetcode_problem_rating/refs/heads/main/ratings.txt"

    try:
        logger.info("Attempting to update LeetCode problem ratings from GitHub...") # Changed to logger.info
        response = requests.get(ratings_url, timeout=15) # Added timeout
        response.raise_for_status() # Check for HTTP errors

        # Parse the ratings data
        new_ratings_data = {}
        lines = response.text.strip().split('\n')

        if not lines or len(lines) <= 1:
             logger.warning("Downloaded ratings data is empty or only contains header.") # Changed to logger.warning
             return False

        # Skip header line
        for i, line in enumerate(lines[1:], 1): # Start enumeration from 1 for line number logging
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                try:
                    rating = float(parts[0])
                    problem_id = parts[1]
                    new_ratings_data[problem_id] = {
                        'rating': rating,
                        'title': parts[2] if len(parts) > 2 else '',
                        'title_zh': parts[3] if len(parts) > 3 else '',
                        'slug': parts[4] if len(parts) > 4 else '',
                        'contest': parts[5] if len(parts) > 5 else '',
                        'problem_index': parts[6] if len(parts) > 6 else ''
                    }
                except ValueError:
                    logger.warning(f"Skipping invalid rating line {i+1}: {line}") # Changed to logger.warning
                    continue
            else:
                 logger.warning(f"Skipping malformed line {i+1} (not enough parts): {line}") # Changed to logger.warning


        if not new_ratings_data:
            logger.warning("No valid ratings data parsed from the downloaded file.") # Changed to logger.warning
            return False

        # Save the parsed data
        try:
            os.makedirs(os.path.dirname(ratings_file), exist_ok=True)
            with open(ratings_file, 'w', encoding='utf-8') as f:
                json.dump(new_ratings_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Ratings updated successfully. {len(new_ratings_data)} problems loaded into {ratings_file}.") # Changed to logger.info
            return True
        except IOError as e:
            logger.error(f"Failed to write updated ratings to {ratings_file}: {e}") # Changed to logger.error
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch ratings from {ratings_url}: {e}") # Changed to logger.error
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during ratings update: {e}") # Changed to logger.error
        return False

def save_to_file(info: dict, output_dir: str = "./data/daily"):
    """
    Saves the challenge information to a JSON file named by date.

    Args:
        info (dict): The dictionary containing challenge information.
        output_dir (str): The base directory to save the file.
    """
    try:
        date = info['date']
        yy, mm, _ = date.split('-')
        target_dir = os.path.join(output_dir, yy, mm)
        os.makedirs(target_dir, exist_ok=True)
        filename = os.path.join(target_dir, f"{date}.json")

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=4)

        logger.info(f"Challenge info saved to {filename}") # Changed to logger.info
    except KeyError as e:
         logger.error(f"Missing 'date' key in info dictionary: {e}") # Changed to logger.error
    except IOError as e:
         logger.error(f"Failed to save challenge info to file: {e}") # Changed to logger.error
    except Exception as e:
         logger.error(f"An unexpected error occurred during file saving: {e}") # Changed to logger.error


if __name__ == "__main__":
    try:
        # Initialize the LeetCode client
        leetcode_client = LeetCodeClient()

        # Fetch raw data
        raw_data = leetcode_client.fetch_daily_challenge_raw()

        # Extract relevant information
        challenge_info = extract_challenge_info(raw_data)

        # Save the information to a file
        save_to_file(challenge_info, output_dir="./data/daily")

    except Exception as e:
        # Catch any exception from the process and log it
        logger.critical(f"Failed to process daily LeetCode challenge: {e}", exc_info=True) # Changed to logger.critical