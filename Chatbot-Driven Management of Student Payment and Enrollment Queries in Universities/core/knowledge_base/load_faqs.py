import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from knowledge_base.models import FAQ

count = 0

with open(os.path.join(BASE_DIR, "faq_aligned.csv"), encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        FAQ.objects.create(
            question=row["question"].strip(),
            answer=row["answer"].strip(),
            category=row["category"].strip()
        )
        count += 1

print(f"{count} FAQs imported successfully.")
