# ShopSense — An Automata-Based Shopping Behaviour Pattern Analyzer

ShopSense is a beginner-friendly Streamlit college project that combines a working deterministic finite automaton (DFA) with descriptive analytics, customer clustering, and frequent-pattern mining. The bundled data is **synthetic** and all findings from it are simulated, not evidence about real customers.

## Problem and objectives

Shopping actions form sequences, but it can be difficult to explain where a session is in its journey. ShopSense demonstrates how a DFA can track browse, view, cart, checkout, purchase, and abandonment states while Python data tools summarize sessions and customer groups.

## Features

- Reproducible generator for 1,200 synthetic shopping sessions.
- Session conversion, cart and checkout abandonment, duration, order value, category revenue, device conversion, popular actions, and sequence metrics.
- Interactive DFA simulator with explanations, state history, and a transition diagram.
- Customer-level scaled KMeans clustering and cluster summaries.
- Apriori product-category co-occurrence rules with support, confidence, and lift.
- Dark Streamlit dashboard, filters, CSV upload validation, and data download.

## TOC and Data Science

A **DFA** is a finite-state machine that processes one symbol at a time. Its **alphabet** is the set of allowed symbols (shopping actions). A **state** summarizes progress so far. The **transition function** maps a current state and input symbol to exactly one next state. An **accepting state** marks a sequence of interest; ShopSense uses S4 after checkout and purchase. Valid unfinished sessions are distinct from invalid action orders, which enter the dead state SD.

**KMeans** groups customers by numeric features. ShopSense scales those features before clustering; cluster numbers are arbitrary, so compare their descriptive statistics. **Association rule mining** searches baskets for items that often occur together. Support is the fraction of baskets containing both sides, confidence is the fraction of left-side baskets also containing the right side, and lift compares that confidence with the right side's overall frequency. Association does not mean causation.

## Architecture

```text
shopsense/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── generate_data.py
│   └── shopping_data.csv       # generated on first run
├── modules/
│   ├── __init__.py
│   ├── automata.py
│   ├── analytics.py
│   └── pattern_mining.py
└── tests/
    └── test_automata.py
```

The Streamlit UI calls small Python modules: `automata.py` models event order, `analytics.py` calculates metrics and segments customers, `pattern_mining.py` runs Apriori, and `data/generate_data.py` creates fixed-seed demo records.

## Install and run

Use Python 3.10 or newer. Activate your virtual environment, then install dependencies if needed:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

The app creates `data/shopping_data.csv` on its first launch if it is missing. Use **Regenerate synthetic dataset** in the sidebar to create the same seeded example data again. To run unit tests:

```bash
python -m unittest discover -s tests -v
```

## Dataset

Each row is one synthetic session and includes session/customer IDs, timestamp, device, product category and (for completed transactions) a synthetic category basket, ordered JSON action sequence, viewed/added counts, checkout/purchase flags, duration, and purchase amount. The generator uses a fixed random seed. Do not interpret the generated figures as actual customer behaviour.

## Example use cases

1. Choose **Automata Simulator** and load “Successful purchase” to inspect each transition.
2. Filter **Shopping Behaviour** by device/category/date and compare session outcomes.
3. Run **Customer Segments** and compare feature averages across clusters.
4. Lower the support threshold in **Product Patterns** to inspect more simulated co-occurrences.
5. Upload a CSV in **Data Explorer**; missing required fields are reported instead of being accepted silently.

## Limitations and future work

The data is simulated, product patterns use category-level baskets, and the automaton simplifies real checkout/payment flows. KMeans results depend on selected cluster count and feature design. Future work could include item-level real data with appropriate consent, payment retries, returns, time trends, and cluster stability checks.

## Viva questions and answers

**What is a DFA?** A machine with a finite number of states and one deterministic next state for each state/input pair.

**Why is an incomplete session not invalid?** A customer can stop after browsing or adding to cart; that is a valid prefix of a shopping journey, even though it is not an accepted purchase sequence.

**What does the dead state mean?** The event order could not follow a defined shopping workflow transition, such as purchasing before checkout.

**Why scale KMeans features?** KMeans uses distances; scaling prevents large-valued fields such as duration from overwhelming smaller frequency fields.

**What does lift greater than one mean?** The two sides co-occur more than expected from the consequent's overall frequency. It does not show causation.

**Why use a fixed random seed?** It makes the demo dataset and clustering reproducible for explanation and review.
