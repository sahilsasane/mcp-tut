import json
import os

from src.config import PROJECT_INFO, PROJECT_INFO_DIR, logger


async def get_project_info() -> str:
    """Get project information from the knowledge repository"""
    logger.info("Called get_project_info resource.")
    try:
        path = os.path.join(PROJECT_INFO_DIR, PROJECT_INFO)
        if not os.path.exists(path):
            logger.warning(f"No project info found at {path}.")
            return json.dumps({"error": "No project info found."})

        with open(path, "r") as file:
            project_info = json.load(file).get("projects", {})
        return json.dumps(project_info, indent=2)
    except Exception as e:
        logger.error(f"Error fetching project info: {e}")
        return json.dumps({"error": str(e)})


async def get_feature_updates() -> str:
    """Get feature updates from the knowledge repository"""
    logger.info("Called get_feature_updates resource.")
    try:
        path = os.path.join(PROJECT_INFO_DIR, PROJECT_INFO)
        if not os.path.exists(path):
            logger.warning(f"No feature updates found at {path}.")
            return json.dumps({"error": "No feature updates found."})

        with open(path, "r") as file:
            feature_updates = (
                json.load(file).get("projects", {})[0].get("feature_updates", [])
            )
        return json.dumps(feature_updates, indent=2)
    except Exception as e:
        logger.error(f"Error fetching feature updates: {e}")
        return json.dumps({"error": str(e)})


async def get_project_status() -> str:
    """Get project status from the knowledge repository"""
    logger.info("Called get_project_status resource.")
    try:
        path = os.path.join(PROJECT_INFO_DIR, PROJECT_INFO)
        if not os.path.exists(path):
            logger.warning(f"No project status found at {path}.")
            return json.dumps({"error": "No project status found."})

        with open(path, "r") as file:
            project_data = json.load(file).get("projects", {})[0]

            project_status = {
                "milestones": project_data.get("milestones", []),
                "feature_updates": project_data.get("feature_updates", []),
                "risk_register": project_data.get("risk_register", []),
                "deployment_notes": project_data.get("deployment_notes", {}),
            }
        return json.dumps(project_status, indent=2)
    except Exception as e:
        logger.error(f"Error fetching project status: {e}")
        return json.dumps({"error": str(e)})
