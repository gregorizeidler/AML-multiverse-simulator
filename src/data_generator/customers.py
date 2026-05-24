from __future__ import annotations

import numpy as np
import pandas as pd
from faker import Faker

RISK_LEVELS = ["low", "medium", "high"]
RISK_WEIGHTS = [0.70, 0.22, 0.08]

COUNTRIES = {
    "domestic": ["US", "US", "US", "US", "US", "US", "US", "CA", "GB"],
    "high_risk": ["NG", "PK", "VE", "IR", "KP", "MM", "BY", "RU"],
}

OCCUPATIONS = [
    "Software Engineer", "Nurse", "Teacher", "Accountant", "Sales Rep",
    "Restaurant Owner", "Freelancer", "Retail Worker", "Doctor", "Lawyer",
    "Real Estate Agent", "Truck Driver", "Consultant", "Manager", "Student",
]


def generate_customers(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    risk_levels = rng.choice(RISK_LEVELS, size=n, p=RISK_WEIGHTS)
    ages = rng.integers(18, 80, size=n)

    countries = []
    for risk in risk_levels:
        if risk == "high" and rng.random() < 0.5:
            countries.append(rng.choice(COUNTRIES["high_risk"]))
        else:
            countries.append(rng.choice(COUNTRIES["domestic"]))

    income_base = rng.choice(
        [25_000, 45_000, 75_000, 120_000, 200_000, 500_000],
        size=n,
        p=[0.15, 0.30, 0.30, 0.15, 0.07, 0.03],
    )
    income = income_base * rng.uniform(0.8, 1.2, size=n)

    customers = pd.DataFrame(
        {
            "customer_id": [f"C{i:06d}" for i in range(n)],
            "name": [fake.name() for _ in range(n)],
            "age": ages,
            "country": countries,
            "occupation": rng.choice(OCCUPATIONS, size=n),
            "annual_income": income.astype(int),
            "risk_level": risk_levels,
            "is_pep": (risk_levels == "high") & (rng.random(n) < 0.15),
            "created_at": pd.to_datetime(
                rng.integers(
                    pd.Timestamp("2018-01-01").value,
                    pd.Timestamp("2024-01-01").value,
                    size=n,
                )
            ),
        }
    )
    return customers
