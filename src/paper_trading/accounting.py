"""Exact Decimal spot-token accounting for WP173 paper sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal

from .models import (
    PaperFill,
    PaperOrder,
    PaperTradingError,
    decimal_text,
    decimal_value,
)


@dataclass(frozen=True)
class PaperPosition:
    market_id: str
    asset_id: str
    quantity: str
    cost_basis: str
    realized_pnl: str


@dataclass(frozen=True)
class PaperAccount:
    initial_cash: str
    cash: str
    reserved_cash: str
    positions: tuple[PaperPosition, ...]
    reserved_positions: tuple[tuple[str, str], ...]
    realized_pnl: str
    daily_realized_pnl: tuple[tuple[str, str], ...] = ()


def new_account(initial_cash: str) -> PaperAccount:
    value = decimal_value(initial_cash, nonnegative=True)
    if value <= 0:
        raise PaperTradingError("ACCOUNT_INVALID")
    text = decimal_text(value)
    return PaperAccount(text, text, "0", (), (), "0", ())


def utc_day_key(event_time_ns: int) -> str:
    if not isinstance(event_time_ns, int) or isinstance(event_time_ns, bool) or event_time_ns < 0:
        raise PaperTradingError("ACCOUNT_INVALID")
    return str(event_time_ns // 86_400_000_000_000)


def position_map(account: PaperAccount) -> dict[str, PaperPosition]:
    return {item.asset_id: item for item in account.positions}


def reservation_map(account: PaperAccount) -> dict[str, Decimal]:
    return {asset: Decimal(quantity) for asset, quantity in account.reserved_positions}


def free_cash(account: PaperAccount) -> Decimal:
    return Decimal(account.cash) - Decimal(account.reserved_cash)


def free_position(account: PaperAccount, asset_id: str) -> Decimal:
    position = position_map(account).get(asset_id)
    owned = Decimal(position.quantity) if position else Decimal(0)
    return owned - reservation_map(account).get(asset_id, Decimal(0))


def validate_account(account: object) -> None:
    if type(account) is not PaperAccount:
        raise PaperTradingError("ACCOUNT_INVALID")
    initial = decimal_value(account.initial_cash, nonnegative=True)
    cash = decimal_value(account.cash, nonnegative=True)
    reserved_cash = decimal_value(account.reserved_cash, nonnegative=True)
    decimal_value(account.realized_pnl)
    if initial <= 0 or reserved_cash > cash:
        raise PaperTradingError("ACCOUNT_INVALID")
    assets: set[str] = set()
    for position in account.positions:
        if (
            position.asset_id in assets
            or decimal_value(position.quantity, nonnegative=True) <= 0
            or decimal_value(position.cost_basis, nonnegative=True) < 0
        ):
            raise PaperTradingError("ACCOUNT_INVALID")
        decimal_value(position.realized_pnl)
        assets.add(position.asset_id)
    reserved_assets: set[str] = set()
    for asset_id, quantity in account.reserved_positions:
        if (
            asset_id in reserved_assets
            or decimal_value(quantity, nonnegative=True) <= 0
            or asset_id not in assets
        ):
            raise PaperTradingError("ACCOUNT_INVALID")
        reserved_assets.add(asset_id)
    days: set[str] = set()
    for day, amount in account.daily_realized_pnl:
        if not isinstance(day, str) or not day.isdigit() or day in days:
            raise PaperTradingError("ACCOUNT_INVALID")
        decimal_value(amount)
        days.add(day)
    if any(free_position(account, asset_id) < 0 for asset_id in assets):
        raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")


def reserve(account: PaperAccount, order: PaperOrder) -> PaperAccount:
    if order.side == "BUY":
        amount = Decimal(order.reserved_cash)
        if free_cash(account) < amount:
            raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
        return replace(
            account, reserved_cash=decimal_text(Decimal(account.reserved_cash) + amount)
        )
    amount = Decimal(order.reserved_quantity)
    if free_position(account, order.asset_id) < amount:
        raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
    reserved = reservation_map(account)
    reserved[order.asset_id] = reserved.get(order.asset_id, Decimal(0)) + amount
    return replace(
        account,
        reserved_positions=tuple(
            sorted(
                (asset, decimal_text(quantity))
                for asset, quantity in reserved.items()
                if quantity
            )
        ),
    )


def release(account: PaperAccount, order: PaperOrder) -> PaperAccount:
    if order.side == "BUY":
        remaining = Decimal(account.reserved_cash) - Decimal(order.reserved_cash)
        if remaining < 0:
            raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
        return replace(account, reserved_cash=decimal_text(remaining))
    reserved = reservation_map(account)
    remaining = reserved.get(order.asset_id, Decimal(0)) - Decimal(
        order.reserved_quantity
    )
    if remaining < 0:
        raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
    if remaining:
        reserved[order.asset_id] = remaining
    else:
        reserved.pop(order.asset_id, None)
    return replace(
        account,
        reserved_positions=tuple(
            sorted(
                (asset, decimal_text(quantity)) for asset, quantity in reserved.items()
            )
        ),
    )


def apply_fill(
    account: PaperAccount,
    order_before: PaperOrder,
    order_after: PaperOrder,
    fill: PaperFill,
) -> PaperAccount:
    quantity = Decimal(fill.quantity)
    notional = quantity * Decimal(fill.price)
    fee = Decimal(fill.fee)
    positions = position_map(account)
    reserved_positions = reservation_map(account)
    cash = Decimal(account.cash)
    reserved_cash = Decimal(account.reserved_cash)
    realized = Decimal(account.realized_pnl)
    daily = {day: Decimal(value) for day, value in account.daily_realized_pnl}
    if order_before.side == "BUY":
        released = Decimal(order_before.reserved_cash) - Decimal(
            order_after.reserved_cash
        )
        reserved_cash -= released
        cash -= notional + fee
        if cash < 0 or reserved_cash < 0 or cash - reserved_cash < 0:
            raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
        current = positions.get(order_before.asset_id)
        old_qty = Decimal(current.quantity) if current else Decimal(0)
        old_basis = Decimal(current.cost_basis) if current else Decimal(0)
        new_qty = old_qty + quantity
        positions[order_before.asset_id] = PaperPosition(
            order_before.market_id,
            order_before.asset_id,
            decimal_text(new_qty),
            decimal_text(old_basis + notional + fee),
            current.realized_pnl if current else "0",
        )
    else:
        current = positions.get(order_before.asset_id)
        if current is None or Decimal(current.quantity) < quantity:
            raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
        old_qty = Decimal(current.quantity)
        old_basis = Decimal(current.cost_basis)
        removed_basis = old_basis * quantity / old_qty
        new_qty = old_qty - quantity
        pnl = notional - fee - removed_basis
        realized += pnl
        day = utc_day_key(fill.receive_time_ns)
        daily[day] = daily.get(day, Decimal(0)) + pnl
        cash += notional - fee
        reserved_positions[order_before.asset_id] = (
            reserved_positions.get(order_before.asset_id, Decimal(0)) - quantity
        )
        if reserved_positions[order_before.asset_id] < 0:
            raise PaperTradingError("ACCOUNT_NEGATIVE_FORBIDDEN")
        if reserved_positions[order_before.asset_id] == 0:
            reserved_positions.pop(order_before.asset_id)
        if new_qty:
            positions[order_before.asset_id] = PaperPosition(
                current.market_id,
                current.asset_id,
                decimal_text(new_qty),
                decimal_text(old_basis - removed_basis),
                decimal_text(Decimal(current.realized_pnl) + pnl),
            )
        else:
            positions.pop(order_before.asset_id)
    return PaperAccount(
        account.initial_cash,
        decimal_text(cash),
        decimal_text(reserved_cash),
        tuple(sorted(positions.values(), key=lambda item: item.asset_id)),
        tuple(
            sorted(
                (asset, decimal_text(value))
                for asset, value in reserved_positions.items()
            )
        ),
        decimal_text(realized),
        tuple(sorted((day, decimal_text(value)) for day, value in daily.items())),
    )


def mark_account(
    account: PaperAccount,
    marks: dict[str, str],
) -> dict[str, str | None]:
    marked_value = Decimal(0)
    unrealized = Decimal(0)
    for position in account.positions:
        mark = marks.get(position.asset_id)
        if mark is None:
            return {"equity": None, "unrealized_pnl": None}
        value = Decimal(position.quantity) * Decimal(mark)
        marked_value += value
        unrealized += value - Decimal(position.cost_basis)
    equity = Decimal(account.cash) + marked_value
    return {"equity": decimal_text(equity), "unrealized_pnl": decimal_text(unrealized)}


def settle_position(
    account: PaperAccount, asset_id: str, payoff: Decimal, event_time_ns: int
) -> PaperAccount:
    positions = position_map(account)
    position = positions.get(asset_id)
    if position is None:
        return account
    quantity = Decimal(position.quantity)
    proceeds = quantity * payoff
    pnl = proceeds - Decimal(position.cost_basis)
    positions.pop(asset_id)
    reserved = reservation_map(account)
    reserved.pop(asset_id, None)
    daily = {day: Decimal(value) for day, value in account.daily_realized_pnl}
    day = utc_day_key(event_time_ns)
    daily[day] = daily.get(day, Decimal(0)) + pnl
    return PaperAccount(
        account.initial_cash,
        decimal_text(Decimal(account.cash) + proceeds),
        account.reserved_cash,
        tuple(sorted(positions.values(), key=lambda item: item.asset_id)),
        tuple(
            sorted((asset, decimal_text(value)) for asset, value in reserved.items())
        ),
        decimal_text(Decimal(account.realized_pnl) + pnl),
        tuple(sorted((key, decimal_text(value)) for key, value in daily.items())),
    )


def account_to_mapping(account: PaperAccount) -> dict[str, object]:
    value = asdict(account)
    value["positions"] = list(value["positions"])
    value["reserved_positions"] = [list(item) for item in account.reserved_positions]
    value["daily_realized_pnl"] = [list(item) for item in account.daily_realized_pnl]
    return value


def account_from_mapping(value: dict[str, object]) -> PaperAccount:
    try:
        positions = tuple(PaperPosition(**item) for item in value["positions"])
        reserved = tuple(tuple(item) for item in value["reserved_positions"])
        account = PaperAccount(
            value["initial_cash"],
            value["cash"],
            value["reserved_cash"],
            positions,
            reserved,
            value["realized_pnl"],
            tuple(tuple(item) for item in value.get("daily_realized_pnl", ())),
        )
    except (KeyError, TypeError, ValueError):
        raise PaperTradingError("SERIALIZATION_INVALID") from None
    validate_account(account)
    return account
