"""
llm_client.py
 
설명:
  - 이 스크립트는 OpenAI ChatGPT 계열과 Google Vertex AI(Gemini) 계열 LLM에 요청을 보내고 응답을 받아오는 간단한 클라이언트입니다.
  - 최대한 단순하게 작성되어 있으며, 외부 의존성을 최소화했습니다.

사용법:
  1. OpenAI (ChatGPT) 예시:
     export OPENAI_API_KEY="sk-..."
     python llm_client.py --provider openai --model gpt-4o-mini --prompt "안녕, 잘 지내?"

  2. Google Vertex AI (Gemini) 예시:
     export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
     python llm_client.py --provider gemini --project your-gcp-project --location=us-central1 --model="gemini-1.5" --prompt "안녕, 잘 지내?"

출력:
  - JSON 형태로 원응답(raw)과 텍스트(text) 필드를 포함합니다.
"""

import os
import sys
import json
import argparse
import random
import time


try:
    # .env 파일에서 환경 변수를 로드합니다.
    # pip install python-dotenv
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv가 설치되지 않은 경우 무시합니다.

try:
    # pip install openai
    from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError, AuthenticationError, BadRequestError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    # pip install google-generativeai
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False

# OpenAI ChatGPT 호출
def call_openai(api_key: str, model: str, prompt: str,
                temperature: float = 0.7,
                as_json: bool = False,
                timeout: int = 60):
    """
    Returns: {"raw": <sdk object dict>, "text": <str>, "json": <dict or None>}
    """
    # Prefer the explicit arg; fall back to env for convenience
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing. Pass api_key or set env var.")

    client = OpenAI(api_key=key)

    system = """You are a video summarizer.
    Output JSON with keys:
    - bullets: array of 5 key insights
    - tldr: one sentence (<=25 words)
    - hooks: array of 3 short, catchy titles (<=10 words) for Shorts/Reels/TikTok
    Keep proper nouns as-is; answer in the language the summary is provided in."""

    # Basic retry on transient errors (HTTP 429/5xx)
    for attempt in range(5):
        try:
            kwargs = {
                "model": model,                 # e.g. "gpt-4o-mini" or "gpt-4o"
                "input": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_output_tokens": 1024,      # adjust for summaries
                "timeout": timeout,
            }
            if as_json:
                kwargs["response_format"] = {"type": "json_object"}

            resp = client.responses.create(**kwargs)

            # Unified text accessor
            text = getattr(resp, "output_text", "") or ""
            data = resp.model_dump()  # serialize SDK object

            out = {"raw": data, "text": text, "json": None}
            if as_json:
                try:
                    out["json"] = json.loads(text) if text else None
                except json.JSONDecodeError:
                    # Fallback: try pulling from structured outputs if present
                    out["json"] = None
            return out

        except AuthenticationError as e:
            # Don’t retry bad credentials
            raise RuntimeError(f"Auth failed (check API key/org): {getattr(e,'status_code',None)} {getattr(getattr(e,'response',None),'text',e)}") from e

        except BadRequestError as e:
            # Don’t retry invalid request (e.g., too many tokens)
            body = getattr(getattr(e, "response", None), "text", "")
            raise RuntimeError(f"Bad request: {body or str(e)}") from e

        except RateLimitError as e:
            last_err = e
            retry_after = None
            try:
                retry_after = getattr(e, "response", None).headers.get("retry-after")  # seconds
            except Exception:
                pass
            if retry_after is not None:
                sleep = float(retry_after)
            else:
                sleep = (2 ** attempt) + random.random()
            time.sleep(sleep)

        except APIStatusError as e:
            last_err = e
            code = getattr(e, "status_code", 0)
            if 500 <= code < 600:
                sleep = (2 ** attempt) + random.random()
                time.sleep(sleep)
            elif code == 429:
                # Some 429s arrive as APIStatusError
                retry_after = None
                try:
                    retry_after = getattr(e, "response", None).headers.get("retry-after")
                except Exception:
                    pass
                sleep = float(retry_after) if retry_after else (2 ** attempt) + random.random()
                time.sleep(sleep)
            else:
                body = getattr(getattr(e, "response", None), "text", "")
                raise RuntimeError(f"OpenAI API error {code}: {body or str(e)}") from e

        except APIConnectionError as e:
            last_err = e
            time.sleep((2 ** attempt) + random.random())

    # If we got here, all retries failed—surface the last error details
    msg = "OpenAI request failed after retries."
    if last_err is not None:
        sc = getattr(last_err, "status_code", None)
        body = getattr(getattr(last_err, "response", None), "text", "")
        if sc or body:
            msg += f" Last status={sc}, body={body or repr(last_err)}"
        else:
            msg += f" Last error={repr(last_err)}"
    raise RuntimeError(msg)

# Gemini(Vertex AI) 호출
def call_gemini(project, location, model, prompt, credentials_path=None):
   
    # This function now uses the google-generativeai library, which uses an API key.
    # The project, location, and credentials_path arguments are kept for command-line compatibility but are not used.
    if not VERTEXAI_AVAILABLE:
        raise RuntimeError("google-generativeai 라이브러리 설치 필요. `pip install google-generativeai`")
    
    # RECOMMENDED MODELS
    # gemini-2.5-flash: Fast and good
    # gemini-2.5-pro: Better
    # gemini-2.5-flash-lite: Lightest

    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise RuntimeError('GOOGLE_API_KEY 환경변수 필요')
    
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel(model_name=model)

    response = gemini_model.generate_content(prompt)
    text = response.text
    return {"raw": str(response), "text": text}

# 메인 함수
def main():

    # command line arguments
    parser = argparse.ArgumentParser(description="간단한 LLM 클라이언트")
    parser.add_argument('--provider', choices=['openai','gemini'], required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--project')
    parser.add_argument('--location', default='us-central1')
    parser.add_argument('--credentials-path', help="Path to Google Cloud service account JSON file. Overrides GOOGLE_APPLICATION_CREDENTIALS.")
    args = parser.parse_args()

    try:
        if args.provider == 'openai':
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError('OPENAI_API_KEY 환경변수 필요')
            out = call_openai(api_key=api_key, model=args.model, prompt=args.prompt)
        elif args.provider == 'gemini':
            out = call_gemini(args.project, args.location, args.model, args.prompt, args.credentials_path)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except RateLimitError as e:
        print(json.dumps({'error': f"OpenAI Rate Limit Exceeded: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except google_exceptions.ResourceExhausted as e:
        print(json.dumps({'error': f"Google Cloud Quota Exceeded: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({'error': f"An unexpected error occurred: {type(e).__name__}: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()