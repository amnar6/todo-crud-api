# Job Card: Task Auto-Categorization & Priority Estimator

## What it does (one sentence):
Analyzes a user-provided task or todo description and assigns a canonical category, priority level, estimated completion time in minutes, and confidence score.

## Input:
{
  "description": "string, 3-1000 characters"
}

## Output:
{
  "category": one of ["work", "personal", "finance", "health", "urgent", "other"],
  "priority": one of ["low", "normal", "high"],
  "estimated_minutes": integer (1-480),
  "confidence": float (0.0-1.0),
  "reason": "string, one concise sentence"
}

## It must never:
- Invent categories outside the closed list.
- Return raw free text or markdown wrapper formatting.
- Default to guessing when ambiguous.

## When unsure it should:
Return category `"other"` with confidence `< 0.5` and priority `"normal"`.