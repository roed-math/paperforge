#!/usr/bin/env python3
"""Extraction + sanitization for published session records.

This module reproduces, byte-for-byte, the pipeline that generated gq2's 20
published roe_formalization__session_NN.json files, so the same code can be
trusted to generate further corpora (gq2 validates this against ground truth
with its validate_formalization.py).

Extraction rule (verified against all 20 published formalization files):
* Read the MAIN session transcript only (subagent transcripts are counted in
  the token ledger but their prose is not part of the published record).
* Claude Code writes one JSONL line per content block; all lines of one API
  message share message.id.  Group lines by message.id in first-occurrence
  order.
* Skip messages whose model is "<synthetic>" (spend-limit / API-error
  placeholders) or missing.
* A message's text is the concatenation of its distinct nonempty text blocks
  in order of appearance ("\n\n" joined); replayed lines after resume/compact
  repeat identical blocks and are collapsed by the distinct-blocks rule.
* Messages with no text are dropped (tool-only / thinking-only messages).
* The published timestamp is the message's FIRST transcript-line timestamp,
  truncated to whole seconds, with a "Z" suffix.
* Thinking blocks, tool payloads, and all user/human text are never emitted.

Sanitization (matches the published policy):
* absolute local paths and ~-paths -> "[local path]"
* local session ids (8-hex prefixes / UUIDs of Claude Code sessions)
  -> "[private session id]"
* hardware-capacity phrases ("<n> core...") -> "[private capacity]"
* a final audit pass (audit_text) flags anything that still looks like a
  secret, an email address, or a personal path so a human can review.

Instance-editorial rules come from the records config's "sanitize" block
(call configure() before redact/audit_text):

    "sanitize": {
      "keep_emails": ["extra@allowed.example"],
      "user_echo_replacements": [["Go ahead", "the instruction to proceed"]],
      "private_name_replacements": [["(?i)pattern", "replacement"]],
      "audit_extra_patterns": [["private name", "(?i)pattern"]]
    }
"""
import json
import re

PUBLIC_MODEL_NAMES = {
    "claude-fable-5": "Fable 5",
    "claude-opus-4-8": "Opus 4.8",
    "claude-opus-4-7": "Opus 4.7",
    "claude-sonnet-4-5": "Sonnet 4.5",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
    "claude-haiku-5": "Haiku 5",
}


def public_model(model_id):
    return PUBLIC_MODEL_NAMES.get(model_id, model_id)


def extract_messages(path):
    """Yield published-record message dicts from one main transcript."""
    first_ts = {}
    order = []
    by_id = {}
    anon = []
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "assistant":
            continue
        msg = d.get("message") or {}
        model = msg.get("model")
        if model in (None, "<synthetic>"):
            continue
        mid = msg.get("id")
        content = msg.get("content")
        texts = []
        if isinstance(content, list):
            texts = [p.get("text", "") for p in content
                     if isinstance(p, dict) and p.get("type") == "text"
                     and p.get("text", "").strip()]
        elif isinstance(content, str) and content.strip():
            texts = [content]
        if mid:
            if mid not in first_ts:
                first_ts[mid] = d.get("timestamp")
                order.append(mid)
                by_id[mid] = {"model": model, "texts": []}
            for t in texts:
                if t not in by_id[mid]["texts"]:
                    by_id[mid]["texts"].append(t)
        elif texts:
            anon.append({"model": model, "texts": texts,
                         "ts": d.get("timestamp")})
    out = []
    for mid in order:
        e = by_id[mid]
        if not e["texts"]:
            continue
        ts = first_ts.get(mid) or ""
        out.append({
            "model": public_model(e["model"]),
            "phase": "message",
            "role": "assistant",
            "text": "\n\n".join(e["texts"]).strip(),
            "timestamp": ts[:19] + "Z" if ts else None,
        })
    for e in anon:
        ts = e["ts"] or ""
        out.append({
            "model": public_model(e["model"]),
            "phase": "message",
            "role": "assistant",
            "text": "\n\n".join(e["texts"]).strip(),
            "timestamp": ts[:19] + "Z" if ts else None,
        })
    return out


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

# Session ids that may legitimately appear in assistant prose (references to
# local Claude Code sessions).  Redacted to "[private session id]".
_HEX8 = r"[0-9a-f]{8}"
_UUID = _HEX8 + r"(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"

# A "path chunk": no spaces, no quotes/backticks, no closing delimiters that
# usually end a path in prose; an optional trailing :LINE is absorbed.
_CHUNK = r"[^\s'\"`\)\]\},:;]*(?::\d+)?"

# machine-local paths -> [local path]
LOCAL_PATH_PATTERNS = [
    re.compile(r"/(?:Users|home)/" + _CHUNK),
    re.compile(r"~/" + _CHUNK),
]
# scratch/temp locations -> [private compute path]
COMPUTE_PATH_PATTERNS = [
    re.compile(r"/private/tmp/" + _CHUNK),
    re.compile(r"/var/folders/" + _CHUNK),
    re.compile(r"(?<![\w.])/tmp(?:/" + _CHUNK + r")?"),
]
# local servers
LOCAL_SERVICE_RE = re.compile(r"https?://localhost(?::\d+)?[^\s'\"`\)\]\}*]*")
LOCAL_HOST_RE = re.compile(r"\blocalhost\b")

# hardware-capacity phrases such as "10 core" (also false-positives like
# "Lemma 9.2 core", reproduced deliberately for consistency with gq2's
# published corpus)
CAPACITY_RE = re.compile(r"\b\d+(?:\.\d+)?\s+core\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

BASE_KEEP_EMAILS = {"git@github.com", "noreply@anthropic.com"}

# Instance-editorial state, set by configure() from the records config.
KEEP_EMAILS = set(BASE_KEEP_EMAILS)
USER_ECHO_REPLACEMENTS = []      # [(verbatim, paraphrase)]
PRIVATE_NAME_REPLACEMENTS = []   # [(compiled pattern, replacement)]
AUDIT_EXTRA_PATTERNS = []        # [(label, compiled pattern)]


def configure(sanitize_cfg):
    """Install the instance's editorial rules (records config "sanitize")."""
    global KEEP_EMAILS, USER_ECHO_REPLACEMENTS
    global PRIVATE_NAME_REPLACEMENTS, AUDIT_EXTRA_PATTERNS
    cfg = sanitize_cfg or {}
    KEEP_EMAILS = BASE_KEEP_EMAILS | set(cfg.get("keep_emails", []))
    USER_ECHO_REPLACEMENTS = [tuple(pair) for pair
                              in cfg.get("user_echo_replacements", [])]
    PRIVATE_NAME_REPLACEMENTS = [(re.compile(pat), rep) for pat, rep
                                 in cfg.get("private_name_replacements", [])]
    AUDIT_EXTRA_PATTERNS = [(label, re.compile(pat)) for label, pat
                            in cfg.get("audit_extra_patterns", [])]


def redact(text, session_ids=()):
    """Apply the published redaction policy to one message text."""
    text = LOCAL_SERVICE_RE.sub("[private local service]", text)
    text = LOCAL_HOST_RE.sub("[private local host]", text)
    for pat in LOCAL_PATH_PATTERNS:
        text = pat.sub("[local path]", text)
    for pat in COMPUTE_PATH_PATTERNS:
        text = pat.sub("[private compute path]", text)
    # collapse doubled redactions like "[local path]/[local path]"
    text = re.sub(r"(\[local path\][/\\]?)+", "[local path]", text)
    text = re.sub(r"(\[private compute path\][/\\]?)+", "[private compute path]", text)
    for sid in session_ids:
        if sid:
            text = text.replace(sid, "[private session id]")
    text = CAPACITY_RE.sub("[private capacity]", text)
    for old, new in USER_ECHO_REPLACEMENTS:
        text = text.replace(old, new)
    for pat, new in PRIVATE_NAME_REPLACEMENTS:
        text = pat.sub(new, text)

    def email_sub(m):
        return m.group(0) if m.group(0) in KEEP_EMAILS else "[redacted-email]"
    text = EMAIL_RE.sub(email_sub, text)
    return text


BASE_AUDIT_PATTERNS = [
    ("possible secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*\S{8,}")),
    ("bearer token", re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}")),
    ("anthropic key", re.compile(r"sk-ant-[A-Za-z0-9-]{10,}")),
    ("github token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("aws key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("email", EMAIL_RE),
    ("home path", re.compile(r"/(?:Users|home)/\w+")),
    ("tilde path", re.compile(r"~/")),
    ("ip address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("ssh host", re.compile(r"(?i)\bssh\s+\w+@")),
]


def audit_text(text):
    """Return a list of (label, excerpt) findings for human review."""
    findings = []
    for label, pat in AUDIT_EXTRA_PATTERNS + BASE_AUDIT_PATTERNS:
        for m in pat.finditer(text):
            frag = m.group(0)
            if label == "email" and frag in KEEP_EMAILS:
                continue
            if label == "email" and frag == "[redacted-email]":
                continue
            findings.append((label, text[max(0, m.start() - 40):m.end() + 40]))
    return findings
