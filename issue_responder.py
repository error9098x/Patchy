"""
Issue Responder
Handles GitHub webhook → parse @mention → LLM response → post comment
"""

import json
import os
import re
import threading
import github_client
import pr_reviewer
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
    sender = payload.get("sender", {})

    # Check if bot is @mentioned
    comment_body = comment.get("body", "")
    bot_name = os.getenv("GITHUB_APP_SLUG") or github_client.APP_SLUG or "patchybot-dev"

    if _is_bot_author(sender, bot_name):
        return {"status": "ignored", "message": "Ignoring bot-authored comment"}

    if not _mentions_patchy(comment_body, bot_name):
        return {"status": "ignored", "message": "Bot not mentioned"}

    # Get installation ID
    installation_id = installation.get("id")
    if not installation_id:
        return {"status": "error", "message": "No installation ID in webhook"}

    repo_full_name = repo.get("full_name", "")
    issue_number = issue.get("number", 0)
    is_pull_request = bool(issue.get("pull_request"))

    thread = threading.Thread(
        target=_process_mention,
        args=(installation_id, repo_full_name, issue_number, comment_body, is_pull_request),
        daemon=True,
    )
    thread.start()

    return {
        "status": "accepted",
        "message": f"Queued mention response for #{issue_number}",
        "issue": issue_number,
        "repo": repo_full_name,
        "is_pull_request": is_pull_request,
    }


def _process_mention(installation_id, repo_full_name, issue_number,
                     comment_body, is_pull_request):
    """Generate and post the response outside the webhook request path."""
    ack_comment_id = None

    try:
        if is_pull_request:
            if pr_reviewer.is_review_request(comment_body):
                ack_comment_id = github_client.post_issue_comment(
                    installation_id, repo_full_name, issue_number,
                    "Patchy is running a report-only security review for this PR. I will update this comment with the findings shortly."
                )
                response_text = pr_reviewer.review_pull_request(
                    installation_id, repo_full_name, issue_number, comment_body
                )
            else:
                ack_comment_id = github_client.post_issue_comment(
                    installation_id, repo_full_name, issue_number,
                    "Patchy is reading this PR context now. I will update this comment with an answer shortly."
                )
                response_text = pr_reviewer.answer_pull_request_question(
                    installation_id, repo_full_name, issue_number, comment_body
                )
        else:
            ack_comment_id = github_client.post_issue_comment(
                installation_id, repo_full_name, issue_number,
                "Patchy is looking at this issue now. I will update this comment shortly."
            )
            issue_context = github_client.get_issue_context(
                installation_id, repo_full_name, issue_number
            )
            issue_context["comments"].append(f"@developer: {comment_body}")
            response_text = respond_to_issue(issue_context)

        _publish_response(
            installation_id, repo_full_name, issue_number,
            response_text, ack_comment_id
        )

    except Exception as e:
        print(f"Issue response failed: {e}")
        error_body = f"Patchy hit an error while responding: `{str(e)[:500]}`"
        try:
            _publish_response(
                installation_id, repo_full_name, issue_number,
                error_body, ack_comment_id
            )
        except Exception as post_error:
            print(f"Failed to post error comment: {post_error}")


def _publish_response(installation_id, repo_full_name, issue_number,
                      response_text, ack_comment_id=None):
    if ack_comment_id:
        try:
            return github_client.update_issue_comment(
                installation_id, repo_full_name, ack_comment_id, response_text
            )
        except Exception as e:
            print(f"Failed to update ack comment, posting new comment: {e}")
    return github_client.post_issue_comment(
        installation_id, repo_full_name, issue_number, response_text
    )


def _mentions_patchy(comment_body, bot_name):
    body = (comment_body or "").lower()
    names = {bot_name.lower(), "patchybot", "patchy"}
    for name in names:
        if re.search(rf"@{re.escape(name)}\b", body):
            return True
    return False


def _is_bot_author(sender, bot_name):
    login = (sender or {}).get("login", "").lower()
    sender_type = (sender or {}).get("type", "").lower()
    return sender_type == "bot" or login in {bot_name.lower(), f"{bot_name.lower()}[bot]"}
