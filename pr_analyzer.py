import requests
# from langchain_core.prompts import PromptTemplate
from langchain_mistralai import ChatMistralAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables
load_dotenv(find_dotenv())

GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PR_NUMBER = os.getenv("GITHUB_PR_NUMBER")


# ================================================================================================================================================

# get details of single pr on the basis of pr number
def get_pull_request():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{PR_NUMBER}"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

# ================================================================================================================================================

# Function to get files changed in a specific PR
def get_pr_files():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{PR_NUMBER}/files"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None


# ================================================================================================================================================

# Function to extract PR details
def get_pr_details(pr):
    pr_data = {
        "title": pr.get("title"),
        "description": pr.get("body"),
        "author": pr.get("user", {}).get("login"),
        "url": pr.get("html_url"),
        "number": pr.get("number")
    }
    return pr_data


# ================================================================================================================================================

# Summarizing code changes using LangChain
def summarize_code_changes(code_diff):
    # Create a prompt template for code summarization
    # Define the prompt template
    prompt_template = """
        You are an **Apex Code Review AI** specialized in analyzing pull requests for best practices, governor limits, and security risks.

        **Objective:**
        - Review the entire code thoroughly before making judgments.
        - Identify potential issues and suggest improvements.
        - If no issues are found, explicitly state that the code follows best practices.

        **Common Apex Issues to Detect:**
        1️⃣ **SOQL inside `for` loops** → Avoid SOQL queries inside loops to prevent governor limit errors.
        2️⃣ **Unsecured SOQL queries** → Ensure queries have proper filtering to avoid security risks.
        3️⃣ **Unbulkified DML operations** → Optimize DML statements for large datasets to prevent governor limit errors.
        4️⃣ **Hardcoded IDs** → Avoid hardcoding IDs; fetch them dynamically instead.
        5️⃣ **Improper use of `@AuraEnabled`** → Ensure methods are secured and properly scoped.
        6️⃣ **Excessive CPU time usage** → Avoid deep nesting and unnecessary computations to reduce CPU time.

        **Response Format:**
        ```
        [file_name.cls]
        Line [line_number]: [Issue Type] - [Description]
        Suggestion: [Possible Fix]
        Severity: [Error or warning]
        ```

        **Pull Request Data:**
        {pr_data}

        **Instructions:**
        - Carefully examine each line of code for the issues listed above.
        - Provide a detailed analysis, specifying the line number and type of issue and please mention the severity of issue detected during your analysis.
        - Offer clear and actionable suggestions for improvement.
        - Ensure your response is structured and easy to understand.
        - Also mention Error vs Warning which may be caused by the issue listed.
        - Categorised and group the feedback/(issues detected) based on their severity.
    """


    prompt = PromptTemplate(input_variables=["pr_data"], template=prompt_template)

    # Initialize Mistral Chat Model
    llm = ChatMistralAI(model="mistral-large-latest", temperature=0.7)

    # Create LLM Chain     
    chain = prompt | llm

    # Get summary of code changes
    summary = chain.invoke({"pr_data": code_diff})
    return summary.content

# ================================================================================================================================================

# function to link everything for single pr

def analyze_pull_request():
    pr = get_pull_request()
    if pr:
        pr_details = get_pr_details(pr)
        print(f"PR Title: {pr_details['title']}")
        print(f"Author: {pr_details['author']}")
        print(f"PR URL: {pr_details['url']}")
        print(f"PR Description: {pr_details['description']}")
        
        # Fetch the files changed in this PR
        files_changed = get_pr_files()
        if files_changed:
            for file in files_changed:
                # print(f"File: {file['filename']}")
                # print(f"Status: {file['status']}")
                # print(f"Changes: {file['patch'][:500]}...")  # Limit the output for large diffs
                
                # Summarize the code changes using LangChain
                pr_summary = summarize_code_changes(file['patch'])
                print(f"Code Changes Summary: {pr_summary}")
                print("="*80)
    else:
        print("No PRs found or error fetching PRs.")

# ================================================================================================================================================
# post comment on the pr

def post_pr_comment(comment):
    """Post analysis result as a PR comment"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    payload = {"body": comment}
    requests.post(url, headers=headers, json=payload)


# ================================================================================================================================================

# Run the PR analysis

if __name__ == "__main__":
    analysis_result = analyze_pull_request()
    post_pr_comment(analysis_result)