import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import logger  # Assuming logger is defined in a notifier module
from discord import send_discord_alert  # Provided by user


def IPONews(url: str):
    """
    Fetch IPO news from the specified URL.
    
    Args:
        url (str): The URL to fetch IPO news from.
        
    Returns:
        dict or None: JSON response if successful, None if the request fails.
    """
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to fetch IPO news. Status code: {response.status_code}")
        return None
    return response.json()


def get_last_max_id(state_file: str = "last_ipo_state.json") -> int:
    """
    Read the last max IPO ID from the state file.
    
    Args:
        state_file (str): Path to the JSON state file.
        
    Returns:
        int: The last max IPO ID (0 if file doesn't exist or invalid).
    """
    if not os.path.exists(state_file):
        logger.info("No state file found. Treating all IPOs as new.")
        return 0
    try:
        with open(state_file, "r") as f:
            data = json.load(f)
            return data.get("last_max_id", 0)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Invalid state file: {e}. Resetting to 0.")
        return 0


def update_last_max_id(max_id: int, state_file: str = "last_ipo_state.json"):
    """
    Update the state file with the new max IPO ID.
    
    Args:
        max_id (int): The new max IPO ID.
        state_file (str): Path to the JSON state file.
    """
    data = {"last_max_id": max_id}
    with open(state_file, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Updated state file with max IPO ID: {max_id}")


def format_number(number: str) -> str:
    """
    Format a number string with commas for readability.
    
    Args:
        number (str): Number as a string.
        
    Returns:
        str: Formatted number with commas.
    """
    try:
        return "{:,}".format(int(number))
    except ValueError:
        return number


def create_discord_embed(ipo_data: list):
    """
    Create a visually appealing Discord embed payload for up to the top 3 IPO news items.
    
    Args:
        ipo_data (list): List of IPO news items.
        
    Returns:
        dict: Discord embed payload with up to 3 embeds.
    """
    embeds = []
    
    # Limit to top 3 IPO entries
    for ipo in ipo_data[:3]:
        # Set color and status emoji based on status
        status = ipo['status'].lower()
        color = 0x00FF00 if status == "open" else 0xFF0000
        
        # Build description with key info
        description = (
            f"**Sector**: {ipo['sectorName']}\n"
            f"**Share Type**: {ipo['shareType'].capitalize()}\n"
            f"**Rating**: {ipo['rating'] or 'N/A'}"
        )
        
        embed = {
            "title": f"{ipo['companyName']} ({ipo['stockSymbol']})",
            "description": description,
            "color": color,
            "fields": [
                {
                    "name": "📊 Status",
                    "value": f"{ipo['status']}",
                    "inline": True
                },
                {
                    "name": "💵 Price per Unit",
                    "value": f"NPR {ipo['pricePerUnit']}",
                    "inline": True
                },
                {
                    "name": "📈 Total Units",
                    "value": format_number(ipo['units']),
                    "inline": True
                },
                {
                    "name": "🔢 Min/Max Units",
                    "value": f"{format_number(ipo['minUnits'])} / {format_number(ipo['maxUnits'])}",
                    "inline": True
                },
                {
                    "name": "📅 Opening Date",
                    "value": f"{ipo['openingDateAD']} ({ipo['openingDateBS']})",
                    "inline": True
                },
                {
                    "name": "🕒 Closing Date",
                    "value": f"{ipo['closingDateAD']} ({ipo['closingDateBS']}) at {ipo['closingDateClosingTime']}",
                    "inline": True
                },
                {
                    "name": "🏢 Share Registrar",
                    "value": ipo['shareRegistrar'],
                    "inline": True
                },
                {
                    "name": "💰 Total Amount",
                    "value": f"NPR {format_number(ipo['totalAmount'])}",
                    "inline": True
                }
            ],
            "thumbnail": {
                "url": "https://www.svgrepo.com/show/483222/stock-market.svg"  # Stock market icon
            },
            "footer": {
                "text": "Reported by IPO Notifier Bot | @dev-sandip"
            },
            "timestamp": datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()  # IST (UTC+5:30)
        }
        embeds.append(embed)
    
    return {
        "username": "IPO Notifier",
        "avatar_url": "https://img.icons8.com/fluency/48/000000/bullish.png",  # Bull market icon
        "embeds": embeds
    }


def main():
    """
    Main function to fetch IPO news, detect new IPOs, create a Discord embed for top 3 new IPOs,
    and send via webhook. Optimized for cron job execution.
    """
    load_dotenv()
    
    # Environment variable checks
    initial_url = os.getenv("IPO_NEWS_URL")
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if initial_url is None:
        logger.error("IPO_NEWS_URL is not set in environment variables.")
        return
    
    if discord_webhook_url is None:
        logger.error("DISCORD_WEBHOOK_URL is not set in environment variables.")
        return
    
    # URL parameters
    pageNo = 1
    itemsPerPage = 10
    pagePerDisplay = 5
    url = f"{initial_url}?&pageNo={pageNo}&itemsPerPage={itemsPerPage}&pagePerDisplay={pagePerDisplay}"
    
    try:
        ipo_news = IPONews(url)
        if ipo_news and ipo_news.get("statusCode") == 200 and ipo_news.get("result", {}).get("data"):
            all_data = ipo_news["result"]["data"]
            logger.info(f"Fetched IPO news with {len(all_data)} items.")
            
            # Get last max ID from state file
            last_max_id = get_last_max_id()
            
            # Extract current IPO IDs and find new ones (ipoId > last_max_id)
            current_ids = [item["ipoId"] for item in all_data]
            max_current_id = max(current_ids) if current_ids else 0
            new_data = [item for item in all_data if item["ipoId"] > last_max_id]
            
            if new_data:
                logger.info(f"New IPOs detected: {len(new_data)} (IDs: {[item['ipoId'] for item in new_data]})")
                # Limit to top 3 new IPOs
                new_data_limited = new_data[:3]
                payload = create_discord_embed(new_data_limited)
                send_discord_alert(payload, discord_webhook_url)
                logger.info("Discord alert sent for new IPOs.")
                
                # Update state with new max ID
                update_last_max_id(max_current_id)
            else:
                logger.info(f"No new IPOs. Current max ID: {max_current_id} (last seen: {last_max_id})")
        else:
            logger.info("No IPO news fetched or invalid response.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()