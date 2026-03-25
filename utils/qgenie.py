"""
QGenie AI prediction helper for IPL Fantasy 2026.
Loads prompt config from data/prompt.json and calls the QGenie LLM API.
"""

import json
import os
import re
import streamlit as st
from qgenie import QGenieClient


PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prompt.json")


def _load_prompt_config() -> dict:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_client() -> tuple:
    """Returns (QGenieClient, model_name)"""
    api_key = st.secrets.get("QGENIE_API_KEY", "")
    endpoint = st.secrets.get("QGENIE_ENDPOINT", "https://qgenie-chat.qualcomm.com")
    model = st.secrets.get("QGENIE_MODEL", "gpt-oss-120b")
    if not api_key:
        raise ValueError("QGENIE_API_KEY not found in .streamlit/secrets.toml")
    return QGenieClient(endpoint=endpoint, api_key=api_key), model


def get_ai_prediction(team1: str, team2: str, venue: str, city: str, match_date: str, match_time: str) -> dict:
    """
    Call QGenie LLM and return a structured prediction dict:
    {
        "predicted_winner": str,
        "win_probability": str,
        "headline": str,
        "factors": [{"title": str, "detail": str}, ...]
    }
    Returns None on error, with an "error" key.
    """
    try:
        config = _load_prompt_config()
        client, model = _get_client()

        user_message = config["user_template"].format(
            team1=team1,
            team2=team2,
            venue=venue,
            city=city,
            match_date=match_date,
            match_time=match_time,
        )

        response = client.chat(
            messages=[
                {"role": "system", "content": config["system"]},
                {"role": "user", "content": user_message},
            ],
            max_tokens=config.get("max_tokens", 2000),
            model=model,
        )

        raw_content = response.choices[0].message.content.strip()

        # Strip <think>...</think> reasoning block if present
        raw_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()

        # Strip markdown code fences if present
        raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
        raw_content = re.sub(r"\s*```$", "", raw_content.strip())
        raw_content = raw_content.strip()

        # Try direct parse first
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            pass

        # Fallback: extract the outermost {...} block
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = raw_content[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # Last resort: return error with raw content for debugging
        return {"error": f"Could not parse LLM response as JSON", "raw": raw_content[:500]}

    except json.JSONDecodeError as e:
        return {"error": f"LLM returned non-JSON response: {e}", "raw": raw_content[:500]}
    except Exception as e:
        return {"error": str(e)}
