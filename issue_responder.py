"""
Issue Responder
Handles GitHub webhook → parse @mention → LLM response → post comment
"""

import json
import github_client
from tools.nvidia_client import respond_to_issue


def handle_webhook(payload_body, signature):
    """Process incoming GitHub webhook.
    
    Returns:
        dict with 'action' taken and 'status'
    """
    # Verify signature
    if not github_client.verify_webhook_signature(payload_body, signature):
        return {"status": "error", "message": "Invalid signature"}

    payload = json.loads(payload_body)
    event_action = payload.get("action", "")

    # We only care about issue_comment.created
    if event_action != "created":
        return {"status": "ignored", "message": f"Action '{event_action}' not handled"}

    comment = payload.get("comment", {})
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})

    # Check if bot is @mentioned
    comment_body = comment.get("body", "")
    bot_name = "patchybot-dev"  # Match GitHub App slug
    
    if f"@{bot_name}" not in comment_body.lower() and "@patchybot" not in comment_body.lower():
        return {"status": "ignored", "message": "Bot not mentioned"}

    # Get installation ID
    installation_id = installation.get("id")
    if not installation_id:
        return {"status": "error", "message": "No installation ID in webhook"}

    repo_full_name = repo.get("full_name", "")
    issue_number = issue.get("number", 0)

    try:
        # Build context for LLM
        issue_context = {
            "title": issue.get("title", ""),
            "body": issue.get("body", ""),
            "comments": [comment_body],
            "repo_name": repo_full_name
        }

        # Generate response
        response_text = respond_to_issue(issue_context)

        # Post comment
        github_client.post_issue_comment(
            installation_id, repo_full_name, issue_number, response_text
        )

        return {
            "status": "ok",
            "message": f"Responded to issue #{issue_number}",
            "issue": issue_number,
            "repo": repo_full_name
        }

    except Exception as e:
        print(f"Issue response failed: {e}")
        return {"status": "error", "message": str(e)}
