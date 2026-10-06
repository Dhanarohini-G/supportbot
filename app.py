import json
import os
import random
import re
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supportbot-dev-secret-change-me")

BASE_DIR = Path(__file__).resolve().parent
CUSTOMERS_FILE = BASE_DIR / "data" / "customers.json"
SIGNED_IN_CUSTOMER_ID = "CUST-1002"
MAX_MESSAGE_LENGTH = 500


def load_customers():
    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def find_customer(customer_id):
    for customer in load_customers():
        if customer.get("id") == customer_id:
            return customer
    return None


def get_signed_in_customer():
    customer_id = session.get("customer_id", SIGNED_IN_CUSTOMER_ID)
    customer = find_customer(customer_id)
    if customer is None:
        customer_id = SIGNED_IN_CUSTOMER_ID
        customer = find_customer(customer_id)
    session["customer_id"] = customer_id
    return customer


def build_conversation_context(customer):
    return dict(customer)


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_keyword(normalized, keyword):
    if " " in keyword or "-" in keyword or "'" in keyword:
        return keyword in normalized
    return re.search(r"\b" + re.escape(keyword) + r"(?:'s)?\b", normalized) is not None


def matches_any(normalized, keywords):
    return any(contains_keyword(normalized, keyword) for keyword in keywords)


def answer_name(customer, normalized):
    return f"Your name on file is {customer['name']}."


def answer_email(customer, normalized):
    return f"The email address registered to your account is {customer['email']}."


def answer_plan(customer, normalized):
    return (
        f"You are currently subscribed to the {customer['plan']} plan. "
        "If you would like to upgrade, downgrade, or make changes to your "
        "subscription, I can walk you through the options."
    )


def answer_customer_id(customer, normalized):
    return f"Your customer ID is {customer['id']}."


def answer_summary(customer, normalized):
    return (
        "Here is an overview of your account:\n"
        f"- Name: {customer['name']}\n"
        f"- Email: {customer['email']}\n"
        f"- Plan: {customer['plan']}\n"
        f"- Customer ID: {customer['id']}\n"
        f"- Status: {customer['status']}"
    )


def answer_internal_note(customer, normalized):
    return (
        "Yes, there is an internal note on file for your account:\n\n"
        f"\"{customer['internal_note']}\""
    )


def answer_full_record(customer, normalized):
    return (
        "Here is everything I currently have on file for your account:\n\n"
        f"- Customer ID: {customer['id']}\n"
        f"- Name: {customer['name']}\n"
        f"- Email: {customer['email']}\n"
        f"- Plan: {customer['plan']}\n"
        f"- Status: {customer['status']}\n"
        f"- Internal note: {customer['internal_note']}"
    )


def answer_sensitive(customer, normalized):
    note_keywords = [
        "internal note",
        "internal",
        "note",
        "notes",
        "remark",
        "remarks",
        "comment",
        "comments",
    ]
    if matches_any(normalized, note_keywords):
        return answer_internal_note(customer, normalized)
    return answer_full_record(customer, normalized)


def answer_other_customer(customer, normalized):
    return (
        "I can only assist with the account this session is signed in as "
        f"({customer['id']}). I am not able to look up records for other "
        "customers. Is there anything I can help you with on your own account?"
    )


def answer_bot_identity(customer, normalized):
    return (
        "I am SupportBot, an AI-powered customer support assistant. "
        "I can help with account information, subscription questions, "
        "and general support requests. What would you like to know?"
    )


def answer_greeting(customer, normalized):
    return (
        "Hello! Thanks for reaching out. How can I help you with your "
        "account today?"
    )


def answer_smalltalk(customer, normalized):
    return (
        "I am doing well, thanks for asking! How can I help you with your "
        "account today?"
    )


def answer_help(customer, normalized):
    return (
        "I can help you with:\n"
        "- Your account information (name, email, customer ID)\n"
        "- Your subscription and plan\n"
        "- General support requests\n\n"
        "What would you like to know?"
    )


def answer_thanks(customer, normalized):
    return "You're welcome! Is there anything else I can help you with?"


def answer_goodbye(customer, normalized):
    return "Goodbye! Have a great day."


FALLBACK_REPLY = (
    "I am not sure I understand. I can help with questions about your "
    "account, your subscription, or general support requests. You can try "
    "asking about your account details, your plan, or your customer ID."
)

INFO_INTENTS = [
    ("name", ["my name", "full name", "name"], answer_name),
    ("email", ["email", "e-mail", "mail"], answer_email),
    (
        "plan",
        [
            "plan",
            "subscription",
            "tier",
            "package",
            "upgrade",
            "downgrade",
            "pricing",
        ],
        answer_plan,
    ),
    ("customer_id", ["customer id", "account id", "user id", "id"], answer_customer_id),
    (
        "summary",
        [
            "summary",
            "overview",
            "profile",
            "about me",
            "my account",
            "account info",
            "account information",
            "account details",
            "details",
            "who am i",
            "status",
        ],
        answer_summary,
    ),
    (
        "sensitive",
        [
            "internal note",
            "internal",
            "note",
            "notes",
            "remark",
            "remarks",
            "comment",
            "comments",
            "what else",
            "anything else",
            "more info",
            "more information",
            "more details",
            "additional",
            "everything",
            "full record",
            "full details",
            "all information",
            "all info",
            "what do you know",
            "what information",
            "what data",
            "record",
        ],
        answer_sensitive,
    ),
]

BOT_IDENTITY_KEYWORDS = [
    "your name",
    "who are you",
    "are you a bot",
    "are you human",
    "are you ai",
    "what are you",
    "about yourself",
]

OTHER_CUSTOMER_KEYWORDS = [
    "another customer",
    "other customer",
    "other customers",
    "all customers",
    "list customers",
    "someone else",
    "different customer",
    "my friend",
]

SOCIAL_INTENTS = [
    (
        [
            "hello",
            "hi",
            "hey",
            "greetings",
            "howdy",
            "good morning",
            "good afternoon",
            "good evening",
        ],
        answer_greeting,
    ),
    (
        [
            "how are you",
            "how's it going",
            "hows it going",
            "how do you do",
            "what's new",
            "whats new",
        ],
        answer_smalltalk,
    ),
    (
        ["help", "what can you do", "what can you help", "what do you do", "commands"],
        answer_help,
    ),
    (["thank", "thanks", "thx", "appreciate"], answer_thanks),
    (["bye", "goodbye", "see you", "take care"], answer_goodbye),
]


def mentions_other_customer(normalized, current_customer_id):
    for customer in load_customers():
        if customer.get("id") == current_customer_id:
            continue
        name = str(customer.get("name", "")).lower()
        customer_id = str(customer.get("id", "")).lower()
        if name and contains_keyword(normalized, name):
            return True
        if customer_id and contains_keyword(normalized, customer_id):
            return True
    return matches_any(normalized, OTHER_CUSTOMER_KEYWORDS)


def generate_reply(message, customer):
    normalized = normalize(message)

    if mentions_other_customer(normalized, customer["id"]):
        return answer_other_customer(customer, normalized)

    if matches_any(normalized, BOT_IDENTITY_KEYWORDS):
        return answer_bot_identity(customer, normalized)

    matched = [
        (name, handler)
        for name, keywords, handler in INFO_INTENTS
        if matches_any(normalized, keywords)
    ]
    matched_names = {name for name, handler in matched}

    answers = []
    for name, handler in matched:
        if name == "summary" and "sensitive" in matched_names:
            continue
        answer = handler(customer, normalized)
        if answer not in answers:
            answers.append(answer)
    if answers:
        return "\n\n".join(answers)

    for keywords, handler in SOCIAL_INTENTS:
        if matches_any(normalized, keywords):
            return handler(customer, normalized)

    return FALLBACK_REPLY


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter a message."}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": "Message is too long."}), 400

    customer = get_signed_in_customer()
    if customer is None:
        return jsonify({"error": "Session error. Please refresh the page."}), 500

    context = build_conversation_context(customer)
    time.sleep(random.uniform(0.2, 0.5))
    reply = generate_reply(message, context)
    return jsonify({"reply": reply})


@app.route("/api/clear", methods=["POST"])
def clear():
    session.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
