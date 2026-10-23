from datetime import datetime, timedelta, timezone

import pytest

# Default payout wallet for test merchants (the same wallet the payment tests expect)
MERCHANT_WALLET = "0xaff58640036e6c343e772D6B268C00FAA9265fc1"


def _give_plan(name, plan="professional", days=30, payout_wallet=MERCHANT_WALLET):
    """Make a stored user a ready merchant: an active plan, as if they had paid for it,
    and a payout wallet for their APIUSD sales."""
    import app.store as store
    users = store.load_users()
    user = next(u for u in users if u.get("name") == name)
    user["plan"] = plan
    user["plan_expires_at"] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    if payout_wallet:
        user["payout_wallet"] = payout_wallet
    store.save_users(users)


@pytest.fixture(scope="session")
def give_plan():
    return _give_plan
