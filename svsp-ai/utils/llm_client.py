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
import time

import requests

try:
    # .env 파일에서 환경 변수를 로드합니다.
    # pip install python-dotenv
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # python-dotenv가 설치되지 않은 경우 무시합니다.

try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

# OpenAI ChatGPT 호출
def call_openai(api_key, model, prompt, max_retries=5, initial_delay=1):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            text = ''.join(choice['message'].get('content','') for choice in result.get('choices',[]))
            return {"raw": result, "text": text}
        except requests.exceptions.HTTPError as e:
            # 429 is the status code for "Too Many Requests" (rate limiting)
            if e.response.status_code == 429 and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"Rate limit exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(delay)
            else:
                raise # Re-raise the last exception if all retries fail or it's not a 429 error

# Gemini(Vertex AI) 호출
def call_gemini(project, location, model, prompt, credentials_path=None, max_retries=5, initial_delay=1):
    if not GOOGLE_AUTH_AVAILABLE:
        raise RuntimeError("google-auth 라이브러리 설치 필요")

    model_path = f"projects/{project}/locations/{location}/models/{model}"
    endpoint = f"https://{location}-aiplatform.googleapis.com/v1/{model_path}:predict"

    creds_path = credentials_path or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=['https://www.googleapis.com/auth/cloud-platform'])
    creds.refresh(Request())

    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
    payload = {"instances": [{"content": prompt}], "parameters": {"temperature":0.0, "maxOutputTokens":1024}}

    for attempt in range(max_retries):
        try:
            resp = requests.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data.get('predictions',[{}])[0].get('content','')
            return {"raw": data, "text": text}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"Rate limit exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(delay)
            else:
                raise

# 메인 함수
def main():

    # command line arguments
    parser = argparse.ArgumentParser(description="간단한 LLM 클라이언트")
    parser.add_argument('--provider', choices=['openai','gemini'], required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--project')
    parser.add_argument('--location', default='us-central1')
    parser.add_argument('--credentials-path')
    args = parser.parse_args()

    try:
        if args.provider == 'openai':
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError('OPENAI_API_KEY 환경변수 필요')
            out = call_openai(api_key=api_key, model=args.model, prompt=args.prompt)
        elif args.provider == 'gemini':
            if not args.project:
                raise RuntimeError('--project 필요')
            out = call_gemini(args.project, args.location, args.model, args.prompt, args.credentials_path)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()