# core/retry_service.py

import os
import json
from utils.paths import RETRIES_DIR, PERMANENT_FAILURE_DIR
from utils.colors import bcolors
from utils.file_ops import delete_file, move_file
from scripts.generate_landing_pages import generate_blog

def retry_blog(file_name):
    """
    Retry the blog generation based on a saved retry payload.
    
    Args:
        file_name (str): The retry payload filename (JSON).
    
    Returns:
        dict: Result dictionary with slug and status.
    """
    try:
        slug = file_name.replace(".json", "")
        retry_path = os.path.join(RETRIES_DIR, file_name)

        with open(retry_path, "r", encoding="utf-8") as f:
            retry_payload = json.load(f)

        retry_row = {
            "topic": retry_payload["topic"],
            "primary_keyword": retry_payload["primary_keyword"],
            "slug": retry_payload["slug"],
            "meta_title": retry_payload.get("topic", ""),
            "keywords": "ADHD, Neurodivergence"
        }

        print(f"{bcolors.OKBLUE}🔄 Retrying blog generation for: {slug}{bcolors.ENDC}")
        result = generate_blog(retry_row)

        if result and result.get("status") == "success":
            delete_file(retry_path)
            print(f"{bcolors.OKGREEN}🧹 Successfully retried and cleaned: {slug}{bcolors.ENDC}")
        else:
            new_failure_path = os.path.join(PERMANENT_FAILURE_DIR, f"__failed_{file_name}")
            move_file(retry_path, new_failure_path)
            print(f"{bcolors.WARNING}🚨 Permanently failed blog moved: __failed_{file_name}{bcolors.ENDC}")

        return result

    except Exception as e:
        print(f"{bcolors.FAIL}❌ Retry failed for {file_name}: {e}{bcolors.ENDC}")
        return {"slug": slug, "status": "failed", "error": str(e)}
