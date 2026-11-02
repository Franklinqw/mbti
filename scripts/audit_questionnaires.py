"""审计当前全部题库：仅生成报告数据，不修改题目、计分或数据库。"""
import csv
import json
import sys
from collections import Counter
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.question_service import SUPPORTED_MODES as ALL_MODES
# 本脚本保留2026-10-25四套旧题库审计范围；新五级题库另由test_rating_modes检查。
SUPPORTED_MODES = {key: ALL_MODES[key] for key in ('simple','full','pdp','mental_age')}
from services.result_service import result_service
from services.scoring_service import scoring_service
from models.questions import DIMENSION_LETTERS
from models.pdp_questions import PDP_SIDES
from models.mental_age_questions import (AGE_CLUSTERS, AGE_MIN, AGE_MAX,
                                         MENTAL_AGE_SCORE_MIN, MENTAL_AGE_SCORE_MAX,
                                         band_for_age)


def answers(bank, options):
    return [{'questionIndex': q.index, 'optionKey': o.key} for q, o in zip(bank, options)]


def audit():
    overview = {}
    for mode, bank in SUPPORTED_MODES.items():
        assert [q.index for q in bank] == list(range(1, len(bank) + 1)), mode
        for q in bank:
            assert isinstance(q.text, str) and q.text.strip(), (mode, q.index)
            assert len(q.options) == 2 and {o.key for o in q.options} == {'A', 'B'}, (mode, q.index)
            assert all(isinstance(o.text, str) and o.text.strip() for o in q.options)
            assert len({o.text for o in q.options}) == 2
            serialized = q.to_dict()
            assert len(serialized['options']) == 2
            assert [o['text'] for o in serialized['options']] == [o.text for o in q.options]
            for option in q.options:
                assert option.dimension == q.dimension
                if mode in ('simple', 'full'):
                    assert option.side in DIMENSION_LETTERS[q.dimension]
                elif mode == 'pdp':
                    assert option.side in PDP_SIDES
                else:
                    assert option.side in AGE_CLUSTERS and 1 <= option.score <= 5
                # 每个选项都走一次完整报告生成，验证不存在选后无法计分的选项。
                chosen = [item.options[0] for item in bank]
                chosen[q.index - 1] = option
                data = answers(bank, chosen)
                report = result_service.build_result_detail(data, mode)
                assert all(report[key] for key in ('mbtiType', 'traits', 'strengths', 'weaknesses', 'careers'))
                if mode in ('simple', 'full'):
                    tally = Counter(o.side for o in chosen)
                    expected = ''.join(l if tally[l] >= tally[r] else r for l, r in DIMENSION_LETTERS.values())
                    assert report['mbtiType'] == expected
                elif mode == 'pdp':
                    tally = Counter(o.side for o in chosen)
                    assert sum(d['score'] for d in report['dimensions'].values()) == len(bank)
                else:
                    score = sum(o.score for o in chosen)
                    expected = AGE_MIN + round((score - MENTAL_AGE_SCORE_MIN) * (AGE_MAX - AGE_MIN) / (MENTAL_AGE_SCORE_MAX - MENTAL_AGE_SCORE_MIN))
                    assert report['mentalAge'] == expected
        overview[mode] = {'questions': len(bank), 'options': sum(len(q.options) for q in bank),
                          'dimensions': dict(Counter(q.dimension for q in bank)),
                          'option_side_counts': dict(Counter(o.side for q in bank for o in q.options)),
                          'A_side_counts': dict(Counter(q.options[0].side for q in bank)),
                          'B_side_counts': dict(Counter(q.options[1].side for q in bank)),
                          'duplicate_exact_stems': [text for text, n in Counter(q.text for q in bank).items() if n > 1]}

    # 精确聚合 PDP 全部 2^20 个答案序列，按最终五维票数合并；保留代表序列验证服务。
    states = {(0,) * 5: (1, ())}
    for q in SUPPORTED_MODES['pdp']:
        following = {}
        for vector, (count, path) in states.items():
            for o in q.options:
                changed = list(vector)
                changed[PDP_SIDES.index(o.side)] += 1
                vector2 = tuple(changed)
                old_count, old_path = following.get(vector2, (0, path + (o,)))
                following[vector2] = (old_count + count, old_path)
        states = following
    outcomes, ties = Counter(), 0
    for vector, (count, path) in states.items():
        best = max(vector)
        winner = PDP_SIDES[vector.index(best)]
        assert scoring_service.calculate_pdp_type(answers(SUPPORTED_MODES['pdp'], path)) == winner
        outcomes[winner] += count
        if vector.count(best) > 1:
            ties += count
    assert sum(outcomes.values()) == 2 ** 20
    assert set(outcomes) == set(PDP_SIDES)
    overview['pdp']['exact_analysis'] = {'answer_patterns': 2 ** 20, 'distinct_score_vectors': len(states),
        'tied_top_patterns': ties, 'tie_percent': round(ties / 2 ** 20 * 100, 4),
        'winners_under_uniform_random_answers': dict(outcomes),
        'pair_frequencies': {' / '.join(pair): n for pair, n in Counter(tuple(sorted(o.side for o in q.options)) for q in SUPPORTED_MODES['pdp']).items()}}

    ages, bands, rounding, score_paths = Counter(), Counter(), Counter(), {}
    bank = SUPPORTED_MODES['mental_age']
    for chosen in product(*(q.options for q in bank)):
        raw = sum(o.score for o in chosen)
        age = AGE_MIN + round((raw - MENTAL_AGE_SCORE_MIN) * (AGE_MAX - AGE_MIN) / (MENTAL_AGE_SCORE_MAX - MENTAL_AGE_SCORE_MIN))
        ages[age] += 1
        bands[band_for_age(age).nickname] += 1
        cluster_counts = Counter(o.side for o in chosen)
        rounding[sum(round(cluster_counts[c] / len(bank) * 100) for c in AGE_CLUSTERS)] += 1
        score_paths.setdefault(raw, chosen)
    for raw, chosen in score_paths.items():
        expected = AGE_MIN + round((raw - MENTAL_AGE_SCORE_MIN) * (AGE_MAX - AGE_MIN) / (MENTAL_AGE_SCORE_MAX - MENTAL_AGE_SCORE_MIN))
        assert scoring_service.calculate_mental_age(answers(bank, chosen)) == expected
    overview['mental_age']['exact_analysis'] = {'answer_patterns': 2 ** 15,
        'raw_score_range': [min(score_paths), max(score_paths)],
        'reachable_ages': sorted(ages), 'band_counts_under_uniform_random_answers': dict(bands),
        'displayed_percentage_totals': dict(rounding),
        'equal_score_question_ids': [q.index for q in bank if len({o.score for o in q.options}) == 1]}
    return overview


def main():
    result = audit()
    folder = ROOT / 'reports'
    folder.mkdir(exist_ok=True)
    (folder / 'questionnaire-audit-data.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    with (folder / 'questionnaire-options.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(['测试模式', '原始题号', '维度', '题干', '选项', '选项内容', '计分侧', '分值'])
        for mode, bank in SUPPORTED_MODES.items():
            for q in bank:
                for o in q.options:
                    writer.writerow([mode, q.index, q.dimension, q.text, o.key, o.text, o.side, o.score])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
