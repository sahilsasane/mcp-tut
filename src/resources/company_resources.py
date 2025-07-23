import json
import os

from src.config import COMPANY_INFO, INTERNAL_DOCS, KNOWLEDGE_DIR, logger


async def get_company_info() -> str:
    """Get company information from the knowledge repository"""
    logger.info("Called get_company_info resource.")
    try:
        path = os.path.join(KNOWLEDGE_DIR, COMPANY_INFO)
        if not os.path.exists(path):
            logger.warning(f"No company info found at {path}.")
            return json.dumps({"error": "No company info found."})

        with open(path, "r") as file:
            company_info = json.load(file).get("company", {})
        return json.dumps(company_info, indent=2)
    except Exception as e:
        logger.error(f"Error fetching company info: {e}")
        return json.dumps({"error": str(e)})


async def get_solution_info() -> str:
    """Get solution information from the knowledge repository"""
    logger.info("Called get_solution_info resource.")
    try:
        path = os.path.join(KNOWLEDGE_DIR, COMPANY_INFO)
        if not os.path.exists(path):
            logger.warning(f"No solution info found at {path}.")
            return json.dumps({"error": "No solution info found."})

        with open(path, "r") as file:
            solution_info = json.load(file).get("solutions", {})
        return json.dumps(solution_info, indent=2)
    except Exception as e:
        logger.error(f"Error fetching solution info: {e}")
        return json.dumps({"error": str(e)})


async def get_all_info() -> str:
    """Get all information from the knowledge repository"""
    logger.info("Called get_all_info resource.")
    try:
        path = os.path.join(KNOWLEDGE_DIR, COMPANY_INFO)
        if not os.path.exists(path):
            logger.warning(f"No solution info found at {path}.")
            return json.dumps({"error": "No solution info found."})

        with open(path, "r") as file:
            all_info = json.load(file)
        return json.dumps(all_info, indent=2)
    except Exception as e:
        logger.error(f"Error fetching solution info: {e}")
        return json.dumps({"error": str(e)})


async def get_company_docs() -> str:
    """Get company docs from a file for giving access to the internal team"""
    logger.info("Called get_company_docs resource.")
    try:
        path = os.path.join(KNOWLEDGE_DIR, INTERNAL_DOCS)
        if not os.path.exists(path):
            logger.warning(f"No company docs found at {path}.")
            return json.dumps({"error": "No company docs found."})

        with open(path, "r") as file:
            company_docs = json.load(file)
        return json.dumps(company_docs, indent=2)
    except Exception as e:
        logger.error(f"Error fetching company docs: {e}")
        return json.dumps({"error": str(e)})
