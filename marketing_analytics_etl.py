#!/usr/bin/env python3
"""
zoozoo.kr 마케팅 분석 ETL — GA4 Data API, Search Console API, Clarity Data
Export API에서 데이터를 모아 website/data/analytics.json에 기록한다.
GitHub Actions에서 매일 1회 실행된다. 세 플랫폼 중 하나가 실패해도
나머지는 정상적으로 기록되도록 각각 독립적으로 처리한다.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

ROOT = Path(__file__).parent
OUT = ROOT / 'website' / 'data' / 'analytics.json'

KST = timezone(timedelta(hours=9))

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly',
]


def load_existing():
    if OUT.exists():
        return json.loads(OUT.read_text('utf-8'))
    return {
        'ga4': {'daily': [], 'sources': [], 'topPages': [], 'newVsReturning': {'new': 0, 'returning': 0}},
        'gsc': {'top_queries': []},
        'clarity': {'history': [], 'devices': [], 'browsers': [], 'uxSignals': {}},
        'errors': {},
    }


def google_credentials():
    info = json.loads(os.environ['GA4_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(info, scopes=GOOGLE_SCOPES)
    creds.refresh(GoogleAuthRequest())
    return creds


def fetch_ga4(creds, property_id):
    headers = {'Authorization': f'Bearer {creds.token}', 'Content-Type': 'application/json'}
    base = f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport'

    daily_body = {
        'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
        'dimensions': [{'name': 'date'}],
        'metrics': [{'name': 'activeUsers'}],
        'orderBys': [{'dimension': {'dimensionName': 'date'}}],
    }
    daily_res = requests.post(base, headers=headers, json=daily_body, timeout=30)
    daily_res.raise_for_status()
    daily_rows = daily_res.json().get('rows', [])
    daily = [
        {
            'date': f"{r['dimensionValues'][0]['value'][0:4]}-{r['dimensionValues'][0]['value'][4:6]}-{r['dimensionValues'][0]['value'][6:8]}",
            'activeUsers': int(r['metricValues'][0]['value']),
        }
        for r in daily_rows
    ]

    sources_body = {
        'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
        'dimensions': [{'name': 'sessionSource'}],
        'metrics': [{'name': 'sessions'}],
        'orderBys': [{'metric': {'metricName': 'sessions'}, 'desc': True}],
        'limit': 5,
    }
    sources_res = requests.post(base, headers=headers, json=sources_body, timeout=30)
    sources_res.raise_for_status()
    sources_rows = sources_res.json().get('rows', [])
    sources = [
        {'source': r['dimensionValues'][0]['value'], 'sessions': int(r['metricValues'][0]['value'])}
        for r in sources_rows
    ]

    pages_body = {
        'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
        'dimensions': [{'name': 'pagePath'}],
        'metrics': [{'name': 'screenPageViews'}],
        'orderBys': [{'metric': {'metricName': 'screenPageViews'}, 'desc': True}],
        'limit': 5,
    }
    pages_res = requests.post(base, headers=headers, json=pages_body, timeout=30)
    pages_res.raise_for_status()
    pages_rows = pages_res.json().get('rows', [])
    top_pages = [
        {'path': r['dimensionValues'][0]['value'], 'views': int(r['metricValues'][0]['value'])}
        for r in pages_rows
    ]

    new_vs_returning_body = {
        'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
        'dimensions': [{'name': 'newVsReturning'}],
        'metrics': [{'name': 'activeUsers'}],
    }
    nvr_res = requests.post(base, headers=headers, json=new_vs_returning_body, timeout=30)
    nvr_res.raise_for_status()
    nvr_rows = nvr_res.json().get('rows', [])
    new_vs_returning = {'new': 0, 'returning': 0}
    for r in nvr_rows:
        key = r['dimensionValues'][0]['value']  # 'new' | 'returning' | '(not set)'
        if key in new_vs_returning:
            new_vs_returning[key] = int(r['metricValues'][0]['value'])

    return {'daily': daily, 'sources': sources, 'topPages': top_pages, 'newVsReturning': new_vs_returning}


def fetch_gsc(creds, site_url):
    headers = {'Authorization': f'Bearer {creds.token}', 'Content-Type': 'application/json'}
    from urllib.parse import quote
    end = datetime.now(KST).date() - timedelta(days=3)  # GSC 데이터는 최근 2~3일 지연됨
    start = end - timedelta(days=28)
    url = f'https://www.googleapis.com/webmasters/v3/sites/{quote(site_url, safe="")}/searchAnalytics/query'
    body = {
        'startDate': start.isoformat(),
        'endDate': end.isoformat(),
        'dimensions': ['query'],
        'rowLimit': 10,
    }
    res = requests.post(url, headers=headers, json=body, timeout=30)
    res.raise_for_status()
    rows = res.json().get('rows', [])
    top_queries = [
        {
            'query': r['keys'][0],
            'clicks': int(r['clicks']),
            'impressions': int(r['impressions']),
            'position': round(r['position'], 1),
        }
        for r in rows
    ]
    return {'top_queries': top_queries}


def fetch_clarity(project_id, token):
    headers = {'Authorization': f'Bearer {token}'}
    url = 'https://www.clarity.ms/export-data/api/v1/project-live-insights'
    res = requests.get(url, headers=headers, params={'numOfDays': 1}, timeout=30)
    res.raise_for_status()
    metrics = res.json()

    def find_metric(name):
        for m in metrics:
            if m.get('metricName') == name:
                return m.get('information', [{}])[0]
        return {}

    def find_breakdown(name, limit=5):
        for m in metrics:
            if m.get('metricName') == name:
                rows = m.get('information', [])
                return [
                    {'name': row.get('name') or '(알 수 없음)', 'sessions': int(row.get('sessionsCount', 0) or 0)}
                    for row in rows[:limit]
                ]
        return []

    traffic = find_metric('Traffic')
    scroll = find_metric('ScrollDepth')
    engagement = find_metric('EngagementTime')

    sessions = int(traffic.get('totalSessionCount', 0) or 0)
    # EngagementTime은 평균이 아니라 세션 합산 초(activeTime)로 내려오므로 세션 수로 나눠 평균을 구한다.
    avg_engagement = (engagement.get('activeTime', 0) or 0) / sessions if sessions else 0.0

    snapshot = {
        'date': datetime.now(KST).date().isoformat(),
        'sessions': sessions,
        'scrollDepth': float(scroll.get('averageScrollDepth', 0) or 0),
        'engagementTime': round(float(avg_engagement), 1),
    }

    devices = find_breakdown('Device')
    browsers = find_breakdown('Browser')

    # sessionsWithMetricPercentage: 해당 UX 문제가 한 번이라도 발생한 세션의 비율(%)
    ux_signals = {
        'rageClick': float(find_metric('RageClickCount').get('sessionsWithMetricPercentage', 0) or 0),
        'deadClick': float(find_metric('DeadClickCount').get('sessionsWithMetricPercentage', 0) or 0),
        'quickback': float(find_metric('QuickbackClick').get('sessionsWithMetricPercentage', 0) or 0),
        'excessiveScroll': float(find_metric('ExcessiveScroll').get('sessionsWithMetricPercentage', 0) or 0),
        'scriptError': float(find_metric('ScriptErrorCount').get('sessionsWithMetricPercentage', 0) or 0),
    }

    return snapshot, devices, browsers, ux_signals


def merge_clarity_history(existing_history, today_snapshot):
    history = [h for h in existing_history if h['date'] != today_snapshot['date']]
    history.append(today_snapshot)
    history.sort(key=lambda h: h['date'])
    return history[-30:]


def main():
    data = load_existing()
    errors = {}

    try:
        creds = google_credentials()
    except Exception as e:
        errors['google_auth'] = str(e)
        creds = None

    if creds:
        try:
            data['ga4'] = fetch_ga4(creds, os.environ['GA4_PROPERTY_ID'])
        except Exception as e:
            errors['ga4'] = str(e)

        try:
            data['gsc'] = fetch_gsc(creds, os.environ['GSC_SITE_URL'])
        except Exception as e:
            errors['gsc'] = str(e)

    try:
        snapshot, devices, browsers, ux_signals = fetch_clarity(
            os.environ['CLARITY_PROJECT_ID'], os.environ['CLARITY_API_TOKEN']
        )
        data.setdefault('clarity', {'history': []})
        data['clarity']['history'] = merge_clarity_history(data['clarity'].get('history', []), snapshot)
        data['clarity']['devices'] = devices
        data['clarity']['browsers'] = browsers
        data['clarity']['uxSignals'] = ux_signals
        data['clarity'].pop('_debug_raw', None)
    except Exception as e:
        errors['clarity'] = str(e)

    data['errors'] = errors
    data['updated_at'] = datetime.now(KST).isoformat()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    print(f'analytics.json 갱신 완료 → {OUT} (오류: {errors or "없음"})')


if __name__ == '__main__':
    main()
