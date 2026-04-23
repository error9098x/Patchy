"""
Cerebras LLM Client
Uses official Cerebras Cloud SDK (OpenAI-compatible)
Supports streaming and non-streaming completions
"""

import os
from typing import List, Dict, Optional, Iterator
from cerebras.cloud.sdk import Cerebras

# Initialize client
client = Cerebras(
    api_key=os.environ.get("CEREBRAS_API_KEY")
)

# Default model
DEFAULT_MODEL = "qwen-3-235b-a22b-instruct-2507"

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def chat(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    stream: bool = False,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    top_p: float = 1.0
) -> str | Iterator[str]:
    """
    Call Cerebras chat completion API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (default: qwen-3-235b)
        stream: Whether to stream response
        max_tokens: Max completion tokens
        temperature: Sampling temperature (0-1)
        top_p: Nucleus sampling parameter
    
    Returns:
        Complete response string (if stream=False)
        Iterator of response chunks (if stream=True)
    
    Example:
        >>> response = chat([
        ...     {"role": "system", "content": "You are a security expert."},
        ...     {"role": "user", "content": "Explain SQL injection."}
        ... ])
        >>> print(response)
    """
    response = client.chat.completions.create(
        messages=messages,
        model=model,
        stream=stream,
        max_completion_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p
    )
    
    if stream:
        return _stream_response(response)
    else:
        return response.choices[0].message.content


def _stream_response(stream) -> Iterator[str]:
    """
    Generator that yields chunks from streaming response.
    
    Usage:
        for chunk in chat(..., stream=True):
            print(chunk, end="", flush=True)
    """
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


# =============================================================================
# AGENT-SPECIFIC FUNCTIONS
# =============================================================================

def validate_finding(finding: Dict, code_context: str) -> Dict:
    """
    ValidatorAgent: Ask LLM if finding is real or false positive.
    
    Args:
        finding: Semgrep finding dict
        code_context: Surrounding code (±10 lines)
    
    Returns:
        {
            "is_valid": bool,
            "severity": "critical" | "high" | "medium" | "low",
            "reasoning": str
        }
    """
    prompt = f"""You are a security expert reviewing a potential vulnerability.

**Finding:**
- Type: {finding.get('check_id', 'unknown')}
- File: {finding.get('path', 'unknown')}
- Line: {finding.get('start', {}).get('line', '?')}
- Message: {finding.get('extra', {}).get('message', 'No message')}

**Code Context:**
```
{code_context}
```

**Task:**
Determine if this is a real security issue or a false positive.
Consider:
1. Is user input actually reaching this code path?
2. Are there existing protections (validation, sanitization)?
3. What's the actual exploitability?

Respond in JSON format:
{{
    "is_valid": true/false,
    "severity": "critical/high/medium/low",
    "reasoning": "brief explanation"
}}
"""
    
    messages = [
        {"role": "system", "content": "You are a security expert. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response = chat(messages, temperature=0.3)  # Lower temp for consistency
    
    # Parse JSON response
    import json
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        return {
            "is_valid": True,  # Conservative: assume valid
            "severity": "medium",
            "reasoning": "Failed to parse LLM response"
        }


def generate_fix(finding: Dict, original_code: str) -> Dict:
    """
    FixAgent: Generate a code fix for a validated vulnerability.
    
    Args:
        finding: Validated finding dict
        original_code: Full file content or relevant section
    
    Returns:
        {
            "fixed_code": str,
            "explanation": str,
            "confidence": float (0-1)
        }
    """
    prompt = f"""You are a security engineer fixing a vulnerability.

**Vulnerability:**
- Type: {finding.get('check_id', 'unknown')}
- File: {finding.get('path', 'unknown')}
- Line: {finding.get('start', {}).get('line', '?')}
- Severity: {finding.get('severity', 'unknown')}

**Original Code:**
```
{original_code}
```

**Task:**
Generate a secure fix for this vulnerability.

Requirements:
1. Fix ONLY the vulnerable code
2. Maintain existing functionality
3. Add comments explaining the fix
4. Ensure the fix is syntactically correct

Respond in JSON format:
{{
    "fixed_code": "complete fixed code",
    "explanation": "what changed and why",
    "confidence": 0.95
}}
"""
    
    messages = [
        {"role": "system", "content": "You are a security engineer. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response = chat(messages, temperature=0.5, max_tokens=4096)
    
    import json
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "fixed_code": original_code,  # Fallback: no change
            "explanation": "Failed to generate fix",
            "confidence": 0.0
        }


def respond_to_issue(issue_context: Dict) -> str:
    """
    IssueResponder: Generate helpful response to GitHub issue.
    
    Args:
        issue_context: {
            "title": str,
            "body": str,
            "comments": List[str],
            "repo_name": str
        }
    
    Returns:
        Response text to post as comment
    """
    prompt = f"""You are Patchy, an AI security bot for GitHub repositories.

**Issue Context:**
- Repository: {issue_context.get('repo_name')}
- Title: {issue_context.get('title')}
- Body: {issue_context.get('body', 'No description')}

**Previous Comments:**
{chr(10).join(issue_context.get('comments', []))}

**Task:**
Provide a helpful, security-focused response.

Guidelines:
1. Be concise and actionable
2. If it's a security question, provide specific advice
3. If asking about Patchy, explain what you can do
4. Be friendly but professional
5. Use markdown formatting

Response:
"""
    
    messages = [
        {
            "role": "system",
            "content": "You are Patchy, a friendly AI security bot. You help developers fix security issues in their code."
        },
        {"role": "user", "content": prompt}
    ]
    
    return chat(messages, temperature=0.8, max_tokens=1024)


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def validate_findings_batch(findings: List[Dict], code_contexts: List[str]) -> List[Dict]:
    """
    Validate multiple findings in a single LLM call (cost optimization).
    
    Args:
        findings: List of Semgrep findings
        code_contexts: Corresponding code contexts
    
    Returns:
        List of validation results
    """
    # Build batch prompt
    findings_text = ""
    for i, (finding, context) in enumerate(zip(findings, code_contexts)):
        findings_text += f"""
### Finding {i+1}
- Type: {finding.get('check_id')}
- File: {finding.get('path')}
- Line: {finding.get('start', {}).get('line')}

Code:
```
{context}
```
---
"""
    
    prompt = f"""You are a security expert reviewing {len(findings)} potential vulnerabilities.

{findings_text}

For each finding, determine if it's valid and assign severity.

Respond with a JSON array:
[
    {{"finding_id": 1, "is_valid": true, "severity": "high", "reasoning": "..."}},
    {{"finding_id": 2, "is_valid": false, "severity": "low", "reasoning": "..."}}
]
"""
    
    messages = [
        {"role": "system", "content": "You are a security expert. Respond only with valid JSON array."},
        {"role": "user", "content": prompt}
    ]
    
    response = chat(messages, temperature=0.3, max_tokens=8192)
    
    import json
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Fallback: validate individually
        return [validate_finding(f, c) for f, c in zip(findings, code_contexts)]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def test_connection() -> bool:
    """
    Test if Cerebras API is accessible.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        response = chat(
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10
        )
        return "ok" in response.lower()
    except Exception as e:
        print(f"Cerebras connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test the client
    print("Testing Cerebras connection...")
    if test_connection():
        print("✅ Connection successful!")
        
        # Test streaming
        print("\nTesting streaming:")
        for chunk in chat(
            messages=[{"role": "user", "content": "Count to 5."}],
            stream=True,
            max_tokens=50
        ):
            print(chunk, end="", flush=True)
        print("\n")
    else:
        print("❌ Connection failed. Check CEREBRAS_API_KEY.")
