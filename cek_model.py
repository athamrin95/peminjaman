import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def check_env(api_key:str, base_url:str, model:str) -> str:
    """Returns None if .env is loaded properly and the necessary properties are present."""
    if any(value is None or value == "" for value in(api_key, base_url, model)):
        return "OPENAI_API_KEY, OPENAI_BASE_URL, and/or OPENAI_MODEL is missing or cannot be read from your .env file. Exiting..."
    else:
        return None

def main() -> None:
    # Load the .env properties first
    load_dotenv()
    result = check_env(os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_BASE_URL"), os.getenv("OPENAI_MODEL"))
    if result:
        print(result)
        sys.exit(1)

    # Specify the model
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        use_responses_api=True
    )

    # Ask a single question and check the response
    question = "How are you?"
    response = model.invoke(question)
    print(f"Question: {question}")
    print(f"Agent answer: {response.text}")
    print(f"Usage metadata: {response.usage_metadata}")
    

if __name__ == "__main__":
    main()