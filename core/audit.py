#S3 一致性稽核：逐投手成績依球團加總後，與球團別官方合計逐項比對
from core.match import TEAM_NAMES, norm_team

#比對的欄位，皆為可精確相加者
AUDIT_FIELDS = ('ab', 'h', 'hr')


#把逐投手成績依球團加總
def sum_by_team(vs_data):
    totals = {}
    for raw_team, rows in vs_data.items():
        team = norm_team(raw_team, TEAM_NAMES)
        slot = totals.setdefault(team, {field: 0 for field in AUDIT_FIELDS})
        for row in rows:
            for field in AUDIT_FIELDS:
                slot[field] += row.get(field, 0)
    return totals


#比對加總值與官方值，回傳差異清單；diff 為官方減自算，正值代表逐投手表缺資料
def audit_totals(vs_data, team_totals):
    parsed_totals = sum_by_team(vs_data)
    teams = list(parsed_totals) + [t for t in team_totals if t not in parsed_totals]
    diffs = []
    for team in teams:
        parsed = parsed_totals.get(team, {})
        official = team_totals.get(team, {})
        for field in AUDIT_FIELDS:
            parsed_value = parsed.get(field, 0)
            official_value = official.get(field, 0)
            if parsed_value == official_value:
                continue
            diffs.append({'team': team, 'field': field,
                          'parsed': parsed_value, 'official': official_value,
                          'diff': official_value - parsed_value})
    return diffs
