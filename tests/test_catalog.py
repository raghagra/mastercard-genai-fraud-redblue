from src.knowledge.load_attack_catalog import load_attack_cards, summarize_catalog
from src.knowledge.validate_attack_cards import validate_attack_catalog


def test_attack_catalog_validates() -> None:
    result = validate_attack_catalog()

    assert result.valid is True
    assert result.checked_count == 25
    assert not result.errors


def test_attack_catalog_covers_five_buckets() -> None:
    cards = load_attack_cards()
    summary = summarize_catalog(cards)

    assert summary["total_cards"] == 25
    assert summary["buckets"] == {
        "credential_based_fraud": 5,
        "identity_onboarding_fraud": 5,
        "merchant_ecosystem_abuse": 5,
        "post_transaction_abuse": 5,
        "social_engineering_payment_fraud": 5,
    }

