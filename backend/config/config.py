from dotenv import load_dotenv
import os

load_dotenv(override=True)
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

if not api_key:
    raise ValueError("AZURE_OPENAI_API_KEY is not set")
if not api_base:
    raise ValueError("AZURE_OPENAI_ENDPOINT is not set")
if not api_version:
    raise ValueError("AZURE_OPENAI_API_VERSION is not set")
if not deployment_name:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME is not set")