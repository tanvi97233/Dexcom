"""Deterministic, budgeted public-search query generation."""
from __future__ import annotations

from dataclasses import dataclass


DEFAULT_LOCATIONS = [
    "United States", "USA", "Canada", "Mexico", "United Kingdom", "UK", "Ireland",
    "Germany", "Netherlands", "France", "Spain", "Italy", "Switzerland", "Sweden",
    "Denmark", "Australia", "New Zealand", "India", "Japan", "Singapore", "China",
    "South Korea", "UAE", "United Arab Emirates",
]
DEFAULT_JOB_FAMILIES = [
    "Engineer", "Software Engineer", "Systems Engineer", "Quality", "Manufacturing",
    "Clinical", "Regulatory", "Scientist", "Data", "Supply Chain", "Operations",
    "Sales", "Marketing", "Finance", "Human Resources", "Program Manager", "Product Manager",
    "Business Analyst", "Manager", "Director", "Lead", "Principal",
]
HIGH_VALUE_COMBINATIONS = [
    ("United States", "Engineer"), ("United States", "Scientist"), ("United States", "Manufacturing"),
    ("Ireland", "Quality"), ("Ireland", "Manufacturing"), ("India", "Software Engineer"),
    ("India", "Systems Engineer"), ("Germany", "Quality"), ("Germany", "Regulatory"),
    ("Singapore", "Sales"), ("Japan", "Clinical"), ("Mexico", "Manufacturing"),
    ("Malaysia", "Manufacturing"), ("Switzerland", "Clinical"), ("United Kingdom", "Marketing"),
]


@dataclass(frozen=True)
class QueryMatrixGenerator:
    company: str = "Dexcom"
    locations: tuple[str, ...] = tuple(DEFAULT_LOCATIONS)
    job_families: tuple[str, ...] = tuple(DEFAULT_JOB_FAMILIES)

    def generate(self, max_queries: int = 75) -> list[str]:
        base = f'site:linkedin.com/jobs/view "{self.company}"'
        candidates = [base, f'{base} jobs', f'{base} careers', f'{base} "{self.company}, Inc."']
        candidates.extend(f'{base} "{location}"' for location in self.locations)
        candidates.extend(f'{base} "{family}"' for family in self.job_families)
        candidates.extend(f'{base} "{location}" "{family}"' for location, family in HIGH_VALUE_COMBINATIONS)
        output = []
        seen = set()
        for query in candidates:
            normalized = " ".join(query.split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                output.append(normalized)
            if len(output) >= max(1, max_queries):
                break
        return output
