---
categories:
- productivity
description: Extract technical discussions from past Hermes sessions and compile them
  into structured design documents. Use when the user says "整理成文档", "写入技术设计文档", "把讨论内容整理",
  or similar.
name: compile-session-to-document
summary: Extract technical discussions from past Hermes sessions and compile them
  into structured design documents. Use when the user says "整理成文档", "写入技术设计文档", "把讨论内容整理",
  or similar.
triggers: []
---

# Compile Past Session Discussions into Documents

## When to Use

- User wants to compile past conversation content into a structured document
- There's a known session with technical discussions that need to be formalized
- The raw content is too large for a single delegate_task

## Workflow

### Step 1: Find the Relevant Session

```
session_search(query="<topic keywords>", limit=5)
```

Look for session IDs in format `session_YYYYMMDD_HHMMSS_xxxxxx`.

### Step 2: Extract Raw Content to Temp File

Use `execute_code` with Python to:
1. Read the session JSON file from `~/.hermes/sessions/`
2. Extract the relevant message range (look for ASSISTANT messages with substantive content)
3. Save to `/tmp/<descriptive_name>_raw.txt`

### Step 3: Read Content in Chunks

Read the temp file in chunks of ~600 lines using `read_file` with offset/limit.
- First read: offset=1, limit=600
- Subsequent: offset=prev_offset+600, limit=600
- Continue until all content is read

### Step 4: Synthesize and Write Document

Based on the chunked readings, write the structured document directly using `write_file`.

## Pitfalls

### delegate_task fails on very large content (>200K input tokens)
- **Symptom**: delegate_task times out after hitting max_iterations with huge input
- **Cause**: Subagent receives 300K+ tokens of raw discussion, can't process in time
- **Fix**: Don't delegate. Read chunks manually in the main session and synthesize directly
- **Prevention**: For content >100KB extracted, always use chunked reading approach

### Output truncation in raw extraction
- **Symptom**: Assistant messages get truncated by output length limit mid-content
- **Cause**: The original session had responses that hit token limits
- **Fix**: Look for continuation messages (user message = "[System: Your previous response was truncated...]")
- **Prevention**: When reading chunks, check for truncation markers and read the continuation from the next chunk

## Document Structure Template

For technical design documents:
1. Document overview (version, date, status, related docs)
2. Requirements/needs analysis
3. Technical decisions with comparison tables
4. Architecture design with ASCII diagrams
5. Implementation details with code examples
6. Data models
7. Error handling / edge cases
8. Performance considerations
9. Summary table
10. Pending items
11. Source attribution (session ID)

## Tips

- Preserve code examples and ASCII diagrams from the original discussion
- Use comparison tables to summarize decision rationale
- Mark the source session at the bottom of the document
- Keep the document faithful to the original discussion — don't fabricate content
- For game project docs, save to `/mnt/data/worldGameSpace/docs/`