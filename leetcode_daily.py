import os
import requests
import json
import logging
from utils.logger import setup_logging, get_logger
from pathlib import Path

# Set up logging
setup_logging()
logger = get_logger("bot.lcus")

def fetch_raw_data():
    """
    Get the daily challenge question from LeetCode
    
    Returns:
        dict: Information about the daily challenge question, including title, difficulty, link, etc.
    """
    # LeetCode GraphQL API endpoint
    leetcode_api_endpoint = 'https://leetcode.com/graphql'
    
    # GraphQL query statement
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
    
    logger.info("Fetching daily challenge from LeetCode API...")
    res = requests.post(leetcode_api_endpoint, headers=headers, json=payload)
    
    # Check if the API request is successful
    if res.status_code != 200:
        error_msg = f"API request failed, status code: {res.status_code}, response: {res.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    return res.json()

def extract_challenge_info(raw_data):
    """
    Extract the information of the daily challenge
    
    Args:
        raw_data (dict): API response JSON data
        
    Returns:
        dict: Extracted challenge information
    """
    question_info = raw_data['data']['activeDailyCodingChallengeQuestion']
    question = question_info['question']
    
    # Extract the fields
    date = question_info['date']
    title = question['title']
    difficulty = question['difficulty']
    link = f"https://leetcode.com{question_info['link']}"
    qid = question['frontendQuestionId']
    tags = [tag['name'] for tag in question['topicTags']]
    rating = get_problem_rating(qid)
    
    return dict(date=date, qid=qid, title=title, difficulty=difficulty, rating=rating, link=link, tags=tags)

def get_problem_rating(problem_id, ratings_file="./data/leetcode_ratings.json"):
    """
    Get the problem rating based on problem ID
    
    Args:
        problem_id (str): LeetCode problem ID
        
    Returns:
        float or None: Problem rating if found, None otherwise
    """
    os.makedirs(os.path.dirname(ratings_file), exist_ok=True)
    
    # Load existing ratings file if it exists
    if os.path.exists(ratings_file):
        with open(ratings_file, 'r', encoding='utf-8') as f:
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
        updated = update_ratings_file(ratings_file)
        if updated:
            # Reload the updated data
            with open(ratings_file, 'r', encoding='utf-8') as f:
                ratings_data = json.load(f)
            if problem_id in ratings_data:
                if isinstance(ratings_data[problem_id], dict) and 'rating' in ratings_data[problem_id]:
                    return ratings_data[problem_id]['rating']
    except Exception as e:
        logger.error(f"Error updating ratings: {e}")
    
    # Return -1 if problem rating is not found
    return -1

def update_ratings_file(ratings_file="./data/leetcode_ratings.json"):
    """
    Update the ratings file from the GitHub repository
    
    Args:
        ratings_file (str): Path to the ratings JSON file
        
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
        with open(ratings_file, 'w', encoding='utf-8') as f:
            json.dump(ratings_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Ratings updated successfully. {len(ratings_data)} problems loaded.")
        return True
    
    except Exception as e:
        logger.error(f"Error updating ratings: {e}")
        return False

def save_to_file(info, output_dir="./data/daily"):
    date = info['date']
    yy, mm, _ = date.split('-')
    os.makedirs(f"{output_dir}/{yy}/{mm}", exist_ok=True)
    filename = f"{output_dir}/{yy}/{mm}/{date}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=4)
    
    logger.info(f"Challenge info saved to {filename}")

def get_daily_challenge(date_str=None):
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
    file_dir = Path(f"data/daily/{yy}/{mm}")
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
        challenge_data = fetch_raw_data()
        info = extract_challenge_info(challenge_data)
        file_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=4)
        logger.info(f"Challenge data saved to {file_path}")
    
    return info

if __name__ == "__main__":
    try:
        # For testing, use a specific date
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        info = get_daily_challenge(today)
        logger.debug(f"Today's challenge: {info['qid']}. {info['title']} ({info['difficulty']})")
    except Exception as e:
        logger.error(f"Error: {e}") 