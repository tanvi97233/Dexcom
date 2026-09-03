from query_matrix import QueryMatrixGenerator


def test_matrix_contains_prioritized_dimensions():
    queries = QueryMatrixGenerator().generate(75)
    assert 'site:linkedin.com/jobs/view "Dexcom"' in queries
    assert 'site:linkedin.com/jobs/view "Dexcom" "India"' in queries
    assert 'site:linkedin.com/jobs/view "Dexcom" "Software Engineer"' in queries
    assert 'site:linkedin.com/jobs/view "Dexcom" "India" "Software Engineer"' in queries


def test_matrix_is_deterministic_unique_and_budgeted():
    generator = QueryMatrixGenerator(locations=("India", "India"), job_families=("Engineer", "Engineer"))
    first = generator.generate(6)
    assert first == generator.generate(6)
    assert len(first) == len(set(first)) <= 6
    assert all(query and "site:linkedin.com/jobs/view" in query and "Dexcom" in query for query in first)
